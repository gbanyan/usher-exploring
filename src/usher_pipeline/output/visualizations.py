"""Visualization generation for pipeline outputs."""

import logging
from pathlib import Path

import matplotlib
import polars as pl

# Use Agg backend (non-interactive, safe for headless/CLI use)
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

logger = logging.getLogger(__name__)


def plot_score_distribution(df: pl.DataFrame, output_path: Path) -> Path:
    """
    Create histogram of composite scores colored by confidence tier.

    Args:
        df: DataFrame with composite_score and confidence_tier columns
        output_path: Path where PNG will be saved

    Returns:
        Path to the saved PNG file

    Notes:
        - Converts to pandas for seaborn compatibility
        - Uses tier-specific color coding (HIGH=green, MEDIUM=orange, LOW=red)
        - Saves at 300 DPI for publication quality
    """
    # Convert to pandas for seaborn
    pdf = df.to_pandas()

    # Set seaborn theme
    sns.set_theme(style="whitegrid", context="paper")

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create stacked histogram
    sns.histplot(
        data=pdf,
        x="composite_score",
        hue="confidence_tier",
        hue_order=["HIGH", "MEDIUM", "LOW"],
        palette={
            "HIGH": "#2ecc71",
            "MEDIUM": "#f39c12",
            "LOW": "#e74c3c",
        },
        bins=30,
        multiple="stack",
        ax=ax,
    )

    # Add labels
    ax.set_xlabel("Composite Score")
    ax.set_ylabel("Candidate Count")
    ax.set_title("Score Distribution by Confidence Tier")

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")

    # CRITICAL: Close figure to prevent memory leak
    plt.close(fig)

    logger.info(f"Saved score distribution plot to {output_path}")
    return output_path


def plot_layer_contributions(df: pl.DataFrame, output_path: Path) -> Path:
    """
    Create bar chart showing evidence layer coverage.

    Args:
        df: DataFrame with layer score columns
        output_path: Path where PNG will be saved

    Returns:
        Path to the saved PNG file

    Notes:
        - Counts non-null values per layer
        - Shows which layers have the most/least coverage
    """
    # Define layer columns
    layer_columns = [
        "gnomad_score",
        "expression_score",
        "annotation_score",
        "localization_score",
        "animal_model_score",
        "literature_score",
    ]

    # Count non-null values per layer
    layer_counts = {}
    for col in layer_columns:
        if col in df.columns:
            count = df.filter(pl.col(col).is_not_null()).height
            # Clean label (remove "_score" suffix)
            label = col.replace("_score", "").replace("_", " ").title()
            layer_counts[label] = count

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bar chart
    labels = list(layer_counts.keys())
    values = list(layer_counts.values())

    sns.barplot(x=labels, y=values, hue=labels, palette="viridis", ax=ax, legend=False)

    # Rotate labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    # Add labels
    ax.set_xlabel("Evidence Layer")
    ax.set_ylabel("Candidates with Evidence")
    ax.set_title("Evidence Layer Coverage")

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")

    # Close figure
    plt.close(fig)

    logger.info(f"Saved layer contributions plot to {output_path}")
    return output_path


def plot_tier_breakdown(df: pl.DataFrame, output_path: Path) -> Path:
    """
    Create pie chart showing tier distribution.

    Args:
        df: DataFrame with confidence_tier column
        output_path: Path where PNG will be saved

    Returns:
        Path to the saved PNG file

    Notes:
        - Shows percentage breakdown of HIGH/MEDIUM/LOW tiers
        - Uses same color scheme as score distribution plot
    """
    # Count genes per tier
    if "confidence_tier" in df.columns:
        tier_counts = df.group_by("confidence_tier").agg(
            pl.len().alias("count")
        )
        tier_dict = {
            row["confidence_tier"]: row["count"]
            for row in tier_counts.to_dicts()
        }
    else:
        tier_dict = {}

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 8))

    # Define tier order and colors
    tiers = ["HIGH", "MEDIUM", "LOW"]
    colors = ["#2ecc71", "#f39c12", "#e74c3c"]

    # Get counts in order (0 if tier not present)
    counts = [tier_dict.get(tier, 0) for tier in tiers]

    # Create pie chart
    ax.pie(
        counts,
        labels=tiers,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
    )

    ax.set_title("Candidate Tier Breakdown")

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")

    # Close figure
    plt.close(fig)

    logger.info(f"Saved tier breakdown plot to {output_path}")
    return output_path


def generate_all_plots(df: pl.DataFrame, output_dir: Path) -> dict[str, Path]:
    """
    Generate all visualization plots.

    Args:
        df: DataFrame with scoring results
        output_dir: Directory where plots will be saved

    Returns:
        Dictionary mapping plot name to file path

    Notes:
        - Creates output directory if needed
        - Wraps each plot in try/except to continue on individual failures
        - Uses standard filenames for each plot type
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    plots = {}

    # Plot 1: Score distribution
    try:
        plots["score_distribution"] = plot_score_distribution(
            df,
            output_dir / "score_distribution.png",
        )
    except Exception as e:
        logger.warning(f"Failed to create score distribution plot: {e}")

    # Plot 2: Layer contributions
    try:
        plots["layer_contributions"] = plot_layer_contributions(
            df,
            output_dir / "layer_contributions.png",
        )
    except Exception as e:
        logger.warning(f"Failed to create layer contributions plot: {e}")

    # Plot 3: Tier breakdown
    try:
        plots["tier_breakdown"] = plot_tier_breakdown(
            df,
            output_dir / "tier_breakdown.png",
        )
    except Exception as e:
        logger.warning(f"Failed to create tier breakdown plot: {e}")

    logger.info(f"Generated {len(plots)} plots in {output_dir}")
    return plots

"""Evidence layer commands: Fetch and process evidence data.

Commands for downloading and processing various evidence sources:
- gnomad: Constraint metrics (pLI, LOEUF)
- clingen: Gene-disease associations (future)
- gtex: Expression data (future)
- etc.
"""

import logging
import sys
from pathlib import Path

import click
import structlog

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.evidence.gnomad import (
    download_constraint_metrics,
    process_gnomad_constraint,
    load_to_duckdb as gnomad_load_to_duckdb,
    GNOMAD_CONSTRAINT_URL,
)
from usher_pipeline.evidence.annotation import (
    process_annotation_evidence,
    load_to_duckdb as annotation_load_to_duckdb,
)
from usher_pipeline.evidence.protein import (
    process_protein_evidence,
    load_to_duckdb as protein_load_to_duckdb,
)
from usher_pipeline.evidence.localization import (
    process_localization_evidence,
    load_to_duckdb as localization_load_to_duckdb,
)
from usher_pipeline.evidence.literature import (
    process_literature_evidence,
    load_to_duckdb as literature_load_to_duckdb,
)
from usher_pipeline.evidence.animal_models import (
    process_animal_model_evidence,
    load_to_duckdb as animal_models_load_to_duckdb,
)
from usher_pipeline.evidence.expression import (
    process_expression_evidence,
    load_to_duckdb as expression_load_to_duckdb,
)

logger = logging.getLogger(__name__)


@click.group('evidence')
def evidence():
    """Fetch and process evidence layer data.

    Evidence sources include constraint metrics (gnomAD), gene-disease
    associations (ClinGen), expression data (GTEx), and more.

    Each evidence source follows the fetch -> transform -> load pattern
    with checkpoint-restart and provenance tracking.
    """
    pass


@evidence.command('gnomad')
@click.option(
    '--force',
    is_flag=True,
    help='Re-download and reprocess data even if checkpoint exists'
)
@click.option(
    '--url',
    default=GNOMAD_CONSTRAINT_URL,
    help='Override gnomAD constraint file URL'
)
@click.option(
    '--min-depth',
    type=float,
    default=30.0,
    help='Minimum mean sequencing depth for quality filtering (default: 30x)'
)
@click.option(
    '--min-cds-pct',
    type=float,
    default=0.9,
    help='Minimum CDS coverage percentage for quality filtering (default: 0.9 = 90%%)'
)
@click.pass_context
def gnomad(ctx, force, url, min_depth, min_cds_pct):
    """Fetch and load gnomAD constraint metrics (pLI, LOEUF).

    Downloads gnomAD v4.1 constraint metrics, filters by coverage quality,
    normalizes LOEUF scores (0-1 range, inverted), and loads to DuckDB.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: download, process, and load
        usher-pipeline evidence gnomad

        # Force re-download and reprocess
        usher-pipeline evidence gnomad --force

        # Use custom quality thresholds
        usher-pipeline evidence gnomad --min-depth 20 --min-cds-pct 0.8
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== gnomAD Constraint Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo(f"  gnomAD Version: {config.versions.gnomad_version}")
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('gnomad_constraint')

        if has_checkpoint and not force:
            click.echo(click.style(
                "gnomAD constraint checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('gnomad_constraint')
            if df is not None:
                total_genes = len(df)
                measured = df.filter(df['quality_flag'] == 'measured').height
                incomplete = df.filter(df['quality_flag'] == 'incomplete_coverage').height
                no_data = df.filter(df['quality_flag'] == 'no_data').height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  Measured (good coverage): {measured}")
                click.echo(f"  Incomplete coverage: {incomplete}")
                click.echo(f"  No data: {no_data}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Download gnomAD constraint metrics
        click.echo("Downloading gnomAD constraint metrics...")
        click.echo(f"  URL: {url}")
        click.echo(f"  Version: {config.versions.gnomad_version}")

        gnomad_dir = Path(config.data_dir) / "gnomad"
        gnomad_dir.mkdir(parents=True, exist_ok=True)
        tsv_path = gnomad_dir / "constraint_metrics.tsv"

        try:
            tsv_path = download_constraint_metrics(
                output_path=tsv_path,
                url=url,
                force=force
            )
            click.echo(click.style(
                f"  Downloaded to: {tsv_path}",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error downloading: {e}", fg='red'), err=True)
            logger.exception("Failed to download gnomAD constraint metrics")
            sys.exit(1)

        click.echo()
        provenance.record_step('download_gnomad_constraint', {
            'url': url,
            'version': config.versions.gnomad_version,
            'output_path': str(tsv_path),
        })

        # Process constraint data
        click.echo("Processing constraint metrics...")
        click.echo(f"  Min depth: {min_depth}x")
        click.echo(f"  Min CDS coverage: {min_cds_pct:.0%}")

        try:
            df = process_gnomad_constraint(
                tsv_path=tsv_path,
                min_depth=min_depth,
                min_cds_pct=min_cds_pct
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process gnomAD constraint metrics")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_gnomad_constraint', {
            'min_depth': min_depth,
            'min_cds_pct': min_cds_pct,
            'total_genes': len(df),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        try:
            gnomad_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description=f"gnomAD {config.versions.gnomad_version} constraint metrics"
            )
            click.echo(click.style(
                f"  Saved to 'gnomad_constraint' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load gnomAD constraint data to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = gnomad_dir / "constraint.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        measured = df.filter(df['quality_flag'] == 'measured').height
        incomplete = df.filter(df['quality_flag'] == 'incomplete_coverage').height
        no_data = df.filter(df['quality_flag'] == 'no_data').height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo(f"  Measured (good coverage): {measured}")
        click.echo(f"  Incomplete coverage: {incomplete}")
        click.echo(f"  No data: {no_data}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("gnomAD evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('annotation')
@click.option(
    '--force',
    is_flag=True,
    help='Reprocess data even if checkpoint exists'
)
@click.pass_context
def annotation(ctx, force):
    """Fetch and load gene annotation completeness metrics.

    Retrieves GO term counts from mygene.info and UniProt annotation scores,
    classifies genes into annotation tiers (well/partial/poor), normalizes
    composite scores (0-1 range), and loads to DuckDB.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: fetch, process, and load
        usher-pipeline evidence annotation

        # Force reprocessing
        usher-pipeline evidence annotation --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Annotation Completeness Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('annotation_completeness')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Annotation completeness checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('annotation_completeness')
            if df is not None:
                total_genes = len(df)
                well_annotated = df.filter(df['annotation_tier'] == 'well_annotated').height
                partial = df.filter(df['annotation_tier'] == 'partially_annotated').height
                poor = df.filter(df['annotation_tier'] == 'poorly_annotated').height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  Well annotated: {well_annotated}")
                click.echo(f"  Partially annotated: {partial}")
                click.echo(f"  Poorly annotated: {poor}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids and uniprot mappings)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()
        uniprot_mapping = gene_universe.select(["gene_id", "uniprot_accession"]).filter(
            gene_universe["uniprot_accession"].is_not_null()
        )

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes ({uniprot_mapping.height} with UniProt mapping)",
            fg='green'
        ))
        click.echo()

        # Process annotation evidence
        click.echo("Fetching and processing annotation data...")
        click.echo("  This may take a few minutes (mygene.info + UniProt API queries)...")

        try:
            df = process_annotation_evidence(
                gene_ids=gene_ids,
                uniprot_mapping=uniprot_mapping
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process annotation evidence")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_annotation_evidence', {
            'total_genes': len(df),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        annotation_dir = Path(config.data_dir) / "annotation"
        annotation_dir.mkdir(parents=True, exist_ok=True)

        try:
            annotation_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Gene annotation completeness metrics from GO terms, UniProt scores, and pathway membership"
            )
            click.echo(click.style(
                f"  Saved to 'annotation_completeness' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load annotation data to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = annotation_dir / "completeness.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        well_annotated = df.filter(df['annotation_tier'] == 'well_annotated').height
        partial = df.filter(df['annotation_tier'] == 'partially_annotated').height
        poor = df.filter(df['annotation_tier'] == 'poorly_annotated').height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo(f"  Well annotated: {well_annotated}")
        click.echo(f"  Partially annotated: {partial}")
        click.echo(f"  Poorly annotated: {poor}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Annotation evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('localization')
@click.option(
    '--force',
    is_flag=True,
    help='Re-download and reprocess data even if checkpoint exists'
)
@click.pass_context
def localization(ctx, force):
    """Fetch and load subcellular localization evidence (HPA + proteomics).

    Integrates HPA subcellular location data with curated cilia/centrosome
    proteomics datasets. Classifies evidence as experimental vs computational,
    scores cilia proximity, and loads to DuckDB.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: download, process, and load
        usher-pipeline evidence localization

        # Force re-download and reprocess
        usher-pipeline evidence localization --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Subcellular Localization Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('subcellular_localization')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Localization checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('subcellular_localization')
            if df is not None:
                total_genes = len(df)
                experimental = df.filter(df['evidence_type'] == 'experimental').height
                computational = df.filter(df['evidence_type'] == 'computational').height
                both = df.filter(df['evidence_type'] == 'both').height
                cilia_localized = df.filter(df['cilia_proximity_score'] > 0.5).height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  Experimental evidence: {experimental}")
                click.echo(f"  Computational evidence: {computational}")
                click.echo(f"  Both: {both}")
                click.echo(f"  Cilia-localized (proximity > 0.5): {cilia_localized}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids and gene_symbol mapping)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()
        gene_symbol_map = gene_universe.select(["gene_id", "gene_symbol"])

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes",
            fg='green'
        ))
        click.echo()

        # Create localization data directory
        localization_dir = Path(config.data_dir) / "localization"
        localization_dir.mkdir(parents=True, exist_ok=True)

        # Process localization evidence
        click.echo("Fetching and processing localization data...")
        click.echo("  Downloading HPA subcellular location data (~10MB)...")
        click.echo("  Cross-referencing cilia/centrosome proteomics datasets...")

        try:
            df = process_localization_evidence(
                gene_ids=gene_ids,
                gene_symbol_map=gene_symbol_map,
                cache_dir=localization_dir,
                force=force,
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process localization evidence")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_localization_evidence', {
            'total_genes': len(df),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        try:
            localization_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="HPA subcellular localization with cilia/centrosome proteomics cross-references"
            )
            click.echo(click.style(
                f"  Saved to 'subcellular_localization' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load localization data to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = localization_dir / "subcellular.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        experimental = df.filter(df['evidence_type'] == 'experimental').height
        computational = df.filter(df['evidence_type'] == 'computational').height
        both = df.filter(df['evidence_type'] == 'both').height
        cilia_localized = df.filter(df['cilia_proximity_score'] > 0.5).height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo(f"  Experimental evidence: {experimental}")
        click.echo(f"  Computational evidence: {computational}")
        click.echo(f"  Both: {both}")
        click.echo(f"  Cilia-localized (proximity > 0.5): {cilia_localized}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Localization evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('protein')
@click.option(
    '--force',
    is_flag=True,
    help='Reprocess data even if checkpoint exists'
)
@click.pass_context
def protein(ctx, force):
    """Fetch and load protein features from UniProt/InterPro.

    Extracts protein length, domain composition, coiled-coil regions,
    transmembrane domains, and cilia-associated motifs. Computes normalized
    composite protein score (0-1 range).

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: fetch, process, and load
        usher-pipeline evidence protein

        # Force re-fetch and reprocess
        usher-pipeline evidence protein --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Protein Features Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('protein_features')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Protein features checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('protein_features')
            if df is not None:
                total_genes = len(df)
                with_uniprot = df.filter(df['uniprot_id'].is_not_null()).height
                cilia_domains = df.filter(df['has_cilia_domain'] == True).height
                scaffold_domains = df.filter(df['scaffold_adaptor_domain'] == True).height
                coiled_coils = df.filter(df['coiled_coil'] == True).height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  With UniProt data: {with_uniprot}")
                click.echo(f"  With cilia domains: {cilia_domains}")
                click.echo(f"  With scaffold domains: {scaffold_domains}")
                click.echo(f"  With coiled-coils: {coiled_coils}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe for gene IDs and UniProt mappings
        click.echo("Loading gene universe...")
        gene_universe = store.load_dataframe('gene_universe')
        if gene_universe is None:
            click.echo(click.style(
                "Error: gene_universe not found. Run 'usher-pipeline setup gene-universe' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()
        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes from gene_universe",
            fg='green'
        ))
        click.echo()

        # Process protein evidence
        click.echo("Processing protein features...")
        click.echo("  Fetching from UniProt and InterPro APIs...")
        click.echo("  (This may take several minutes depending on API rate limits)")

        try:
            df = process_protein_evidence(
                gene_ids=gene_ids,
                uniprot_mapping=gene_universe,
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process protein features")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_protein_features', {
            'total_genes': len(df),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        protein_dir = Path(config.data_dir) / "protein"
        protein_dir.mkdir(parents=True, exist_ok=True)

        try:
            protein_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Protein features from UniProt/InterPro with domain composition and cilia motif detection"
            )
            click.echo(click.style(
                f"  Saved to 'protein_features' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load protein features to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = protein_dir / "features.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        total_genes = len(df)
        with_uniprot = df.filter(df['uniprot_id'].is_not_null()).height
        cilia_domains = df.filter(df['has_cilia_domain'] == True).height
        scaffold_domains = df.filter(df['scaffold_adaptor_domain'] == True).height
        coiled_coils = df.filter(df['coiled_coil'] == True).height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {total_genes}")
        click.echo(f"  With UniProt data: {with_uniprot}")
        click.echo(f"  With cilia domains: {cilia_domains}")
        click.echo(f"  With scaffold domains: {scaffold_domains}")
        click.echo(f"  With coiled-coils: {coiled_coils}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Protein evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('animal-models')
@click.option(
    '--force',
    is_flag=True,
    help='Reprocess data even if checkpoint exists'
)
@click.pass_context
def animal_models(ctx, force):
    """Fetch and load animal model phenotype evidence.

    Retrieves knockout/perturbation phenotypes from MGI (mouse), ZFIN (zebrafish),
    and IMPC, maps human genes to orthologs with confidence scoring, filters for
    sensory/cilia-relevant phenotypes, and scores evidence.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: fetch, process, and load
        usher-pipeline evidence animal-models

        # Force reprocessing
        usher-pipeline evidence animal-models --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Animal Model Phenotype Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('animal_model_phenotypes')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Animal model phenotypes checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('animal_model_phenotypes')
            if df is not None:
                total_genes = len(df)
                with_mouse = df.filter(df['mouse_ortholog'].is_not_null()).height
                with_zebrafish = df.filter(df['zebrafish_ortholog'].is_not_null()).height
                with_sensory = df.filter(df['sensory_phenotype_count'].is_not_null()).height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  With mouse ortholog: {with_mouse}")
                click.echo(f"  With zebrafish ortholog: {with_zebrafish}")
                click.echo(f"  With sensory phenotypes: {with_sensory}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes",
            fg='green'
        ))
        click.echo()

        # Process animal model evidence
        click.echo("Fetching and processing animal model data...")
        click.echo("  This may take several minutes (HCOP, MGI, ZFIN, IMPC downloads)...")

        try:
            df = process_animal_model_evidence(gene_ids=gene_ids)
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process animal model evidence")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_animal_model_evidence', {
            'total_genes': len(df),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        animal_models_dir = Path(config.data_dir) / "animal_models"
        animal_models_dir.mkdir(parents=True, exist_ok=True)

        try:
            animal_models_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Animal model phenotypes from MGI, ZFIN, and IMPC with ortholog confidence scoring"
            )
            click.echo(click.style(
                f"  Saved to 'animal_model_phenotypes' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load animal model data to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = animal_models_dir / "phenotypes.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        with_mouse = df.filter(df['mouse_ortholog'].is_not_null()).height
        with_zebrafish = df.filter(df['zebrafish_ortholog'].is_not_null()).height
        with_sensory = df.filter(df['sensory_phenotype_count'].is_not_null()).height

        # Top scoring genes
        top_genes = df.filter(df['animal_model_score_normalized'].is_not_null()).sort(
            'animal_model_score_normalized', descending=True
        ).head(10).select(['gene_id', 'sensory_phenotype_count', 'animal_model_score_normalized'])

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo(f"  With mouse ortholog: {with_mouse}")
        click.echo(f"  With zebrafish ortholog: {with_zebrafish}")
        click.echo(f"  With sensory phenotypes: {with_sensory}")
        click.echo()
        click.echo("Top 10 scoring genes:")
        for row in top_genes.iter_rows(named=True):
            click.echo(f"  {row['gene_id']}: {row['animal_model_score_normalized']:.3f} ({row['sensory_phenotype_count']} phenotypes)")
        click.echo()
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Animal model evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('literature')
@click.option(
    '--force',
    is_flag=True,
    help='Reprocess data even if checkpoint exists'
)
@click.option(
    '--email',
    required=True,
    help='Email address for NCBI E-utilities (required by PubMed API)'
)
@click.option(
    '--api-key',
    default=None,
    help='NCBI API key for higher rate limit (10 req/sec vs 3 req/sec). Get from https://www.ncbi.nlm.nih.gov/account/settings/'
)
@click.option(
    '--batch-size',
    type=int,
    default=500,
    help='Save partial checkpoints every N genes (default: 500)'
)
@click.pass_context
def literature(ctx, force, email, api_key, batch_size):
    """Fetch and load literature evidence from PubMed.

    Queries PubMed for each gene across multiple contexts (cilia, sensory, cytoskeleton,
    cell polarity), classifies evidence into quality tiers, and computes quality-weighted
    scores with bias mitigation to avoid TP53-like well-studied gene dominance.

    WARNING: This is a SLOW operation (estimated 3-11 hours for 20K genes):
    - With API key (10 req/sec): ~3.3 hours
    - Without API key (3 req/sec): ~11 hours

    Supports checkpoint-restart: saves partial results every batch-size genes.
    Interrupted runs can be resumed (use --force to restart from scratch).

    Get NCBI API key: https://www.ncbi.nlm.nih.gov/account/settings/
    (API Key Management -> Create API Key)

    Examples:

        # With API key (recommended - 3x faster)
        usher-pipeline evidence literature --email you@example.com --api-key YOUR_KEY

        # Without API key (slower)
        usher-pipeline evidence literature --email you@example.com

        # Force restart from scratch
        usher-pipeline evidence literature --email you@example.com --api-key YOUR_KEY --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Literature Evidence (PubMed) ===", bold=True))
    click.echo()

    # Warn about long runtime
    if api_key:
        click.echo(click.style("  NCBI API key provided: faster rate limit (10 req/sec)", fg='cyan'))
        click.echo(click.style("  Estimated runtime: ~3-4 hours for 20K genes", fg='cyan'))
    else:
        click.echo(click.style("  No API key: using default rate limit (3 req/sec)", fg='yellow'))
        click.echo(click.style("  Estimated runtime: ~10-12 hours for 20K genes", fg='yellow'))
        click.echo(click.style("  Get API key at: https://www.ncbi.nlm.nih.gov/account/settings/", fg='yellow'))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('literature_evidence')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Literature evidence checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('literature_evidence')
            if df is not None:
                total_genes = len(df)
                tier_counts = (
                    df.group_by("evidence_tier")
                    .agg(df.select("gene_id").count().alias("count"))
                    .sort("count", descending=True)
                )

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo("Evidence Tier Distribution:")
                for row in tier_counts.to_dicts():
                    tier = row["evidence_tier"]
                    count = row["count"]
                    pct = (count / total_genes) * 100
                    click.echo(f"  {tier}: {count} ({pct:.1f}%)")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids and gene_symbols)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()
        gene_symbol_map = gene_universe.select(["gene_id", "gene_symbol"]).filter(
            gene_universe["gene_symbol"].is_not_null()
        )

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes ({gene_symbol_map.height} with symbols)",
            fg='green'
        ))
        click.echo()

        # Process literature evidence
        click.echo("Fetching and processing literature evidence from PubMed...")
        click.echo(f"  Email: {email}")
        click.echo(f"  Batch size: {batch_size} genes")
        click.echo(f"  This will take several hours. Progress logged every 100 genes.")
        click.echo()

        try:
            df = process_literature_evidence(
                gene_ids=gene_ids,
                gene_symbol_map=gene_symbol_map,
                email=email,
                api_key=api_key,
                batch_size=batch_size,
                checkpoint_df=None,  # Future: load partial checkpoint if exists
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process literature evidence")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_literature_evidence', {
            'total_genes': len(df),
            'email': email,
            'has_api_key': api_key is not None,
            'batch_size': batch_size,
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        literature_dir = Path(config.data_dir) / "literature"
        literature_dir.mkdir(parents=True, exist_ok=True)

        try:
            literature_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="PubMed literature evidence with context-specific queries and quality-weighted scoring"
            )
            click.echo(click.style(
                f"  Saved to 'literature_evidence' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load literature evidence to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = literature_dir / "pubmed.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        tier_counts = (
            df.group_by("evidence_tier")
            .agg(df.select("gene_id").count().alias("count"))
            .sort("count", descending=True)
        )

        genes_with_evidence = df.filter(
            df["evidence_tier"].is_in(["direct_experimental", "functional_mention", "hts_hit"])
        ).height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo("Evidence Tier Distribution:")
        for row in tier_counts.to_dicts():
            tier = row["evidence_tier"]
            count = row["count"]
            pct = (count / len(df)) * 100
            click.echo(f"  {tier}: {count} ({pct:.1f}%)")
        click.echo()
        click.echo(f"Genes with Evidence (direct/functional/hts): {genes_with_evidence}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Literature evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()

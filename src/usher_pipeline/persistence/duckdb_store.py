"""DuckDB-based storage for pipeline checkpoints with restart capability."""

from pathlib import Path
from typing import Optional, Union

import duckdb
import polars as pl

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class PipelineStore:
    """
    DuckDB-based storage for pipeline intermediate results.

    Enables checkpoint-restart pattern: expensive operations (API downloads,
    processing) can be saved as DuckDB tables and skipped on subsequent runs.
    """

    def __init__(self, db_path: Path):
        """
        Initialize PipelineStore with a DuckDB database.

        Args:
            db_path: Path to DuckDB database file. Parent directories
                     are created automatically.
        """
        self.db_path = db_path
        # Create parent directories
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to DuckDB
        self.conn = duckdb.connect(str(db_path))

        # Create metadata table for tracking checkpoints
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _checkpoints (
                table_name VARCHAR PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                row_count INTEGER,
                description VARCHAR
            )
        """)

    def save_dataframe(
        self,
        df: Union[pl.DataFrame, "pd.DataFrame"],
        table_name: str,
        description: str = "",
        replace: bool = True
    ) -> None:
        """
        Save a DataFrame to DuckDB as a table.

        Args:
            df: Polars or pandas DataFrame to save
            table_name: Name for the DuckDB table
            description: Optional description for checkpoint metadata
            replace: If True, replace existing table; if False, append
        """
        # Detect DataFrame type
        is_polars = isinstance(df, pl.DataFrame)
        if not is_polars and not HAS_PANDAS:
            raise ValueError("pandas not available")
        if not is_polars and not isinstance(df, pd.DataFrame):
            raise ValueError("df must be polars.DataFrame or pandas.DataFrame")

        # Save DataFrame
        if replace:
            self.conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
        else:
            self.conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")

        # Update checkpoint metadata
        row_count = len(df)
        self.conn.execute("""
            INSERT OR REPLACE INTO _checkpoints (table_name, row_count, description, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, [table_name, row_count, description])

    def load_dataframe(
        self,
        table_name: str,
        as_polars: bool = True
    ) -> Optional[Union[pl.DataFrame, "pd.DataFrame"]]:
        """
        Load a table as a DataFrame.

        Args:
            table_name: Name of the DuckDB table
            as_polars: If True, return polars DataFrame; else pandas

        Returns:
            DataFrame or None if table doesn't exist
        """
        try:
            result = self.conn.execute(f"SELECT * FROM {table_name}")
            if as_polars:
                return result.pl()
            else:
                if not HAS_PANDAS:
                    raise ValueError("pandas not available")
                return result.df()
        except duckdb.CatalogException:
            # Table doesn't exist
            return None

    def has_checkpoint(self, table_name: str) -> bool:
        """
        Check if a checkpoint exists.

        Args:
            table_name: Name of the table to check

        Returns:
            True if checkpoint exists, False otherwise
        """
        result = self.conn.execute(
            "SELECT COUNT(*) FROM _checkpoints WHERE table_name = ?",
            [table_name]
        ).fetchone()
        return result[0] > 0

    def list_checkpoints(self) -> list[dict]:
        """
        List all checkpoints with metadata.

        Returns:
            List of checkpoint metadata dicts with keys:
            table_name, created_at, row_count, description
        """
        result = self.conn.execute("""
            SELECT table_name, created_at, row_count, description
            FROM _checkpoints
            ORDER BY created_at DESC
        """).fetchall()

        return [
            {
                "table_name": row[0],
                "created_at": row[1],
                "row_count": row[2],
                "description": row[3],
            }
            for row in result
        ]

    def delete_checkpoint(self, table_name: str) -> None:
        """
        Delete a checkpoint and its metadata.

        Args:
            table_name: Name of the table to delete
        """
        # Drop table if exists
        self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")

        # Remove from metadata
        self.conn.execute(
            "DELETE FROM _checkpoints WHERE table_name = ?",
            [table_name]
        )

    def export_parquet(self, table_name: str, output_path: Path) -> None:
        """
        Export a table to Parquet format.

        Args:
            table_name: Name of the table to export
            output_path: Path to output Parquet file
        """
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Export using DuckDB's native Parquet writer
        self.conn.execute(
            f"COPY {table_name} TO ? (FORMAT PARQUET)",
            [str(output_path)]
        )

    def execute_query(
        self,
        query: str,
        params: Optional[list] = None
    ) -> pl.DataFrame:
        """
        Execute arbitrary SQL query and return polars DataFrame.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            Query results as polars DataFrame
        """
        if params:
            result = self.conn.execute(query, params)
        else:
            result = self.conn.execute(query)
        return result.pl()

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()
        return False

    @classmethod
    def from_config(cls, config: "PipelineConfig") -> "PipelineStore":
        """
        Create PipelineStore from a PipelineConfig.

        Args:
            config: PipelineConfig instance

        Returns:
            PipelineStore instance
        """
        return cls(config.duckdb_path)

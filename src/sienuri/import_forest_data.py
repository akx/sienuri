import argparse
import pathlib
import time
from contextlib import contextmanager

import duckdb
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

console = Console()


def import_forest_data():
    """Import forest data from GeoPackage files into DuckDB database."""
    ap = argparse.ArgumentParser(description="Import forest data from GeoPackages into topo.duckdb")
    ap.add_argument("--forest-dir", required=True, type=pathlib.Path, help="Directory containing .gpkg files")
    ap.add_argument("--database", required=True, type=pathlib.Path, help="Path to topo.duckdb database")
    args = ap.parse_args()

    if not args.forest_dir.exists():
        console.print(f"[red]Error: Forest directory {args.forest_dir} does not exist[/red]")
        return 1

    if not args.database.exists():
        console.print(f"[red]Error: Database {args.database} does not exist[/red]")
        return 1

    gpkg_files = sorted(args.forest_dir.glob("*.gpkg"))
    if not gpkg_files:
        console.print(f"[red]Error: No .gpkg files found in {args.forest_dir}[/red]")
        return 1

    console.print(f"Found {len(gpkg_files)} GeoPackage files")

    with duckdb.connect(str(args.database)) as con:
        # Install and load spatial extension
        con.execute("INSTALL spatial")
        con.execute("LOAD spatial")

        import_tables(con, gpkg_files)

        # Perform spatial join
        add_stand_id_to_topo(con)

    console.print("[green]✓ Forest data import completed successfully[/green]")
    return 0


def import_tables(con: duckdb.DuckDBPyConnection, gpkg_files: list[pathlib.Path]):
    table_id_columns = {
        "stand": "standid",
        # TODO: enable when needed by a query
        # "assortment": "assortmentid",
        # "operation": "operationid",
        # "restriction": "restrictionid",
        # "specialfeature": "specialfeatureid",
        # "specification": "specificationid",
        "treestand": "treestandid",
        "treestandsummary": "treestandsummaryid",
        # "treestratum": "treestratumid",
        # "datasource": "code",
    }

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(elapsed_when_finished=True),
    ) as progress:
        for table_name, id_column in table_id_columns.items():
            task = progress.add_task(f"[cyan]Processing {table_name}...", total=len(gpkg_files))
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            id_column = table_id_columns[table_name]
            extra = ""
            if table_name == "stand":
                pass  # extra = ", st_extent(geometry) as bbox"

            for idx, gpkg_file in enumerate(gpkg_files):
                if idx == 0:
                    con.execute(f"""
                        CREATE TABLE {table_name} AS
                        SELECT '{gpkg_file.name}' AS source_file, *{extra}
                        FROM st_read('{gpkg_file}', layer='{table_name}')
                    """)
                    con.execute(f"ALTER TABLE {table_name} ADD PRIMARY KEY ({id_column})")
                else:
                    con.execute(f"""
                        INSERT OR IGNORE INTO {table_name}
                        SELECT '{gpkg_file.name}' AS source_file, *{extra}
                        FROM st_read('{gpkg_file}', layer='{table_name}')
                    """)

                progress.update(task, advance=1)

            if table_name == "stand":
                progress.update(task, description=(f"[cyan]Creating spatial index on {table_name}...[/cyan]"))
                con.execute(f"CREATE INDEX {table_name}_geom_idx ON {table_name} USING RTREE (geometry)")

            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            progress.update(task, description=(f"[green]✓ Imported {count:,} {table_name} records[/green]"))


@contextmanager
def measure_time(*, intro: str, outro: str):
    with Progress(
        SpinnerColumn(),
        TimeElapsedColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task(intro, total=None)
        t0 = time.monotonic()
        yield
        t1 = time.monotonic()
        progress.update(task, description=outro)
    console.print(f"[green]✓ {outro} in {t1 - t0:.1f}s[/green]")


def add_stand_id_to_topo(con: duckdb.DuckDBPyConnection):
    """Add stand_id column to topo table via spatial join."""
    console.print("\n[bold]Performing spatial join...[/bold]")

    with measure_time(
        intro="Creating temporary join table (this may take several minutes)",
        outro="Temporary join table created",
    ):
        con.execute("""
            CREATE TEMP TABLE topo_stand_mapping AS
            SELECT t.rowid as topo_rowid, s.standid
            FROM topo t LEFT JOIN stand s
            ON ST_Within(ST_Point(t.x_etrs, t.y_etrs), s.geometry)
        """)

    with measure_time(intro="Updating topo table...", outro="Topo table updated"):
        try:
            con.execute("ALTER TABLE topo DROP COLUMN standid")
        except Exception:
            pass

        # Add column
        con.execute("ALTER TABLE topo ADD COLUMN standid INTEGER")

        con.execute("UPDATE topo SET standid = m.standid FROM topo_stand_mapping m WHERE topo.rowid = m.topo_rowid")

    # Clean up temp table
    con.execute("DROP TABLE topo_stand_mapping")

    # Get statistics
    total_points = con.execute("SELECT COUNT(*) FROM topo").fetchone()[0]
    matched_points = con.execute("SELECT COUNT(*) FROM topo WHERE standid IS NOT NULL").fetchone()[0]
    match_percentage = (matched_points / total_points * 100) if total_points > 0 else 0

    console.print(f"  Total topo points: {total_points:,}")
    console.print(f"  Matched to stands: {matched_points:,} ({match_percentage:.1f}%)")
    console.print(f"  Unmatched points: {total_points - matched_points:,}")


if __name__ == "__main__":
    import sys

    sys.exit(import_forest_data())

import argparse
import pathlib
import time

import duckdb
from rich.console import Console
from rich.progress import Progress

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

    console.print(f"[green]Found {len(gpkg_files)} GeoPackage files[/green]")

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
        "assortment": "assortmentid",
        "operation": "operationid",
        "restriction": "restrictionid",
        "specialfeature": "specialfeatureid",
        "specification": "specificationid",
        "treestand": "treestandid",
        "treestandsummary": "treestandsummaryid",
        "treestratum": "treestratumid",
        "datasource": "code",
    }

    with Progress() as progress:
        # Import tables that reference stand
        # Map table name to their ID column name (the primary key in the table)

        for table_name, id_column in table_id_columns.items():
            task = progress.add_task(f"[cyan]Processing {table_name}...", total=len(gpkg_files))
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            id_column = table_id_columns[table_name]

            for idx, gpkg_file in enumerate(gpkg_files):
                if idx == 0:
                    con.execute(f"""
                        CREATE TABLE {table_name} AS
                        SELECT '{gpkg_file.name}' AS source_file, *
                        FROM st_read('{gpkg_file}', layer='{table_name}')
                    """)
                    con.execute(f"ALTER TABLE {table_name} ADD PRIMARY KEY ({id_column})")
                else:
                    con.execute(f"""
                        INSERT OR IGNORE INTO {table_name}
                        SELECT '{gpkg_file.name}' AS source_file, *
                        FROM st_read('{gpkg_file}', layer='{table_name}')
                    """)

                progress.update(task, advance=1)

            if table_name == "stand":
                progress.update(task, description=(f"[cyan]Creating spatial index on {table_name}...[/cyan]"))
                con.execute(f"CREATE INDEX {table_name}_geom_idx ON {table_name} USING RTREE (geometry)")

            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            progress.update(task, description=(f"[green]✓ Imported {count:,} {table_name} records[/green]"))


def add_stand_id_to_topo(con: duckdb.DuckDBPyConnection):
    """Add stand_id column to topo table via spatial join."""
    console.print("\n[bold]Performing spatial join...[/bold]")

    console.print("[cyan]Creating temporary join table (this may take several minutes)...[/cyan]")
    t0 = time.monotonic()

    con.execute("""
        CREATE TEMP TABLE topo_stand_mapping AS
        SELECT t.rowid as topo_rowid, s.standid
        FROM topo t JOIN stand s
        ON ST_Within(ST_Point(t.x_etrs, t.y_etrs), s.geometry)
    """)

    t_join = time.monotonic()
    console.print(f"[green]✓ Join completed in {t_join - t0:.1f}s[/green]")

    console.print("[cyan]Updating topo table...[/cyan]")

    # Check if column already exists
    try:
        con.execute("ALTER TABLE topo DROP COLUMN standid")
    except Exception:
        pass

    # Add column
    con.execute("ALTER TABLE topo ADD COLUMN standid INTEGER")

    con.execute("""
        UPDATE topo
        SET standid = m.standid
        FROM topo_stand_mapping m
        WHERE topo.rowid = m.topo_rowid
    """)

    t1 = time.monotonic()

    # Clean up temp table
    con.execute("DROP TABLE topo_stand_mapping")

    # Get statistics
    total_points = con.execute("SELECT COUNT(*) FROM topo").fetchone()[0]
    matched_points = con.execute("SELECT COUNT(*) FROM topo WHERE standid IS NOT NULL").fetchone()[0]
    match_percentage = (matched_points / total_points * 100) if total_points > 0 else 0

    console.print(f"[green]✓ Spatial join completed in {t1 - t0:.1f}s total[/green]")
    console.print(f"  Total topo points: {total_points:,}")
    console.print(f"  Matched to stands: {matched_points:,} ({match_percentage:.1f}%)")
    console.print(f"  Unmatched points: {total_points - matched_points:,}")


if __name__ == "__main__":
    import sys

    sys.exit(import_forest_data())

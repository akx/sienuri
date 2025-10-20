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

        # Import all forest data
        import_all_stands(con, gpkg_files)
        import_related_tables(con, gpkg_files)

        # Perform spatial join
        add_stand_id_to_topo(con)

    console.print("[green]✓ Forest data import completed successfully[/green]")
    return 0


def import_all_stands(con: duckdb.DuckDBPyConnection, gpkg_files: list[pathlib.Path]):
    """Import all stand tables from GeoPackages into a single stand table."""
    console.print("\n[bold]Importing stand data...[/bold]")

    # Drop existing stand table if it exists
    con.execute("DROP TABLE IF EXISTS stand")

    with Progress() as progress:
        task = progress.add_task("[cyan]Processing GeoPackages...", total=len(gpkg_files))

        for idx, gpkg_file in enumerate(gpkg_files):
            t0 = time.monotonic()

            # Calculate global ID offset (each file gets a range of IDs)
            global_id_offset = idx * 10000000  # Large offset to avoid collisions

            # Read stand table from GeoPackage and add to main database
            if idx == 0:
                # First file: create the table
                con.execute(f"""
                    CREATE TABLE stand AS
                    SELECT
                        {global_id_offset} + standid AS global_stand_id,
                        '{gpkg_file.name}' AS source_file,
                        *
                    FROM st_read('{gpkg_file}', layer='stand')
                """)
            else:
                # Subsequent files: insert into existing table
                con.execute(f"""
                    INSERT INTO stand
                    SELECT
                        {global_id_offset} + standid AS global_stand_id,
                        '{gpkg_file.name}' AS source_file,
                        *
                    FROM st_read('{gpkg_file}', layer='stand')
                """)

            t1 = time.monotonic()
            progress.update(task, advance=1, description=f"[cyan]Processed {gpkg_file.name} in {t1-t0:.1f}s")

    # Get count and report
    count = con.execute("SELECT COUNT(*) FROM stand").fetchone()[0]
    console.print(f"[green]✓ Imported {count:,} stands from {len(gpkg_files)} files[/green]")


def import_related_tables(con: duckdb.DuckDBPyConnection, gpkg_files: list[pathlib.Path]):
    """Import related forest tables (treestand, treestratum, etc.)."""
    console.print("\n[bold]Importing related tables...[/bold]")

    # Tables that reference stand via standid foreign key
    related_tables = [
        "treestand",
        "restriction",
        "operation",
        "specialfeature",
    ]

    # Tables with other foreign keys
    nested_tables = {
        "treestratum": "treestandid",  # references treestand
        "treestandsummary": "treestandid",  # references treestand
        "assortment": "operationid",  # references operation
        "specification": "operationid",  # references operation
    }

    # Independent table
    other_tables = ["datasource"]

    with Progress() as progress:
        # Import tables that reference stand
        # Map table name to their ID column name (the primary key in the table)
        table_id_columns = {
            "treestand": "treestandid",
            "restriction": "restrictionid",
            "operation": "operationid",
            "specialfeature": "specialfeatureid",
        }

        for table_name in related_tables:
            task = progress.add_task(f"[cyan]Processing {table_name}...", total=len(gpkg_files))
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            id_column = table_id_columns.get(table_name, "id")

            for idx, gpkg_file in enumerate(gpkg_files):
                global_id_offset = idx * 10000000

                # Check if table exists in this GeoPackage
                try:
                    if idx == 0:
                        con.execute(f"""
                            CREATE TABLE {table_name} AS
                            SELECT
                                {global_id_offset} + {id_column} AS global_id,
                                {global_id_offset} + standid AS global_stand_id,
                                '{gpkg_file.name}' AS source_file,
                                *
                            FROM st_read('{gpkg_file}', layer='{table_name}')
                        """)
                    else:
                        con.execute(f"""
                            INSERT INTO {table_name}
                            SELECT
                                {global_id_offset} + {id_column} AS global_id,
                                {global_id_offset} + standid AS global_stand_id,
                                '{gpkg_file.name}' AS source_file,
                                *
                            FROM st_read('{gpkg_file}', layer='{table_name}')
                        """)
                except Exception:
                    # Table might not exist in this GeoPackage, skip
                    pass

                progress.update(task, advance=1)

            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            console.print(f"[green]✓ Imported {count:,} {table_name} records[/green]")

        # Import nested tables (reference treestand or operation)
        # Map table name to their ID column name
        nested_id_columns = {
            "treestratum": "treestratumid",
            "treestandsummary": "treestandsummaryid",
            "assortment": "assortmentid",
            "specification": "specificationid",
        }

        for table_name, fk_column in nested_tables.items():
            task = progress.add_task(f"[cyan]Processing {table_name}...", total=len(gpkg_files))
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            id_column = nested_id_columns.get(table_name, "id")

            for idx, gpkg_file in enumerate(gpkg_files):
                global_id_offset = idx * 10000000

                try:
                    if idx == 0:
                        con.execute(f"""
                            CREATE TABLE {table_name} AS
                            SELECT
                                {global_id_offset} + {id_column} AS global_id,
                                {global_id_offset} + {fk_column} AS global_{fk_column},
                                '{gpkg_file.name}' AS source_file,
                                *
                            FROM st_read('{gpkg_file}', layer='{table_name}')
                        """)
                    else:
                        con.execute(f"""
                            INSERT INTO {table_name}
                            SELECT
                                {global_id_offset} + {id_column} AS global_id,
                                {global_id_offset} + {fk_column} AS global_{fk_column},
                                '{gpkg_file.name}' AS source_file,
                                *
                            FROM st_read('{gpkg_file}', layer='{table_name}')
                        """)
                except Exception:
                    pass

                progress.update(task, advance=1)

            count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            console.print(f"[green]✓ Imported {count:,} {table_name} records[/green]")

        # Import datasource table (no foreign keys needed)
        task = progress.add_task("[cyan]Processing datasource...", total=len(gpkg_files))
        con.execute("DROP TABLE IF EXISTS datasource")

        for idx, gpkg_file in enumerate(gpkg_files):
            try:
                if idx == 0:
                    con.execute(f"""
                        CREATE TABLE datasource AS
                        SELECT DISTINCT * FROM st_read('{gpkg_file}', layer='datasource')
                    """)
                else:
                    con.execute(f"""
                        INSERT INTO datasource
                        SELECT * FROM st_read('{gpkg_file}', layer='datasource')
                        WHERE code NOT IN (SELECT code FROM datasource)
                    """)
            except Exception:
                pass

            progress.update(task, advance=1)

        count = con.execute("SELECT COUNT(*) FROM datasource").fetchone()[0]
        console.print(f"[green]✓ Imported {count:,} datasource records[/green]")


def add_stand_id_to_topo(con: duckdb.DuckDBPyConnection):
    """Add stand_id column to topo table via spatial join."""
    console.print("\n[bold]Performing spatial join...[/bold]")

    # Check if column already exists
    try:
        con.execute("ALTER TABLE topo DROP COLUMN stand_id")
    except Exception:
        pass

    # Add column
    con.execute("ALTER TABLE topo ADD COLUMN stand_id INTEGER")

    console.print("[cyan]Creating temporary join table (this may take several minutes)...[/cyan]")
    t0 = time.monotonic()

    # Use a more efficient approach: create a temporary table with the join results
    # then update the main table in one go
    con.execute("""
        CREATE TEMP TABLE topo_stand_mapping AS
        SELECT
            t.rowid as topo_rowid,
            s.global_stand_id
        FROM topo t
        JOIN stand s
        ON ST_Within(
            ST_Point(t.x_etrs, t.y_etrs),
            s.geometry
        )
    """)

    t_join = time.monotonic()
    console.print(f"[green]✓ Join completed in {t_join-t0:.1f}s[/green]")

    console.print("[cyan]Updating topo table...[/cyan]")

    # Update the topo table using the mapping
    con.execute("""
        UPDATE topo
        SET stand_id = m.global_stand_id
        FROM topo_stand_mapping m
        WHERE topo.rowid = m.topo_rowid
    """)

    t1 = time.monotonic()

    # Clean up temp table
    con.execute("DROP TABLE topo_stand_mapping")

    # Get statistics
    total_points = con.execute("SELECT COUNT(*) FROM topo").fetchone()[0]
    matched_points = con.execute("SELECT COUNT(*) FROM topo WHERE stand_id IS NOT NULL").fetchone()[0]
    match_percentage = (matched_points / total_points * 100) if total_points > 0 else 0

    console.print(f"[green]✓ Spatial join completed in {t1-t0:.1f}s total[/green]")
    console.print(f"  Total topo points: {total_points:,}")
    console.print(f"  Matched to stands: {matched_points:,} ({match_percentage:.1f}%)")
    console.print(f"  Unmatched points: {total_points - matched_points:,}")


if __name__ == "__main__":
    import sys

    sys.exit(import_forest_data())

# How to?

1. Download "Korkeusmalli 2M" geotiffs from MML
2. Extract the files to `data/korkeusmalli`
3. Run `uv run -m sienuri.generate_heightmap_pq --input-dir data/korkeusmalli/hila_2m/ --output-dir pq`
4. Run `uv run -m sienuri.download_forest_data --parquet-dir=pq --out-dir=forest`
5. Run `duckdb topo.duckdb -c "CREATE TABLE topo AS SELECT * FROM read_parquet('pq/*.parquet');"`
6. Run `uv run -m sienuri.import_forest_data --forest-dir forest/ --database topo.duckdb`

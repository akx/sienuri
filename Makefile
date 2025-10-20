.PHONY: topo.duckdb

topo.duckdb:
	uv run -m sienuri.generate_heightmap_pq --input-dir data/korkeusmalli/hila_2m/ --output-dir pq
	uv run -m sienuri.download_forest_data --parquet-dir=pq --out-dir=forest
	duckdb $@ -c "LOAD spatial; CREATE TABLE topo AS SELECT * FROM read_parquet('pq/*.parquet');"
	uv run -m sienuri.import_forest_data --forest-dir forest/ --database $@


#duckdb $@ -c "LOAD spatial; CREATE TABLE topo AS SELECT *, ST_Point(x_etrs, y_etrs) AS etrs_point FROM read_parquet('pq/*.parquet');"
# TODO: curiously this makes the join slower? : duckdb $@ -c "LOAD spatial; CREATE INDEX idx_topo_etrs_point ON topo USING rtree(etrs_point);"

import argparse
import multiprocessing
import pathlib
import time

import numpy as np
import pyarrow as pa
import rasterio
from pyproj import Transformer
from scipy.ndimage import gaussian_filter


def calculate_tpi(dem, radius_meters, *, cell_size):
    radius_cells = radius_meters / cell_size
    smoothed = gaussian_filter(dem, sigma=radius_cells)
    return dem - smoothed


def process_topo(source_file, *, name: str):
    src: rasterio.DatasetReader
    with rasterio.open(source_file) as src:
        dem = src.read(1)
        transform = src.transform
        crs = src.crs
        cell_size = transform[0]

    height, width = dem.shape

    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

    # TPI at multiple scales
    tpi_10m = calculate_tpi(dem, 10, cell_size=cell_size)
    tpi_20m = calculate_tpi(dem, 20, cell_size=cell_size)
    tpi_30m = calculate_tpi(dem, 30, cell_size=cell_size)
    dy, dx = np.gradient(dem, cell_size)
    slope = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
    aspect = (np.degrees(np.arctan2(-dx, dy)) + 360) % 360

    # Generate coordinate arrays
    rows, cols = np.meshgrid(range(height), range(width), indexing="ij")
    rows_flat = rows.ravel()
    cols_flat = cols.ravel()

    x_etrs = transform[2] + cols_flat * transform[0]
    y_etrs = transform[5] + rows_flat * transform[4]

    lon, lat = transformer.transform(x_etrs, y_etrs)

    return pa.table(
        {
            "name": pa.array([name] * (height * width), type=pa.string()),
            # "row": pa.array(rows_flat, type=pa.int32()),
            # "col": pa.array(cols_flat, type=pa.int32()),
            "x_etrs": pa.array(x_etrs, type=pa.int32()),
            "y_etrs": pa.array(y_etrs, type=pa.int32()),
            "lon": pa.array(lon, type=pa.float64()),
            "lat": pa.array(lat, type=pa.float64()),
            "elevation": pa.array(dem.ravel(), type=pa.float32()),
            "tpi_10m": pa.array(tpi_10m.ravel(), type=pa.float32()),
            "tpi_20m": pa.array(tpi_20m.ravel(), type=pa.float32()),
            "tpi_30m": pa.array(tpi_30m.ravel(), type=pa.float32()),
            "slope": pa.array(slope.ravel(), type=pa.float16()),
            "aspect": pa.array(aspect.ravel(), type=pa.float16()),
        }
    )


def generate_heightmap_pq() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True, type=pathlib.Path)
    ap.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = ap.parse_args()

    jobs = []

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for tiff in args.input_dir.rglob("*.tif"):
        out_path = (args.output_dir) / f"{tiff.stem}.parquet"
        if not out_path.exists():
            jobs.append((tiff, out_path))

    if not jobs:
        print("No new TIFF files to process.")
        return

    with multiprocessing.Pool() as pool:
        print(f"Processing {len(jobs)} TIFF files with {pool._processes} processes")
        pool.starmap(process_to_pq, jobs)


def process_to_pq(tiff_path: pathlib.Path, out_path: pathlib.Path):
    import pyarrow.parquet as pq

    t0 = time.monotonic()
    tab = process_topo(tiff_path, name=tiff_path.name)
    pq.write_table(tab, out_path, compression="zstd", use_dictionary=["name"])
    t1 = time.monotonic()
    print(f"Wrote {out_path} in {t1 - t0:.2f} seconds")


if __name__ == "__main__":
    generate_heightmap_pq()

import argparse
import multiprocessing
import pathlib
import time


def generate_heightmap_pq() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    jobs = []

    for tiff in pathlib.Path(args.input_dir).rglob("*.tif"):
        out_path = pathlib.Path(args.output_dir) / f"{tiff.stem}.parquet"
        if not out_path.exists():
            jobs.append((tiff, out_path))

    if not jobs:
        print("No new TIFF files to process.")
        return

    print(f"Processing {len(jobs)} TIFF files...")

    with multiprocessing.Pool() as pool:
        pool.starmap(process_to_pq, jobs)


def process_to_pq(tiff_path: pathlib.Path, out_path: pathlib.Path):
    import pyarrow.parquet as pq

    from sienuri.geo import process_topo

    t0 = time.monotonic()
    tab = process_topo(tiff_path, name=tiff_path.name)
    pq.write_table(tab, out_path, compression="snappy")
    t1 = time.monotonic()
    print(f"Wrote {out_path} in {t1 - t0:.2f} seconds")


if __name__ == "__main__":
    generate_heightmap_pq()

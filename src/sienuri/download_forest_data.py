import argparse
import pathlib
import zipfile
from contextlib import closing
from io import BytesIO

import pycurl


def download_forest_data():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet-dir", required=True, type=pathlib.Path)
    ap.add_argument("--out-dir", required=True, type=pathlib.Path)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    skipped = set()
    downloaded = set()
    with closing(pycurl.Curl()) as c:
        for parquet_path in args.parquet_dir.rglob("*.parquet"):
            url = f"https://avoin.metsakeskus.fi/aineistot/Metsavarakuviot/Karttalehti/MV_{parquet_path.stem}.zip"
            gpkg_filename = args.out_dir / f"MV_{parquet_path.stem}.gpkg"
            if gpkg_filename.exists():
                skipped.add(gpkg_filename)
                continue
            buffer = BytesIO()
            c.setopt(c.URL, url)
            c.setopt(c.FOLLOWLOCATION, True)
            c.setopt(c.WRITEDATA, buffer)
            c.perform()
            with zipfile.ZipFile(buffer) as zf:
                for name in zf.namelist():
                    if name.endswith(".gpkg"):
                        print(f"Extracting {gpkg_filename} from {url}")
                        zf.extract(name, args.out_dir)
                        downloaded.add(gpkg_filename)
    print(f"Downloaded {len(downloaded)} files, skipped {len(skipped)} existing files.")


if __name__ == "__main__":
    download_forest_data()

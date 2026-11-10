#!/usr/bin/env python
"""Download, index and cache the four chest radiograph collections.

Examples (run from the repository root):

    python scripts/prepare_data.py download all --metadata-only   # small files only
    python scripts/prepare_data.py download nih rsna covid kermany  # full release
    python scripts/prepare_data.py index all
    python scripts/prepare_data.py cache all --size 512 --limit 100  # timing probe
    python scripts/prepare_data.py cache all --size 512

Data goes to $CHEST_OVERLAP_DATA, else $HPCWORK/chest_overlap, else ./data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chest_overlap.config import COLLECTIONS, data_root, get_collection  # noqa: E402


def _keys(names: list[str]) -> list[str]:
    if not names or names == ["all"]:
        return list(COLLECTIONS)
    for n in names:
        get_collection(n)
    return names


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", help="override the data folder")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="download from Kaggle and write provenance manifests")
    d.add_argument("collections", nargs="*", default=["all"], help=f"any of {list(COLLECTIONS)} or 'all'")
    d.add_argument("--metadata-only", action="store_true", help="only the CSV/list files, no images")
    d.add_argument("--force", action="store_true", help="download again even if present")
    d.add_argument("--keep-zip", action="store_true", help="keep the Kaggle zip after extracting")
    d.add_argument("--no-checksum", action="store_true", help="skip the per-file SHA-256 manifest")

    i = sub.add_parser("index", help="build the per-collection image index CSVs")
    i.add_argument("collections", nargs="*", default=["all"])
    i.add_argument("--no-dicom-headers", action="store_true", help="skip reading RSNA DICOM headers")

    c = sub.add_parser("cache", help="write the reduced-resolution working cache")
    c.add_argument("collections", nargs="*", default=["all"])
    c.add_argument("--size", type=int, default=512, help="longer image side in pixels (default 512)")
    c.add_argument("--limit", type=int, help="random sample of N images per collection (timing probe)")
    c.add_argument("--workers", type=int, help="processes (default: $SLURM_CPUS_PER_TASK or all cores)")
    c.add_argument("--overwrite", action="store_true")

    sub.add_parser("info", help="list the collections and the data folder")

    args = p.parse_args(argv)
    root = data_root(args.data_root)

    if args.cmd == "info":
        print(f"data root: {root}")
        for col in COLLECTIONS.values():
            print(f"- {col.key:8s} {col.name}\n  {col.kaggle_url}\n  {col.approx_size}\n  {col.notes}")
        return 0

    failures = []
    for key in _keys(args.collections):
        try:
            if args.cmd == "download":
                from chest_overlap.download import download_collection

                download_collection(
                    get_collection(key), root,
                    metadata_only=args.metadata_only, force=args.force,
                    keep_zip=args.keep_zip, checksums=not args.no_checksum,
                )
            elif args.cmd == "index":
                from chest_overlap.inventory import build_index

                build_index(key, root, dicom_headers=not args.no_dicom_headers)
            elif args.cmd == "cache":
                from chest_overlap.cache import build_cache
                from chest_overlap.inventory import load_index

                build_cache(
                    load_index([key], root), root, size=args.size,
                    limit=args.limit, workers=args.workers, overwrite=args.overwrite,
                )
        except Exception as exc:  # noqa: BLE001 - continue with the other collections
            print(f"\n!! {key}: {exc}", file=sys.stderr)
            failures.append(key)

    if failures:
        print(f"\nFailed: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

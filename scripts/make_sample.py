#!/usr/bin/env python
"""Copy a small, reproducible sample of cached images into data/sample/ for git.

The sample lets teammates develop and time the next stages (controls, matchers)
right after cloning, without downloading anything. It is drawn by patient so
that patient-level tests have something to work with:

* patients with images on both sides of the official split (cross-split),
* patients with several images inside one split (same-patient pairs),
* single-image patients (different-patient pairs for the negative control),

and the remainder is filled at random. The draw is fixed by --seed.

    python scripts/make_sample.py                       # kermany, 100 images, 512 px
    python scripts/make_sample.py kermany --n 100 --seed 0

Output:
    data/sample/<collection>_<n>/images/<cache_rel_path>   cached 8-bit PNGs
    data/sample/<collection>_<n>/index.csv                 index rows + cache columns
                                                           + sample_reason, sample_rel_path
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chest_overlap.config import data_root, get_collection  # noqa: E402
from chest_overlap.inventory import load_index  # noqa: E402


def pick_patients(pool: pd.Series, k: int, rng: np.random.Generator) -> list[str]:
    ids = sorted(pool.unique())
    return list(rng.choice(ids, size=min(k, len(ids)), replace=False)) if ids else []


def draw(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Return about ``n`` rows of ``df`` with a ``sample_reason`` column."""
    rng = np.random.default_rng(seed)
    df = df[df["patient_id"] != ""]
    groups = df.groupby("patient_id")
    n_img = groups.size()
    n_split = groups["split"].nunique()

    cross = n_img.index[(n_split > 1)]
    multi = n_img.index[(n_img >= 2) & (n_split == 1)]
    single = n_img.index[n_img == 1]

    chosen: list[pd.DataFrame] = []

    def take(patients, reason, per_patient):
        for pid in patients:
            rows = df[df["patient_id"] == pid].sample(frac=1, random_state=int(rng.integers(1 << 31)))
            if reason == "cross_split":
                # one image per split side, evaluation side first, so the pair straddles the split
                rows = rows.sort_values("is_eval", ascending=False, kind="stable").groupby("split").head(1)
            chosen.append(rows.head(per_patient).assign(sample_reason=reason))

    # About 1/4 cross-split, 1/3 multi-image, then singles; capped at 2–3 images per patient.
    take(pick_patients(pd.Series(cross), max(1, n // 10), rng), "cross_split", 2)
    take(pick_patients(pd.Series(multi), max(1, n // 6), rng), "same_patient", 2)
    out = pd.concat(chosen) if chosen else df.iloc[:0]
    rest = n - len(out)
    if rest > 0:
        singles = df[df["patient_id"].isin(single)]
        out = pd.concat([out, singles.sample(n=min(rest, len(singles)), random_state=seed)
                         .assign(sample_reason="single_image")])
    return out.head(n)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("collection", nargs="?", default="kermany")
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--size", type=int, default=512, help="cache resolution to copy from")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--data-root")
    args = p.parse_args(argv)

    get_collection(args.collection)
    root = data_root(args.data_root)
    cache_dir = root / "cache" / str(args.size) / args.collection
    cache_csv = root / "cache" / str(args.size) / f"{args.collection}_cache.csv"
    if not cache_csv.exists():
        raise SystemExit(f"No cache table at {cache_csv}. Run: python scripts/prepare_data.py cache {args.collection}")

    index = load_index([args.collection], root)
    cache = pd.read_csv(cache_csv, keep_default_na=False)
    cache = cache[cache["error"] == ""].drop(columns="error")
    df = index.merge(cache, on="image_id", how="inner")

    sample = draw(df, args.n, args.seed).sort_values("image_id").reset_index(drop=True)
    out = root / "sample" / f"{args.collection}_{args.n}"
    if out.exists():
        shutil.rmtree(out)
    for rel in sample["cache_rel_path"]:
        dst = out / "images" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cache_dir / rel, dst)
    sample["sample_rel_path"] = "images/" + sample["cache_rel_path"]
    sample.to_csv(out / "index.csv", index=False)

    size_mb = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1e6
    print(f"sample written: {out}  ({len(sample)} images, {sample['patient_id'].nunique()} patients, {size_mb:.1f} MB)")
    print("  by reason: " + str(sample["sample_reason"].value_counts().to_dict()))
    print("  by split:  " + str(sample["split"].value_counts().to_dict()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Reduced-resolution working cache of every indexed image.

Conversion applied to every image, identical for all collections:

1. Decode to one grey channel.
   * DICOM: pixel data -> Modality LUT (slope/intercept) -> MONOCHROME1 inverted
     so that bone is bright -> linear map of the stored bit range
     [0, 2**BitsStored - 1] to [0, 255]. No VOI window is applied, so the cache
     keeps the full stored range.
   * PNG/JPEG: 8-bit grey stays as is; RGB/RGBA -> luma (ITU-R 601-2, Pillow "L");
     16-bit grey -> top 8 bits.
2. Resize so that the longer side equals ``size`` (aspect ratio kept, no
   padding or cropping) with area interpolation (cv2.INTER_AREA). Images that
   are already smaller are not enlarged.
3. Save as lossless 8-bit PNG under ``cache/<size>/<collection>/<rel_path>.png``.

Original size, mode and bit depth go to ``cache/<size>/<collection>_cache.csv``.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm


def load_gray8(path: Path) -> tuple[np.ndarray, dict]:
    """Decode an image file to a 2-D uint8 array, with a note of what was done."""
    if path.suffix.lower() == ".dcm":
        import pydicom
        from pydicom.pixels import apply_modality_lut

        ds = pydicom.dcmread(path)
        arr = apply_modality_lut(ds.pixel_array, ds).astype(np.float64)
        bits = int(ds.get("BitsStored", 8))
        top = float(2**bits - 1)
        if str(ds.get("PhotometricInterpretation", "")).upper() == "MONOCHROME1":
            arr = top - arr
        img = np.clip(np.rint(arr / top * 255.0), 0, 255).astype(np.uint8)
        info = {"orig_mode": str(ds.get("PhotometricInterpretation", "")), "orig_bits": bits}
    else:
        with Image.open(path) as im:
            mode = im.mode
            if mode in ("I;16", "I;16B", "I;16L", "I"):
                a = np.asarray(im, dtype=np.uint32)
                img = (a >> 8).clip(0, 255).astype(np.uint8)
                bits = 16
            else:
                img = np.asarray(im.convert("L"), dtype=np.uint8)
                bits = 8
        info = {"orig_mode": mode, "orig_bits": bits}
    if img.ndim == 3:  # multi-frame or odd DICOM; keep first plane
        img = img[..., 0] if img.shape[-1] in (3, 4) else img[0]
    info["orig_height"], info["orig_width"] = img.shape
    return img, info


def resize_long_side(img: np.ndarray, size: int) -> np.ndarray:
    h, w = img.shape
    scale = size / max(h, w)
    if scale >= 1.0:
        return img
    new = (max(1, round(w * scale)), max(1, round(h * scale)))
    return cv2.resize(img, new, interpolation=cv2.INTER_AREA)


def _work(args: tuple[str, str, str, int]) -> dict:
    image_id, src, dst, size = args
    row = {"image_id": image_id}
    try:
        img, info = load_gray8(Path(src))
        small = resize_long_side(img, size)
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(dst, small)
        row.update(info, cache_height=small.shape[0], cache_width=small.shape[1], error="")
    except Exception as exc:  # noqa: BLE001 - record and continue
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def default_workers() -> int:
    """Use the cores Slurm gave the job, else all local cores."""
    return int(os.environ.get("SLURM_CPUS_PER_TASK") or os.cpu_count() or 1)


def build_cache(
    index: pd.DataFrame,
    root: Path,
    size: int = 512,
    limit: int | None = None,
    workers: int | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    key = index["collection"].iloc[0]
    raw_dir = root / "raw" / key
    out_dir = root / "cache" / str(size) / key
    todo = index[index["rel_path"] != ""]
    if limit:
        todo = todo.sample(n=min(limit, len(todo)), random_state=0)

    jobs, rel_paths = [], {}
    for image_id, rel in zip(todo["image_id"], todo["rel_path"]):
        dst_rel = str(Path(rel).with_suffix(".png").as_posix())
        rel_paths[image_id] = dst_rel
        dst = out_dir / dst_rel
        if overwrite or not dst.exists():
            jobs.append((image_id, str(raw_dir / rel), str(dst), size))

    workers = workers or default_workers()
    print(f"\n=== cache {key}: {len(todo):,} images ({len(jobs):,} to convert) at {size}px, {workers} workers")
    t0 = time.perf_counter()
    rows = []
    if jobs:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for r in tqdm(pool.map(_work, jobs, chunksize=64), total=len(jobs), unit="img"):
                rows.append(r)
    dt = time.perf_counter() - t0
    if jobs:
        print(f"  {len(jobs) / dt:.1f} images/s ({dt:.1f} s)")

    # Merge with any earlier run so the table always covers the whole cache.
    table = root / "cache" / str(size) / f"{key}_cache.csv"
    new = pd.DataFrame(rows)
    if table.exists() and not overwrite:
        old = pd.read_csv(table, keep_default_na=False)
        new = pd.concat([old, new], ignore_index=True).drop_duplicates("image_id", keep="last")
    if not new.empty:
        new["cache_rel_path"] = new["image_id"].map(rel_paths).fillna(new.get("cache_rel_path", ""))
        table.parent.mkdir(parents=True, exist_ok=True)
        new.to_csv(table, index=False)
        n_err = (new["error"] != "").sum()
        print(f"  table: {table}  ({len(new):,} rows, {n_err} errors)")
    return new

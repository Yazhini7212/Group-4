"""Small helpers for looking at images in a Jupyter notebook.

    from chest_overlap import load_index, show_rows
    df = load_index(["nih"])
    show_rows(df.head(8))            # 8 images in a grid, titled with their ids
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .cache import load_gray8
from .config import data_root


def image_path(row: pd.Series, size: int | None = 512, root: Path | str | None = None) -> Path:
    """Path of an image: the cached copy if it exists, otherwise the original file."""
    root = data_root(root)
    if size:
        cached = root / "cache" / str(size) / row["collection"] / Path(row["rel_path"]).with_suffix(".png")
        if cached.exists():
            return cached
    if not row["rel_path"]:
        raise FileNotFoundError(f"{row['image_id']} is listed in the index but not downloaded")
    return root / "raw" / row["collection"] / row["rel_path"]


def load_image(row: pd.Series, size: int | None = 512, root: Path | str | None = None) -> np.ndarray:
    """Load one image (one row of an index table) as a 2-D uint8 array, 0 = black, 255 = white."""
    img, _ = load_gray8(image_path(row, size, root))
    return img


def show(images: list[np.ndarray], titles: list[str] | None = None, cols: int = 4, width: float = 3.0):
    """Show a list of greyscale arrays side by side."""
    import matplotlib.pyplot as plt

    n = len(images)
    if n == 0:
        print("nothing to show")
        return None
    cols = min(cols, n)
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(width * cols, width * rows), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for i, img in enumerate(images):
        ax = axes.flat[i]
        ax.imshow(img, cmap="gray", vmin=0, vmax=255)
        if titles:
            ax.set_title(titles[i], fontsize=8)
    fig.tight_layout()
    return fig


def show_rows(df: pd.DataFrame, size: int | None = 512, root: Path | str | None = None, cols: int = 4):
    """Show the images of the given index rows (skips rows whose file is not on disk)."""
    images, titles = [], []
    for _, row in df.iterrows():
        try:
            images.append(load_image(row, size, root))
            titles.append(row["image_id"])
        except FileNotFoundError as exc:
            print(f"skipped: {exc}")
    return show(images, titles, cols=cols)

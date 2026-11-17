"""Image-level and patient-level overlap across public chest radiograph collections.

Everything you normally need in a notebook can be imported from here:

    from chest_overlap import data_root, load_index, show_rows
"""

from .cache import build_cache, load_gray8, resize_long_side
from .config import COLLECTIONS, data_root, get_collection
from .download import download_collection
from .inventory import build_index, load_index
from .viewer import image_path, load_image, show, show_rows

__all__ = [
    "COLLECTIONS", "data_root", "get_collection",
    "download_collection", "build_index", "load_index",
    "build_cache", "load_gray8", "resize_long_side",
    "image_path", "load_image", "show", "show_rows",
]

"""Build one image index per collection from the metadata each release distributes.

Every index has the same core columns, so the four collections can be compared
directly:

    collection   short key (nih, rsna, covid, kermany)
    image_id     "<collection>/<file name without extension>", unique across collections
    rel_path     path of the image relative to raw/<collection>/ (empty if not downloaded)
    patient_id   "<collection>:<id>" as distributed by the release, empty if none exists
    split        official split name (train_val/test, train/test, train/val/test), empty if none
    is_eval      True when the image is on the evaluation side of the official split
    subset       sub-folder the release groups the image under (covid, kermany)

plus collection-specific provenance columns (see the per-collection functions).

No disease label is carried into the index: the project uses none.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from .config import COLLECTIONS

CORE_COLUMNS = ["collection", "image_id", "rel_path", "patient_id", "split", "is_eval", "subset"]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".dcm"}


def _files_by_name(raw_dir: Path, suffixes: set[str], exclude_parts: set[str] = frozenset()) -> dict[str, Path]:
    """Map file name -> path for every image file below ``raw_dir``."""
    found: dict[str, Path] = {}
    for p in raw_dir.rglob("*"):
        if p.suffix.lower() in suffixes and p.is_file() and not (set(p.parts) & exclude_parts):
            found.setdefault(p.name, p)
    return found


def _rel(p: Path | None, raw_dir: Path) -> str:
    return p.relative_to(raw_dir).as_posix() if p is not None else ""


# --------------------------------------------------------------------------- #
# NIH ChestX-ray14
# --------------------------------------------------------------------------- #
def index_nih(raw_dir: Path) -> pd.DataFrame:
    entry = raw_dir / "Data_Entry_2017.csv"
    if not entry.exists():
        raise FileNotFoundError(f"{entry} missing. Run: python scripts/prepare_data.py download nih --metadata-only")
    meta = pd.read_csv(entry)
    meta.columns = [c.strip() for c in meta.columns]

    def read_list(name: str) -> set[str]:
        path = raw_dir / name
        return set(path.read_text().split()) if path.exists() else set()

    train_val, test = read_list("train_val_list.txt"), read_list("test_list.txt")
    files = _files_by_name(raw_dir, {".png"})

    names = meta["Image Index"]
    split = names.map(lambda n: "test" if n in test else ("train_val" if n in train_val else ""))
    df = pd.DataFrame(
        {
            "collection": "nih",
            "image_id": "nih/" + names.str.replace(r"\.png$", "", regex=True),
            "rel_path": names.map(lambda n: _rel(files.get(n), raw_dir)),
            "patient_id": "nih:" + meta["Patient ID"].astype(int).map("{:08d}".format),
            "split": split,
            "is_eval": split == "test",
            "subset": "",
            "file_name": names,
            "follow_up": meta["Follow-up #"],
            "view_position": meta["View Position"],
            "sex": meta["Patient Gender"],
            "age": meta["Patient Age"],
            "orig_width": meta["OriginalImage[Width"],
            "orig_height": meta["Height]"],
            "pixel_spacing_x": meta["OriginalImagePixelSpacing[x"],
            "pixel_spacing_y": meta["y]"],
        }
    )
    return df


# --------------------------------------------------------------------------- #
# RSNA Pneumonia Detection Challenge (DICOM)
# --------------------------------------------------------------------------- #
DICOM_FIELDS = [
    "Rows", "Columns", "BitsAllocated", "BitsStored", "HighBit", "PixelRepresentation",
    "PhotometricInterpretation", "SamplesPerPixel", "WindowCenter", "WindowWidth",
    "RescaleSlope", "RescaleIntercept", "PixelSpacing", "ViewPosition", "Modality",
    "PatientID", "PatientSex", "PatientAge",
]


def read_dicom_header(path: Path) -> dict:
    """Header fields relevant to intensity handling (bit depth, photometry, windows, LUTs)."""
    import pydicom

    ds = pydicom.dcmread(path, stop_before_pixels=True)
    out = {}
    for f in DICOM_FIELDS:
        v = ds.get(f, None)
        out[f"dcm_{f}"] = "" if v is None else str(v)
    out["dcm_has_VOILUTSequence"] = "VOILUTSequence" in ds
    out["dcm_has_ModalityLUTSequence"] = "ModalityLUTSequence" in ds
    tsuid = getattr(getattr(ds, "file_meta", None), "TransferSyntaxUID", None)
    out["dcm_TransferSyntaxUID"] = str(tsuid) if tsuid else ""
    return out


def index_rsna(raw_dir: Path, dicom_headers: bool = True) -> pd.DataFrame:
    files = _files_by_name(raw_dir, {".dcm"})
    labels = raw_dir / "stage_2_train_labels.csv"
    train_ids = set(pd.read_csv(labels)["patientId"]) if labels.exists() else set()

    rows = []
    for name, p in files.items():
        parent = p.parent.name.lower()
        split = "test" if "test" in parent else ("train" if "train" in parent else "")
        rows.append({"rsna_id": p.stem, "rel_path": _rel(p, raw_dir), "split": split})
    known = {r["rsna_id"] for r in rows}
    # Images listed in the label file but not (yet) downloaded.
    for pid in sorted(train_ids - known):
        rows.append({"rsna_id": pid, "rel_path": "", "split": "train"})
    if not rows:
        raise FileNotFoundError(
            f"No DICOM files or stage_2_train_labels.csv in {raw_dir}. "
            "Run: python scripts/prepare_data.py download rsna"
        )
    df = pd.DataFrame(rows)

    # Documented correspondence to ChestX-ray14 (positive control).
    mapping_path = raw_dir / "pneumonia-challenge-dataset-mappings_2018.json"
    if mapping_path.exists():
        mapping = pd.DataFrame(json.loads(mapping_path.read_text()))
        mapping = mapping[["subset_img_id", "img_id"]].rename(
            columns={"subset_img_id": "rsna_id", "img_id": "linked_nih_file"}
        )
        df = df.merge(mapping.drop_duplicates("rsna_id"), on="rsna_id", how="left")
        df["linked_nih_file"] = df["linked_nih_file"].fillna("")
        df["linked_nih_image_id"] = df["linked_nih_file"].map(
            lambda f: "nih/" + f.rsplit(".", 1)[0] if f else ""
        )
        df["linked_nih_patient_id"] = df["linked_nih_file"].map(lambda f: "nih:" + f[:8] if f else "")
    else:
        print("  RSNA->NIH mapping file not found; linked_nih_* columns left empty")
        for c in ("linked_nih_file", "linked_nih_image_id", "linked_nih_patient_id"):
            df[c] = ""

    df.insert(0, "collection", "rsna")
    df.insert(1, "image_id", "rsna/" + df["rsna_id"])
    # The release's patientId is unique per image; it is kept as distributed.
    df["patient_id"] = "rsna:" + df["rsna_id"]
    df["is_eval"] = df["split"] == "test"
    df["subset"] = ""
    df["file_name"] = df["rel_path"].map(lambda r: Path(r).name if r else "")

    if dicom_headers:
        present = df["rel_path"] != ""
        headers = [
            read_dicom_header(raw_dir / r)
            for r in tqdm(df.loc[present, "rel_path"], desc="DICOM headers", unit="file")
        ]
        if headers:
            hdr = pd.DataFrame(headers, index=df.index[present])
            df = df.join(hdr)
    return df


# --------------------------------------------------------------------------- #
# COVID-19 Radiography Database
# --------------------------------------------------------------------------- #
def index_covid(raw_dir: Path) -> pd.DataFrame:
    rows = []
    for p in raw_dir.rglob("*"):
        if p.suffix.lower() not in IMAGE_SUFFIXES or not p.is_file():
            continue
        if "masks" in {part.lower() for part in p.parts}:
            continue  # lung masks, not radiographs
        # Layout: <class>/images/<file>.png (older versions: <class>/<file>.png)
        subset = p.parent.parent.name if p.parent.name.lower() == "images" else p.parent.name
        rows.append({"rel_path": _rel(p, raw_dir), "subset": subset, "file_name": p.name})
    if not rows:
        raise FileNotFoundError(f"No images in {raw_dir}. Run: python scripts/prepare_data.py download covid")
    df = pd.DataFrame(rows)

    # Per-class metadata sheets list the upstream source of every image.
    sheets = []
    for x in raw_dir.rglob("*.metadata.xlsx"):
        m = pd.read_excel(x)
        m.columns = [str(c).strip().upper() for c in m.columns]
        if "FILE NAME" in m.columns:
            m["key"] = m["FILE NAME"].astype(str).str.strip().str.lower().str.replace(r"\.\w+$", "", regex=True)
            sheets.append(m)
    if sheets:
        meta = pd.concat(sheets, ignore_index=True).drop_duplicates("key")
        meta = meta.rename(columns={"URL": "source_url", "FORMAT": "source_format", "SIZE": "source_size"})
        keep = ["key"] + [c for c in ("source_url", "source_format", "source_size") if c in meta.columns]
        df["key"] = df["file_name"].str.lower().str.replace(r"\.\w+$", "", regex=True)
        df = df.merge(meta[keep], on="key", how="left").drop(columns="key")

    df.insert(0, "collection", "covid")
    df.insert(1, "image_id", "covid/" + df["file_name"].str.replace(r"\.\w+$", "", regex=True))
    df["patient_id"] = ""  # the release distributes no patient identifier
    df["split"] = ""  # and no official split
    df["is_eval"] = False
    return df


# --------------------------------------------------------------------------- #
# Kermany pediatric chest X-ray
# --------------------------------------------------------------------------- #
_KERMANY_PATIENT = [
    re.compile(r"^(person\d+)_", re.I),            # person1_bacteria_1.jpeg
    re.compile(r"^(NORMAL2-IM-\d+)-\d+", re.I),     # NORMAL2-IM-1427-0001.jpeg
    re.compile(r"^(IM-\d+)-\d+", re.I),             # IM-0115-0001.jpeg
]


def kermany_patient(file_name: str) -> str:
    for pat in _KERMANY_PATIENT:
        m = pat.match(file_name)
        if m:
            return m.group(1)
    return ""


def index_kermany(raw_dir: Path) -> pd.DataFrame:
    # The Kaggle archive holds the release twice (chest_xray/ and chest_xray/chest_xray/)
    # plus __MACOSX resource forks. Index the shallowest folder that has a train/ split.
    candidates = [
        d.parent for d in raw_dir.rglob("train")
        if d.is_dir() and "__MACOSX" not in d.parts
    ]
    if not candidates:
        raise FileNotFoundError(f"No train/ folder under {raw_dir}. Run: python scripts/prepare_data.py download kermany")
    root = min(candidates, key=lambda d: len(d.parts))
    others = [c for c in candidates if c != root]
    if others:
        print(f"  kermany: indexing {root.relative_to(raw_dir)}; ignoring duplicate copies {[str(o.relative_to(raw_dir)) for o in others]}")

    rows = []
    for split in ("train", "val", "test"):
        for p in (root / split).rglob("*"):
            if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file() and not p.name.startswith("._"):
                pid = kermany_patient(p.name)
                rows.append(
                    {
                        "rel_path": _rel(p, raw_dir),
                        "split": split,
                        "subset": p.parent.name,
                        "file_name": p.name,
                        "patient_id": f"kermany:{pid}" if pid else "",
                    }
                )
    df = pd.DataFrame(rows)
    df.insert(0, "collection", "kermany")
    df.insert(1, "image_id", "kermany/" + df["split"] + "/" + df["subset"] + "/" + df["file_name"].str.replace(r"\.\w+$", "", regex=True))
    df["is_eval"] = df["split"] == "test"
    return df


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
INDEXERS = {"nih": index_nih, "rsna": index_rsna, "covid": index_covid, "kermany": index_kermany}


def _order(df: pd.DataFrame) -> pd.DataFrame:
    rest = [c for c in df.columns if c not in CORE_COLUMNS]
    return df[CORE_COLUMNS + rest]


def build_index(key: str, root: Path, dicom_headers: bool = True) -> pd.DataFrame:
    raw_dir = root / "raw" / key
    print(f"\n=== indexing {COLLECTIONS[key].name} from {raw_dir}")
    if key == "rsna":
        df = index_rsna(raw_dir, dicom_headers=dicom_headers)
    else:
        df = INDEXERS[key](raw_dir)
    df = _order(df).sort_values("image_id").reset_index(drop=True)
    if df["image_id"].duplicated().any():
        dups = df.loc[df["image_id"].duplicated(keep=False), "image_id"].unique()[:5]
        raise ValueError(f"{key}: duplicate image ids, e.g. {list(dups)}")

    out = root / "index" / f"{key}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(summarize(df))
    print(f"  written: {out}")
    return df


def summarize(df: pd.DataFrame) -> str:
    present = (df["rel_path"] != "").sum()
    patients = df.loc[df["patient_id"] != "", "patient_id"].nunique()
    splits = df["split"].replace("", "(none)").value_counts().to_dict()
    lines = [
        f"  images listed: {len(df):,}   files on disk: {present:,}",
        f"  distinct patient ids: {patients:,}" if patients else "  patient ids: none distributed",
        f"  official split: {splits}",
    ]
    if "linked_nih_image_id" in df:
        lines.append(f"  linked to ChestX-ray14 by RSNA mapping: {(df['linked_nih_image_id'] != '').sum():,}")
    return "\n".join(lines)


def load_index(collections: list[str] | None = None, root: Path | None = None) -> pd.DataFrame:
    """Load the per-collection indexes written by :func:`build_index` into one frame."""
    from .config import data_root

    root = data_root(root)
    keys = collections or list(COLLECTIONS)
    frames = []
    for k in keys:
        path = root / "index" / f"{k}.csv"
        if path.exists():
            frames.append(pd.read_csv(path, dtype={"patient_id": str, "rel_path": str}, keep_default_na=False))
        else:
            print(f"  (no index for {k} at {path})")
    if not frames:
        raise FileNotFoundError(f"No index files under {root / 'index'}; run prepare_data.py index first")
    return pd.concat(frames, ignore_index=True, sort=False)

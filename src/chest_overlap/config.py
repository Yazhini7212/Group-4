"""Registry of the four public chest radiograph collections used in the project.

Every collection is fetched from Kaggle (the only access requirement named in the
project brief). The registry records where each collection comes from, which
small metadata files can be fetched on their own, and the reference paper.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def data_root(override: str | os.PathLike | None = None) -> Path:
    """Root folder for all downloaded and derived data.

    Priority: explicit argument > CHEST_OVERLAP_DATA environment variable >
    ``$HPCWORK/chest_overlap`` (RWTH cluster, large Lustre file system) >
    ``<repo>/data``. The full downloads are ~50 GB, so on the cluster they must
    not go to $HOME.
    """
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("CHEST_OVERLAP_DATA")
    if env:
        return Path(env).expanduser().resolve()
    hpcwork = os.environ.get("HPCWORK")
    if hpcwork:
        return Path(hpcwork).expanduser().resolve() / "chest_overlap"
    return REPO_ROOT / "data"


@dataclass(frozen=True)
class Collection:
    key: str
    name: str
    kaggle_kind: str  # "dataset" or "competition"
    kaggle_ref: str
    reference: str
    approx_size: str
    # Small files that can be downloaded without the image archive.
    metadata_files: tuple[str, ...] = ()
    # Extra public files fetched over plain HTTPS (filename -> url).
    extra_urls: dict[str, str] = field(default_factory=dict)
    notes: str = ""

    @property
    def kaggle_url(self) -> str:
        if self.kaggle_kind == "competition":
            return f"https://www.kaggle.com/competitions/{self.kaggle_ref}"
        return f"https://www.kaggle.com/datasets/{self.kaggle_ref}"


COLLECTIONS: dict[str, Collection] = {
    "nih": Collection(
        key="nih",
        name="NIH ChestX-ray14",
        kaggle_kind="dataset",
        kaggle_ref="nih-chest-xrays/data",
        reference="Wang et al., CVPR 2017. doi:10.1109/CVPR.2017.369",
        approx_size="~45 GB (112,120 PNG images, 1024x1024, 8-bit)",
        metadata_files=(
            "Data_Entry_2017.csv",
            "train_val_list.txt",
            "test_list.txt",
            "BBox_List_2017.csv",
        ),
        notes="Official patient-wise split in train_val_list.txt / test_list.txt.",
    ),
    "rsna": Collection(
        key="rsna",
        name="RSNA Pneumonia Detection Challenge (DICOM)",
        kaggle_kind="competition",
        kaggle_ref="rsna-pneumonia-detection-challenge",
        reference="Shih et al., Radiol Artif Intell 2019. doi:10.1148/ryai.2019180041",
        approx_size="~3.7 GB (30,227 DICOM images)",
        metadata_files=(
            "stage_2_train_labels.csv",
            "stage_2_detailed_class_info.csv",
        ),
        extra_urls={
            # Published by RSNA: maps every challenge image back to its
            # ChestX-ray14 file name. This is the documented positive control.
            "pneumonia-challenge-dataset-mappings_2018.json": (
                "https://s3.amazonaws.com/east1.public.rsna.org/AI/2018/"
                "pneumonia-challenge-dataset-mappings_2018.json"
            ),
        },
        notes=(
            "You must accept the competition rules on kaggle.com once before "
            "the API can download it. patientId is unique per image, so the "
            "NIH patient is recovered through the RSNA mapping file."
        ),
    ),
    "covid": Collection(
        key="covid",
        name="COVID-19 Radiography Database",
        kaggle_kind="dataset",
        kaggle_ref="tawsifurrahman/covid19-radiography-database",
        reference="Chowdhury et al., IEEE Access 2020. doi:10.1109/ACCESS.2020.3010287",
        approx_size="~0.8 GB (21,165 PNG images, 299x299)",
        notes="No patient identifiers and no official split; per-image source URL in metadata.",
    ),
    "kermany": Collection(
        key="kermany",
        name="Pediatric chest X-ray (Kermany et al.)",
        kaggle_kind="dataset",
        kaggle_ref="paultimothymooney/chest-xray-pneumonia",
        reference="Kermany et al., Cell 2018. doi:10.1016/j.cell.2018.02.010",
        approx_size="~1.2 GB (5,856 JPEG images)",
        notes=(
            "Patient id is encoded in the file name. The Kaggle archive contains "
            "a second nested copy (chest_xray/chest_xray) and __MACOSX files; "
            "only the top-level copy is indexed."
        ),
    ),
}


def get_collection(key: str) -> Collection:
    try:
        return COLLECTIONS[key]
    except KeyError:
        raise SystemExit(
            f"Unknown collection '{key}'. Choose from: {', '.join(COLLECTIONS)}"
        ) from None

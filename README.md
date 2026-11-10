# Group-4
Image-Level and Patient-Level Overlap Across Public Chest Radiograph Collections

## Data

The four collections from the project brief, all from Kaggle:

| key       | Collection                                   | Kaggle source                                         | Size     | Patient IDs | Official split |
|-----------|----------------------------------------------|-------------------------------------------------------|----------|-------------|----------------|
| `nih`     | NIH ChestX-ray14 (Wang et al. 2017)          | `nih-chest-xrays/data`                                | ~45 GB   | yes         | train_val / test |
| `rsna`    | RSNA Pneumonia Detection Challenge, DICOM (Shih et al. 2019) | competition `rsna-pneumonia-detection-challenge` | ~3.7 GB | per image only | stage 2 train / test |
| `covid`   | COVID-19 Radiography Database (Chowdhury et al. 2020) | `tawsifurrahman/covid19-radiography-database` | ~0.8 GB  | none        | none           |
| `kermany` | Pediatric chest X-ray (Kermany et al. 2018)  | `paultimothymooney/chest-xray-pneumonia`              | ~1.2 GB  | from file name | train / val / test |

For RSNA the code also downloads RSNA's public mapping file
(`pneumonia-challenge-dataset-mappings_2018.json`), which links every challenge image to its
ChestX-ray14 file. That gives the documented **positive control** (columns
`linked_nih_image_id`, `linked_nih_patient_id` in the RSNA index).

## Running on the RWTH cluster

Data goes to `$HPCWORK/chest_overlap` (override with `CHEST_OVERLAP_DATA` or `--data-root`).
Nothing is stored in the repository or in `$HOME`.

```bash
# 1. once, on a login node, from the repo root
bash scripts/hpc/setup_env.sh
#    then put your Kaggle token in ~/.kaggle/kaggle.json (chmod 600)
#    and accept the RSNA competition rules on kaggle.com

# 2. download + index (Slurm job; edit the --account line first if your course needs one)
sbatch scripts/hpc/download.sbatch            # or: sbatch scripts/hpc/download.sbatch covid kermany

# 3. timing probe on 100 images per collection, then the full cache
sbatch scripts/hpc/cache.sbatch --limit 100
sbatch scripts/hpc/cache.sbatch --size 512
```

If compute nodes cannot reach the internet, run the download step on a login node instead
(inside `tmux`/`screen`):
`python scripts/prepare_data.py download all && python scripts/prepare_data.py index all`.

## What gets written

```
$HPCWORK/chest_overlap/
  raw/<key>/...                  extracted releases, untouched
  manifests/<key>_download.json  source, download date, Kaggle CLI version, Kaggle metadata/licence
  manifests/<key>_files.csv      every file with size and SHA-256
  index/<key>.csv                one row per image (see below)
  cache/<size>/<key>/...         8-bit grey PNGs, longer side = <size>
  cache/<size>/<key>_cache.csv   original size / mode / bit depth per cached image
```

Every index shares these columns: `collection, image_id, rel_path, patient_id, split, is_eval, subset`.
NIH adds view position, age, sex, original size; RSNA adds the DICOM header fields (bit depth,
photometric interpretation, window, rescale, LUT presence); COVID adds the upstream `source_url`.
No disease label is copied into the index, since the project does not use any.

Load them in Python:

```python
import sys; sys.path.insert(0, "src")
from chest_overlap.inventory import load_index
df = load_index()               # all four collections
nih = load_index(["nih"])
```

### Working-cache conversion (documented for the report)
1. Decode to one grey channel. DICOM: modality LUT, MONOCHROME1 inverted, stored bit range
   linearly mapped to 0–255, no VOI window. PNG/JPEG: RGB → luma (Pillow `L`), 16-bit → top 8 bits.
2. Resize so the longer side equals `--size` with area interpolation (`cv2.INTER_AREA`),
   aspect ratio kept, never enlarged.
3. Save as lossless 8-bit PNG.

## Other commands

```bash
python scripts/prepare_data.py info                          # collections + data folder in use
python scripts/prepare_data.py download all --metadata-only  # CSV/list files only (NIH, RSNA)
python scripts/prepare_data.py index rsna --no-dicom-headers
```

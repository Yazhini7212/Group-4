# Group-4
Image-Level and Patient-Level Overlap Across Public Chest Radiograph Collections

> **New here?** Start with [Getting Started](docs/GETTING_STARTED.md) (GitHub, VS Code, cluster
> and Jupyter), then the step-by-step [code manual](docs/MANUAL.md).

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

## Setup

**Laptop (VS Code):** open the folder, accept the recommended extensions, then
*Ctrl+Shift+P → Python: Create Environment → Venv* and tick `requirements.txt`.
Or in a terminal:
```bash
python -m venv .venv
```
```bash
.venv/Scripts/activate      # Windows (Git Bash); on Mac/Linux: source .venv/bin/activate
```
```bash
pip install -r requirements.txt
```

**RWTH cluster:** connect VS Code with Remote-SSH, clone the repo, then once:
```bash
bash scripts/hpc/setup_env.sh
```
This installs everything into `~/venvs/chest_overlap` and registers the notebook kernel
**`chest_overlap`**. Put your Kaggle token in `~/.kaggle/kaggle.json` (chmod 600) and accept the
RSNA competition rules on kaggle.com.

## Preparing the data (on the cluster)

Data goes to `$HPCWORK/chest_overlap` (override with `CHEST_OVERLAP_DATA` or `--data-root`).
Nothing is stored in the repository or in `$HOME`.

```bash
sbatch scripts/hpc/download.sbatch                 # download + index (or: ... download.sbatch covid kermany)
```
```bash
sbatch scripts/hpc/cache.sbatch --limit 100        # timing probe on 100 images per collection
```
```bash
sbatch scripts/hpc/cache.sbatch --size 512         # full working cache
```

If compute nodes cannot reach the internet, run the download on a login node instead
(inside `tmux`/`screen`), one collection at a time, because login nodes stop programs that use a
lot of CPU for more than 20 minutes:
`python scripts/prepare_data.py download covid && python scripts/prepare_data.py index covid`.
The job scripts start with `#!/usr/bin/zsh` (required at RWTH) and use partition `c23ms`.
Enable the commented `--account` line only if you were given a project ID.
How to use the cluster in general: [Getting Started, section 4](docs/GETTING_STARTED.md#4-using-the-rwth-cluster-hpc).

## Notebooks

Open `notebooks/01_explore_data.ipynb` in VS Code, choose the kernel **chest_overlap**
(cluster) or **.venv** (laptop) and run the cells with Shift+Enter. In your own notebooks:

```python
from chest_overlap import load_index, show_rows
df = load_index()               # all four collections, one row per image
show_rows(df.sample(4))         # look at 4 random images
```

Long-running work goes through `sbatch`, not notebooks. Clear notebook outputs before
committing.

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

### Working-cache conversion (documented for the report)
1. Decode to one grey channel. DICOM: modality LUT, MONOCHROME1 inverted, stored bit range
   linearly mapped to 0–255, no VOI window. PNG/JPEG: RGB → luma (Pillow `L`), 16-bit → top 8 bits.
2. Resize so the longer side equals `--size` with area interpolation (`cv2.INTER_AREA`),
   aspect ratio kept, never enlarged.
3. Save as lossless 8-bit PNG.

## Command-line reference

```bash
python scripts/prepare_data.py info                          # collections + data folder in use
python scripts/prepare_data.py download all --metadata-only  # CSV/list files only (NIH, RSNA)
python scripts/prepare_data.py index rsna --no-dicom-headers
python scripts/prepare_data.py --help                        # every option
```

## hongtry
hi!
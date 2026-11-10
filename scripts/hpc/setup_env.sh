#!/usr/bin/env bash
# One-time setup on the RWTH cluster (run on a login node, from the repo root):
#     bash scripts/hpc/setup_env.sh
# Creates a virtual environment in $HOME (small) and points the data at $HPCWORK (large).
set -euo pipefail

# Load a recent Python. Check what exists with: module spider Python
module load Python 2>/dev/null || echo "note: 'module load Python' failed; using system python3"

VENV="${CHEST_OVERLAP_VENV:-$HOME/venvs/chest_overlap}"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p "$HPCWORK/chest_overlap" logs   # logs/ is where the Slurm jobs write
echo
echo "Environment: $VENV"
echo "Data folder: $HPCWORK/chest_overlap"
echo
echo "Next: Kaggle credentials (only once). Create a token at https://www.kaggle.com/settings/api"
echo "and save it as ~/.kaggle/kaggle.json (chmod 600), or run 'kaggle auth login'."
echo "Also accept the RSNA competition rules on kaggle.com before downloading it."

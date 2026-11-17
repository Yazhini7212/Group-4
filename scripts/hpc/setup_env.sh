#!/usr/bin/env bash
# One-time setup on the RWTH cluster. Run on a login node, from the repo folder:
#     bash scripts/hpc/setup_env.sh
# - creates a Python environment in $HOME (small)
# - installs our code + packages + Jupyter kernel
# - registers the kernel "chest_overlap" for VS Code (Remote-SSH) and RWTH JupyterHub
# - creates the data folder in $HPCWORK (large)
set -euo pipefail

# Load a recent Python. See what exists with: module spider Python
module load Python 2>/dev/null || echo "note: 'module load Python' failed; using system python3"

VENV="${CHEST_OVERLAP_VENV:-$HOME/venvs/chest_overlap}"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Make the environment selectable as a notebook kernel.
python -m ipykernel install --user --name chest_overlap --display-name "chest_overlap"

mkdir -p "$HPCWORK/chest_overlap" logs   # logs/ is where the Slurm jobs write

echo
echo "Environment : $VENV"
echo "Kernel      : chest_overlap (choose it in VS Code / JupyterHub)"
echo "Data folder : $HPCWORK/chest_overlap"
echo
echo "Next: Kaggle credentials (only once) - see docs/GETTING_STARTED.md, step 5."

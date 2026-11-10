#!/usr/bin/env bash
# Download all four collections into $HPCWORK/chest_overlap and write checksums.
#     sbatch scripts/hpc/download.sbatch                 # all collections
#     sbatch scripts/hpc/download.sbatch nih             # just one
# If compute nodes have no internet access, run the same python command on a
# login node inside 'screen'/'tmux' instead (it only uses network and disk).
#SBATCH --job-name=cxr_download
#SBATCH --output=logs/%x_%j.out
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=2G
##SBATCH --account=<your_project_or_course_account>
set -euo pipefail
module load Python 2>/dev/null || true
source "${CHEST_OVERLAP_VENV:-$HOME/venvs/chest_overlap}/bin/activate"

python scripts/prepare_data.py download "${@:-all}"
python scripts/prepare_data.py index "${@:-all}"

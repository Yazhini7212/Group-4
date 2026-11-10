#!/usr/bin/env bash
# Build the reduced-resolution working cache in parallel.
#     sbatch scripts/hpc/cache.sbatch                      # all, 512 px
#     sbatch scripts/hpc/cache.sbatch --size 256
#     sbatch scripts/hpc/cache.sbatch --limit 100          # timing probe (brief: measure on 100 images first)
#SBATCH --job-name=cxr_cache
#SBATCH --output=logs/%x_%j.out
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem-per-cpu=2G
##SBATCH --account=<your_project_or_course_account>
set -euo pipefail
module load Python 2>/dev/null || true
source "${CHEST_OVERLAP_VENV:-$HOME/venvs/chest_overlap}/bin/activate"

python scripts/prepare_data.py cache all "$@"

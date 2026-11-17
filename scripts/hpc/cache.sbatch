#!/usr/bin/zsh
# Build the reduced-resolution working cache in parallel.
#     sbatch scripts/hpc/cache.sbatch                      # all, 512 px
#     sbatch scripts/hpc/cache.sbatch --size 256
#     sbatch scripts/hpc/cache.sbatch --limit 100          # timing probe (brief: measure on 100 images first)
# (RWTH batch scripts must start with #!/usr/bin/zsh.)
#SBATCH --job-name=cxr_cache
#SBATCH --output=logs/%x_%j.out
#SBATCH --partition=c23ms
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=32
#SBATCH --mem-per-cpu=2G
##SBATCH --account=<project-id>     # only if you were given a project; otherwise leave disabled

set -e
module load Python
source "${CHEST_OVERLAP_VENV:-$HOME/venvs/chest_overlap}/bin/activate"

python scripts/prepare_data.py cache all "$@"

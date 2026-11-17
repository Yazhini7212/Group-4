#!/usr/bin/zsh
# Download all four collections into $HPCWORK/chest_overlap, write checksums, build the index.
#     sbatch scripts/hpc/download.sbatch                 # all collections
#     sbatch scripts/hpc/download.sbatch nih             # just one
# (RWTH batch scripts must start with #!/usr/bin/zsh.)
#SBATCH --job-name=cxr_download
#SBATCH --output=logs/%x_%j.out
#SBATCH --partition=c23ms
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem-per-cpu=2G
##SBATCH --account=<project-id>     # only if you were given a project; otherwise leave disabled

set -e
module load Python
source "${CHEST_OVERLAP_VENV:-$HOME/venvs/chest_overlap}/bin/activate"

if [ $# -eq 0 ]; then set -- all; fi    # no arguments = all collections
python scripts/prepare_data.py download "$@"
python scripts/prepare_data.py index "$@"

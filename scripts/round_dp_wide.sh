#!/bin/bash -l
#SBATCH --job-name=round_dp
#SBATCH --output=/home/tbellagio/scratch/freqk_gr/logs/round_dp_%j.out
#SBATCH --error=/home/tbellagio/scratch/freqk_gr/logs/round_dp_%j.err
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00

set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
eval "$(conda shell.bash hook)"
conda activate pang

python3 - << 'EOF'
import gzip, sys
from pathlib import Path
import pandas as pd

RESULTS   = Path("/home/tbellagio/scratch/freqk_gr/results")
IN_FILE   = RESULTS / "dp_wide.csv.gz"
TMP_FILE  = RESULTS / "dp_wide_rounded.csv.gz"
DECIMALS  = 4
CHUNKSIZE = 50_000

print(f"Rounding {IN_FILE} to {DECIMALS} decimals → {TMP_FILE}")

first = True
reader = pd.read_csv(IN_FILE, index_col=["chrom","pos"], chunksize=CHUNKSIZE)
with gzip.open(TMP_FILE, "wt") as fout:
    for i, chunk in enumerate(reader):
        num_cols = chunk.select_dtypes(include="float").columns
        chunk[num_cols] = chunk[num_cols].round(DECIMALS)
        chunk.to_csv(fout, header=first)
        first = False
        if (i+1) % 10 == 0:
            print(f"  chunk {i+1} done ({(i+1)*CHUNKSIZE:,} rows)", flush=True)

# replace original with rounded version
TMP_FILE.rename(IN_FILE)
print(f"Done — replaced {IN_FILE}")
EOF

#!/bin/bash -l
#SBATCH --job-name=freqk_seedmix
#SBATCH --output=/home/tbellagio/scratch/freqk_gr/logs/freqk_seedmix_%x_%j.out
#SBATCH --error=/home/tbellagio/scratch/freqk_gr/logs/freqk_seedmix_%x_%j.err
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --time=04:00:00
# =============================================================================
# run_freqk_seedmix.sh
# Run the freqk pipeline for a single GrENE-Net seed mix sample.
#
# The seed mix is the founder population planted across all sites.
# Sample IDs are SEEDMIX_S1 … SEEDMIX_S8; no site/plot/date parsing needed.
#
# Arguments (passed by launch_seedmix.py via sbatch):
#   $1  SAMPLE_ID   e.g. SEEDMIX_S1
#   $2  R1          absolute path to R1 fastq.gz
#   $3  R2          absolute path to R2 fastq.gz
#   $4  K           k-mer size (default: 31)
# =============================================================================
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
eval "$(conda shell.bash hook)"
conda activate freqk_build

SAMPLE_ID=${1:?Usage: run_freqk_seedmix.sh SAMPLE_ID R1 R2 [K]}
R1=${2:?}
R2=${3:?}
K=${4:-31}

source "/home/tbellagio/scratch/freqk_gr/scripts/config.sh"

OUT_DIR=${RESULTS}/seedmix/${SAMPLE_ID}/k${K}
mkdir -p "${OUT_DIR}"

INDEX=${OUT_DIR}/${SAMPLE_ID}.k${K}.freqk.index
VAR_INDEX=${OUT_DIR}/${SAMPLE_ID}.k${K}.freqk.var_index
REF_INDEX=${OUT_DIR}/${SAMPLE_ID}.k${K}.freqk.ref_index
READS_COMBINED=${OUT_DIR}/all.fq.gz
COUNTS_BY_ALLELE=${OUT_DIR}/${SAMPLE_ID}.counts_by_allele.k${K}.tsv
RAW_COUNTS=${OUT_DIR}/${SAMPLE_ID}.raw_kmer_counts.k${K}.tsv
AF_OUT=${OUT_DIR}/${SAMPLE_ID}.allele_frequencies.k${K}.tsv

# --- Clean up any stale intermediate files from a previous failed run ----------
rm -f "${INDEX}" "${VAR_INDEX}" "${REF_INDEX}" "${READS_COMBINED}"

echo "==== freqk seed mix: ${SAMPLE_ID} | k=${K} ===="
echo "R1: ${R1}"
echo "R2: ${R2}"
echo "VCF: ${VCF}"
echo "REF: ${REF}"
echo "OUT: ${OUT_DIR}"
echo

# Validate inputs
[[ -s "${R1}" ]] || { echo "ERROR: R1 not found or empty: ${R1}" >&2; exit 1; }
[[ -s "${R2}" ]] || { echo "ERROR: R2 not found or empty: ${R2}" >&2; exit 1; }
[[ -s "${VCF}" ]]     || { echo "ERROR: VCF not found: ${VCF}" >&2; exit 1; }
[[ -s "${VCF}.tbi" ]] || { echo "ERROR: VCF index not found: ${VCF}.tbi" >&2; exit 1; }
[[ -s "${REF}" ]]     || { echo "ERROR: REF not found: ${REF}" >&2; exit 1; }

step() {
  local label="$1"; shift
  echo
  echo "[$(date)] === ${label} ==="
  echo "+ $*"
  "$@"
}

# --- 1. Build freqk index -----------------------------------------------------
step "index" \
  "$FREQK" index --fasta "$REF" --vcf "$VCF" --output "$INDEX" --kmer "$K"

# --- 2. Var-dedup -------------------------------------------------------------
step "var-dedup" \
  "$FREQK" var-dedup --index "$INDEX" --output "$VAR_INDEX"

# --- 3. Ref-dedup -------------------------------------------------------------
step "ref-dedup" \
  "$FREQK" ref-dedup -i "$VAR_INDEX" -o "$REF_INDEX" -f "$REF" --vcf "$VCF"

# --- 4. Combine reads ---------------------------------------------------------
echo
echo "[$(date)] Combining R1 + R2 -> all.fq.gz"
cat "${R1}" "${R2}" > "${READS_COMBINED}"

# --- 5. Count -----------------------------------------------------------------
step "count" \
  "$FREQK" count \
    --index "$REF_INDEX" \
    --reads "$READS_COMBINED" \
    --nthreads "${SLURM_CPUS_PER_TASK}" \
    --freq-output "$COUNTS_BY_ALLELE" \
    --count-output "$RAW_COUNTS"

# --- 6. Call ------------------------------------------------------------------
step "call" \
  "$FREQK" call \
    --index "$REF_INDEX" \
    --counts "$COUNTS_BY_ALLELE" \
    --output "$AF_OUT"

# --- Cleanup intermediate files -----------------------------------------------
rm -f "${READS_COMBINED}" "${INDEX}" "${VAR_INDEX}" "${REF_INDEX}"

echo
echo "[$(date)] Done. Allele frequencies:"
cat "$AF_OUT"

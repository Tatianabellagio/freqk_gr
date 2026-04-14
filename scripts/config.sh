#!/bin/bash
# =============================================================================
# config.sh
# Central paths and parameters for the freqk_gr pipeline.
# Source this file from other scripts.
# =============================================================================

# --- Cluster paths (adjust if moving to HPC scratch) -------------------------
WORK=/home/tbellagio/scratch/freqk_gr

# --- Input data ---------------------------------------------------------------
READS_ROOT=/home/tbellagio/scratch/pang/grenenet_reads/grenenet-phase1
VCF=/home/tbellagio/scratch/pang/sv_panel/merge_vcfs/panel.snp_ins_del.vcf.gz
REF=/home/tbellagio/scratch/pang/sv_panel/ref/TAIR10.Chr.fa

# --- freqk binary -------------------------------------------------------------
FREQK=/home/tbellagio/scratch/bin/freqk

# --- freqk parameters ---------------------------------------------------------
K=31

# --- Output dirs --------------------------------------------------------------
RESULTS=${WORK}/results
LOGS=${WORK}/logs
DATA=${WORK}/data

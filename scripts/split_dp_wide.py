#!/usr/bin/env python3
"""
split_dp_wide.py
Split dp_wide.csv.gz into SNP and SV (INS+DEL) files.
Reads in chunks to avoid loading the full matrix into memory.

Usage:
    python scripts/split_dp_wide.py
    python scripts/split_dp_wide.py --sample 50000   # also write sampled versions
"""
import argparse
import gzip
import random
import sys
from pathlib import Path

import pandas as pd

# ── paths ──────────────────────────────────────────────────────────────────────
_LOCAL   = Path("/Users/tatiana/Documents_new/freqk_gr")
_CLUSTER = Path("/home/tbellagio/scratch/freqk_gr")
PROJECT  = _LOCAL if _LOCAL.exists() else _CLUSTER
RESULTS  = PROJECT / "results"

IN_FILE  = RESULTS / "dp_wide.csv.gz"
SNP_FILE = RESULTS / "dp_snps.csv.gz"
SV_FILE  = RESULTS / "dp_svs.csv.gz"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunksize", type=int, default=50_000,
                        help="Rows per chunk (default: 50000)")
    parser.add_argument("--sample", type=int, default=None,
                        help="If set, also write dp_snps_sample.csv.gz and dp_svs_sample.csv.gz "
                             "with this many randomly selected rows (reservoir sampling)")
    args = parser.parse_args()

    if not IN_FILE.exists():
        sys.exit(f"ERROR: {IN_FILE} not found — run Stage 4 in the notebook first")

    print(f"Input : {IN_FILE}")
    print(f"Output: {SNP_FILE}")
    print(f"        {SV_FILE}")
    print(f"Chunk size: {args.chunksize:,}")

    # reservoir samples (if --sample requested)
    snp_reservoir, sv_reservoir = [], []
    snp_total, sv_total = 0, 0

    with (gzip.open(SNP_FILE, "wt") as f_snp,
          gzip.open(SV_FILE,  "wt") as f_sv):

        header_written = False
        reader = pd.read_csv(IN_FILE, index_col=["chrom", "pos"],
                             chunksize=args.chunksize)

        for chunk_num, chunk in enumerate(reader):
            snps = chunk[chunk["var_type"] == "SNP"]
            svs  = chunk[chunk["var_type"].isin(["INS", "DEL"])]

            # write header once
            if not header_written:
                snps.iloc[:0].to_csv(f_snp)
                svs.iloc[:0].to_csv(f_sv)
                header_written = True

            snps.to_csv(f_snp, header=False)
            svs.to_csv(f_sv,  header=False)

            snp_total += len(snps)
            sv_total  += len(svs)

            # reservoir sampling
            if args.sample:
                for row in snps.itertuples():
                    snp_total_seen = snp_total - len(snps) + 1
                    if len(snp_reservoir) < args.sample:
                        snp_reservoir.append(row)
                    else:
                        j = random.randint(0, snp_total_seen)
                        if j < args.sample:
                            snp_reservoir[j] = row

                for row in svs.itertuples():
                    sv_total_seen = sv_total - len(svs) + 1
                    if len(sv_reservoir) < args.sample:
                        sv_reservoir.append(row)
                    else:
                        j = random.randint(0, sv_total_seen)
                        if j < args.sample:
                            sv_reservoir[j] = row

            if (chunk_num + 1) % 10 == 0:
                print(f"  chunk {chunk_num+1}: {snp_total:,} SNPs, {sv_total:,} SVs so far")

    print(f"\nDone:")
    print(f"  SNPs: {snp_total:,} → {SNP_FILE}")
    print(f"  SVs : {sv_total:,}  → {SV_FILE}")

    # write sampled versions
    if args.sample and snp_reservoir:
        snp_sample_file = RESULTS / f"dp_snps_sample{args.sample}.csv.gz"
        sv_sample_file  = RESULTS / f"dp_svs_sample{args.sample}.csv.gz"

        pd.DataFrame(snp_reservoir).set_index(["chrom","pos"]).to_csv(
            snp_sample_file, compression="gzip")
        pd.DataFrame(sv_reservoir).set_index(["chrom","pos"]).to_csv(
            sv_sample_file, compression="gzip")

        print(f"  SNP sample ({len(snp_reservoir):,}) → {snp_sample_file}")
        print(f"  SV  sample ({len(sv_reservoir):,}) → {sv_sample_file}")


if __name__ == "__main__":
    main()

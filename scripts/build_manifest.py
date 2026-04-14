#!/usr/bin/env python3
"""
build_manifest.py
Scan the trimmed GrENE-Net reads directory and write data/samples.tsv.

Trimmed reads live in a flat directory:
  grenenet-phase1/trimmed/{STEM}_1P.fq.gz   (R1 paired)
  grenenet-phase1/trimmed/{STEM}_2P.fq.gz   (R2 paired)

where STEM = {SAMPLE_ID}_{library_info}, e.g.
  MLFH040320180306_CKDL210001610-1a-AK34068-AK9012_HFLJCCCX2_L5

Usage:
    python scripts/build_manifest.py
    python scripts/build_manifest.py --reads-root /path/to/grenenet-phase1
"""
import argparse
import csv
import re
import sys
from pathlib import Path

DEFAULT_READS_ROOT = "/home/tbellagio/scratch/pang/grenenet_reads/grenenet-phase1"

# MLFH sample-name pattern: MLFH + site(2) + pot(2) + date(8)
SAMPLE_RE = re.compile(r"^(MLFH(\d{2})(\d{2})(\d{8}))_")


def find_samples(reads_root: Path) -> list[dict]:
    trimmed_dir = reads_root / "trimmed"
    if not trimmed_dir.is_dir():
        sys.exit(f"ERROR: trimmed directory not found: {trimmed_dir}")

    samples = []
    seen = set()

    for r1 in sorted(trimmed_dir.glob("*_1P.fq.gz")):
        m = SAMPLE_RE.match(r1.name)
        if not m:
            continue

        sample_id, site, pot, date = m.group(1), m.group(2), m.group(3), m.group(4)

        # Derive R2 from R1 filename
        r2 = r1.parent / r1.name.replace("_1P.fq.gz", "_2P.fq.gz")
        if not r2.is_file():
            print(f"  WARNING: R2 not found for {sample_id}: {r2}", file=sys.stderr)
            continue

        if sample_id in seen:
            print(f"  WARNING: duplicate sample_id {sample_id}, skipping {r1.name}", file=sys.stderr)
            continue
        seen.add(sample_id)

        samples.append({
            "sample_id": sample_id,
            "site":      site,
            "pot":       pot,
            "date":      date,
            "year":      date[:4],
            "r1":        str(r1),
            "r2":        str(r2),
        })

    return samples


def main():
    parser = argparse.ArgumentParser(description="Build sample manifest from trimmed GrENE-Net reads")
    parser.add_argument("--reads-root", default=DEFAULT_READS_ROOT,
                        help="Path to grenenet-phase1 directory (contains trimmed/ subdir)")
    parser.add_argument("--out", default=None,
                        help="Output TSV path (default: data/samples.tsv)")
    args = parser.parse_args()

    reads_root = Path(args.reads_root)
    if not reads_root.is_dir():
        sys.exit(f"ERROR: reads root not found: {reads_root}")

    if args.out is None:
        project_root = Path(__file__).parent.parent
        out_path = project_root / "data" / "samples.tsv"
    else:
        out_path = Path(args.out)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Scanning: {reads_root / 'trimmed'}")
    samples = find_samples(reads_root)
    print(f"Found {len(samples)} samples")

    fieldnames = ["sample_id", "site", "pot", "date", "year", "r1", "r2"]
    with open(out_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(samples)

    print(f"Manifest written to: {out_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
launch_seedmix.py
Submit freqk SLURM jobs for all GrENE-Net seed mix samples (S1–S8).

The seed mix is the founder population planted across all GrENE-Net sites.
Running it through the same freqk pipeline gives the baseline allele
frequencies to compare against field samples.

Usage examples:
    # Submit all 8 seed mix samples
    python scripts/launch_seedmix.py

    # Dry run — show what would be submitted
    python scripts/launch_seedmix.py --dry-run

    # Skip samples that already have a completed counts_by_allele file
    python scripts/launch_seedmix.py --skip-done

    # Different k-mer size
    python scripts/launch_seedmix.py --k 21
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MANIFEST     = PROJECT_ROOT / "data" / "seedmix_samples.tsv"
RUN_SCRIPT   = PROJECT_ROOT / "scripts" / "run_freqk_seedmix.sh"
RESULTS_ROOT = PROJECT_ROOT / "results"


def load_manifest(path: Path) -> list[dict]:
    if not path.is_file():
        sys.exit(f"ERROR: manifest not found at {path}")
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def result_exists(sample: dict, k: str) -> bool:
    """Return True if the counts_by_allele output already exists."""
    out_dir = RESULTS_ROOT / "seedmix" / sample["sample_id"] / f"k{k}"
    counts_file = out_dir / f"{sample['sample_id']}.counts_by_allele.k{k}.tsv"
    return counts_file.is_file()


def main():
    parser = argparse.ArgumentParser(
        description="Submit freqk SLURM jobs for GrENE-Net seed mix samples"
    )
    parser.add_argument("--k", default="31", help="k-mer size (default: 31)")
    parser.add_argument("--skip-done", action="store_true",
                        help="Skip samples whose counts_by_allele output already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print selected samples and sbatch command; do not submit")
    parser.add_argument("--manifest", default=str(MANIFEST),
                        help=f"Path to seedmix_samples.tsv (default: {MANIFEST})")
    args = parser.parse_args()

    samples = load_manifest(Path(args.manifest))

    if args.skip_done:
        before = len(samples)
        samples = [s for s in samples if not result_exists(s, args.k)]
        skipped = before - len(samples)
        if skipped:
            print(f"Skipping {skipped} already-completed sample(s).")

    if not samples:
        print("All seed mix samples already have results. Nothing to submit.")
        sys.exit(0)

    # Summary table
    print(f"\n{'Sample':<20} {'Done?':>6}")
    print("-" * 30)
    for s in samples:
        done = "yes" if result_exists(s, args.k) else "no"
        print(f"{s['sample_id']:<20} {done:>6}")
    print(f"\nTotal: {len(samples)} sample(s) | k={args.k}")

    if args.dry_run:
        print("\n[dry-run] No jobs submitted.")
        print("\nExample sbatch command:")
        s = samples[0]
        print(f"  sbatch {RUN_SCRIPT} {s['sample_id']} {s['r1']} {s['r2']} {args.k}")
        return

    print()
    job_ids = []
    for s in samples:
        cmd = [
            "sbatch",
            str(RUN_SCRIPT),
            s["sample_id"],
            s["r1"],
            s["r2"],
            args.k,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR submitting {s['sample_id']}: {result.stderr.strip()}", file=sys.stderr)
            continue
        job_id = result.stdout.strip().split()[-1]
        job_ids.append(job_id)
        print(f"  Submitted {s['sample_id']} → job {job_id}")

    print(f"\nSubmitted {len(job_ids)} job(s).")
    if job_ids:
        ids_file = PROJECT_ROOT / "logs" / "submitted_jobs.txt"
        ids_file.parent.mkdir(exist_ok=True)
        with open(ids_file, "a") as fh:
            for jid in job_ids:
                fh.write(jid + "\n")
        print(f"Job IDs appended to: {ids_file}")


if __name__ == "__main__":
    main()

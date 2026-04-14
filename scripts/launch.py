#!/usr/bin/env python3
"""
launch.py
Smart launcher: select GrENE-Net samples from the manifest and submit
one SLURM freqk job per sample.

Usage examples:
    # Site 04, all time points
    python scripts/launch.py --site 04

    # Site 04, year 2018 only
    python scripts/launch.py --site 04 --year 2018

    # Site 04, specific dates
    python scripts/launch.py --site 04 --date 20180306 20190208

    # Multiple sites
    python scripts/launch.py --site 04 05 06

    # Skip samples that already have a completed allele-frequency file
    python scripts/launch.py --site 04 --skip-done

    # Dry run: show what would be submitted without submitting
    python scripts/launch.py --site 04 --dry-run
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MANIFEST     = PROJECT_ROOT / "data" / "samples.tsv"
RUN_SCRIPT   = PROJECT_ROOT / "scripts" / "run_freqk.sh"
RESULTS_ROOT = PROJECT_ROOT / "results"


def load_manifest(path: Path) -> list[dict]:
    if not path.is_file():
        sys.exit(
            f"ERROR: manifest not found at {path}\n"
            "Run  python scripts/build_manifest.py  first."
        )
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def result_exists(sample: dict, k: str) -> bool:
    """Return True if the allele-frequency output file already exists."""
    out_dir = RESULTS_ROOT / f"site{sample['site']}" / sample["sample_id"] / f"k{k}"
    af_file = out_dir / f"{sample['sample_id']}.allele_frequencies.k{k}.tsv"
    return af_file.is_file()


def select_samples(samples: list[dict], args) -> list[dict]:
    selected = samples

    if args.site:
        sites = {s.zfill(2) for s in args.site}
        selected = [s for s in selected if s["site"] in sites]

    if args.year:
        years = set(args.year)
        selected = [s for s in selected if s["year"] in years]

    if args.date:
        dates = set(args.date)
        selected = [s for s in selected if s["date"] in dates]

    if args.pot:
        pots = {p.zfill(2) for p in args.pot}
        selected = [s for s in selected if s["pot"] in pots]

    return selected


def main():
    parser = argparse.ArgumentParser(description="Submit freqk SLURM jobs for selected GrENE-Net samples")

    # Filters
    parser.add_argument("--site",  nargs="+", metavar="XX",   help="Site number(s) e.g. 04 05")
    parser.add_argument("--year",  nargs="+", metavar="YYYY", help="Year(s) e.g. 2018 2019")
    parser.add_argument("--date",  nargs="+", metavar="YYYYMMDD", help="Exact collection date(s)")
    parser.add_argument("--pot",   nargs="+", metavar="XX",   help="Pot number(s) e.g. 03 07")

    # Behaviour
    parser.add_argument("--k", default="31", help="k-mer size passed to run_freqk.sh (default: 31)")
    parser.add_argument("--skip-done", action="store_true",
                        help="Skip samples whose allele-frequency output already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print selected samples and sbatch command; do not submit")
    parser.add_argument("--manifest", default=str(MANIFEST),
                        help=f"Path to samples.tsv (default: {MANIFEST})")

    args = parser.parse_args()

    samples  = load_manifest(Path(args.manifest))
    selected = select_samples(samples, args)

    if not selected:
        print("No samples match the filters.")
        sys.exit(0)

    # Optionally skip completed runs
    if args.skip_done:
        before = len(selected)
        selected = [s for s in selected if not result_exists(s, args.k)]
        skipped = before - len(selected)
        if skipped:
            print(f"Skipping {skipped} already-completed sample(s).")

    if not selected:
        print("All selected samples already have results. Nothing to submit.")
        sys.exit(0)

    # Summary table
    print(f"\n{'Sample':<25} {'Site':>4} {'Pot':>3} {'Date':>10} {'Year':>4} {'Done?':>6}")
    print("-" * 60)
    for s in selected:
        done = "yes" if result_exists(s, args.k) else "no"
        print(f"{s['sample_id']:<25} {s['site']:>4} {s['pot']:>3} {s['date']:>10} {s['year']:>4} {done:>6}")
    print(f"\nTotal: {len(selected)} sample(s) | k={args.k}")

    if args.dry_run:
        print("\n[dry-run] No jobs submitted.")
        return

    print()
    job_ids = []
    for s in selected:
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
        ids_file = PROJECT_ROOT / "logs" / f"submitted_jobs.txt"
        ids_file.parent.mkdir(exist_ok=True)
        with open(ids_file, "a") as fh:
            for jid in job_ids:
                fh.write(jid + "\n")
        print(f"Job IDs appended to: {ids_file}")


if __name__ == "__main__":
    main()

# freqk_gr

Pipeline for running [`freqk`](https://github.com/milesroberts-123/freqk/tree/main/src) on real GrENE-Net pool-seq reads to estimate SV allele frequencies per sample.

Each sample is one pot at one site on one collection date. Jobs are submitted individually to SLURM.

---

## What freqk does

freqk estimates the allele frequency of structural variants (SVs) from pool-seq short reads using k-mers.
Given a reference genome, an SV VCF, and pooled FASTQ reads, it outputs a per-variant allele frequency table.

Pipeline steps run per sample:
1. `freqk index` — build k-mer index from reference FASTA + VCF
2. `freqk var-dedup` — deduplicate variant k-mers
3. `freqk ref-dedup` — remove k-mers not informative against the reference
4. `freqk count` — count k-mers in the reads
5. `freqk call` — estimate allele frequencies

---

## Inputs

| Input | Path (cluster) |
|-------|----------------|
| Reads | `/home/tbellagio/scratch/pang/grenenet_reads/grenenet-phase1/trimmed/` |
| SV VCF | `/home/tbellagio/scratch/pang/sv_panel/merge_vcfs/panel.snp_ins_del.vcf.gz` |
| Reference | `/home/tbellagio/scratch/pang/sv_panel/ref/TAIR10.Chr.fa` |

The VCF contains SNPs, insertions, and deletions.

---

## Sample naming convention

`MLFH` + `site (2 digits)` + `pot (2 digits)` + `date (yyyymmdd)`

| Field | Example | Meaning |
|-------|---------|---------|
| `ML` | ML | Moi Lab |
| `FH` | FH | Flower head sample type |
| site | `04` | Site number (01–57) |
| pot  | `03` | Pot number (00–12) |
| date | `20180306` | Collection date |

Example: `MLFH040320180306` = site 04, pot 03, collected 2018-03-06.

---

## Directory structure

```
freqk_gr/
├── scripts/
│   ├── config.sh            # cluster paths, freqk binary, k-mer size
│   ├── build_manifest.py    # scan reads dir → data/samples.tsv  (run once)
│   ├── launch.py            # filter samples + submit SLURM jobs
│   └── run_freqk.sh         # SLURM job script (one sample per job)
├── data/
│   └── samples.tsv          # manifest: all 1400 samples across all sites/years
├── results/
│   └── site{XX}/
│       └── {SAMPLE_ID}/
│           └── k{K}/
│               ├── {SAMPLE_ID}.counts_by_allele.k{K}.tsv
│               ├── {SAMPLE_ID}.raw_kmer_counts.k{K}.tsv
│               └── {SAMPLE_ID}.allele_frequencies.k{K}.tsv   ← main output
└── logs/
    ├── freqk_{sample}_{jobid}.out
    ├── freqk_{sample}_{jobid}.err
    └── submitted_jobs.txt
```

Intermediate files (combined reads, freqk index files) are deleted after each job completes.

---

## Quick start

### 1. Build the sample manifest (once, after cloning or moving the pipeline)

```bash
python scripts/build_manifest.py
# or with a custom reads root:
python scripts/build_manifest.py --reads-root /path/to/grenenet-phase1
```

Writes `data/samples.tsv` with columns:
`sample_id`, `site`, `pot`, `date`, `year`, `r1`, `r2`

### 2. Preview what would be submitted (dry run)

```bash
python scripts/launch.py --site 04 --dry-run
```

### 3. Submit jobs

```bash
# Site 04, all time points (38 jobs)
python scripts/launch.py --site 04

# Site 04, year 2018 only
python scripts/launch.py --site 04 --year 2018

# Site 04, specific collection dates
python scripts/launch.py --site 04 --date 20180306 20190208

# Multiple sites
python scripts/launch.py --site 04 05 06

# Skip samples whose allele-frequency output already exists
python scripts/launch.py --site 04 --skip-done

# Custom k-mer size
python scripts/launch.py --site 04 --k 21
```

All submitted job IDs are appended to `logs/submitted_jobs.txt`.

---

## Configuration

Edit `scripts/config.sh` to update cluster paths or parameters:

```bash
READS_ROOT   # root of grenenet-phase1 reads
VCF          # SV+SNP VCF (bgzipped + tabixed)
REF          # TAIR10 reference FASTA (indexed)
FREQK        # path to freqk binary
K            # default k-mer size (default: 31)
```

---

## Data summary

The full manifest (`data/samples.tsv`) covers ~57 GrENE-Net sites across 2018–2019+, spread across 8 sequencing releases. Site 04 has 38 samples (pots 03–12, four collection dates).

# Data card

## Sources and permissions

| Source | Fixed version | Role | Publisher declaration |
| --- | --- | --- | --- |
| [PromptCloud SEEK A](https://www.kaggle.com/datasets/promptcloud/job-listings-on-seek-2019) | Kaggle version 1; 15,000 actual records | Classification | CC0 |
| [PromptCloud SEEK B](https://www.kaggle.com/datasets/promptcloud/latest-seek-australia-job-dataset) | Kaggle version 1; 10,000 actual records | Classification | CC0 |
| [SkillSpan](https://github.com/kris927b/SkillSpan) | `2ccf3de5b5af7a5409b8dd814fb1315dd6e0ae1b` | Skill and Knowledge BIO labels | CC BY 4.0 data; upstream repository code MIT |
| [JobStreet](https://huggingface.co/datasets/azrai99/job-dataset) | `b1937baac3ad7a2c7f18d0e24b14b00683a49f1d` | Historical external comparison | YAML Apache-2.0, prose CC BY 4.0; conflict retained |

Exact source URLs, byte hashes and counts are in [sources.json](data/sources.json)
and [checksums.sha256](data/checksums.sha256). The two Kaggle metadata endpoints
and SkillSpan/JobStreet data cards were inspected on 2026-10-21. Provider
licensing statements do not independently settle every third-party right in
an advertisement. JobStreet text is not redistributed here.

No job website is scraped by this project. The downloader retrieves fixed
third-party releases. SEEK observation dates span 2019-05-29 to 2019-10-31;
download/check dates are not posting dates.

## Reconstruction and cohort provenance

The supplied course delivery contains 21,663 postings selected from 25,000
source rows. Its prose describes HTML cleanup, NFKC normalization, conflict
removal, deduplication, employer grouping and category-support filtering.
The original selection/split-generation script is absent.

Rather than invent that missing script, `data/cohort.jsonl.gz` preserves the
actual delivered row selection, source references, labels, groups and split
membership, without descriptions. `download_data.py` independently matches
each source reference's normalized text, label, employer, date and source ID,
then restores the original row order. This reconstructs the **archived cohort**;
it does not demonstrate when the original selection was chosen.

Every source member has a pinned SHA-256. The 22,213 references include multiple
sources for merged duplicates; they are not 22,213 distinct observations.
Content IDs are SHA-256 of UTF-8 normalized text after `lower()`.
Hash matches establish integrity and traceability, not the factual truth or
current validity of the original advertisements.

## Labels and splits

The target is the original platform's broad category, not a fine occupation or
employer industry. The model consumes descriptions only; separate titles,
company names and salaries are not concatenated. Descriptions can themselves
contain titles or employer information.

| Partition | Postings | Normalized employer groups |
| --- | ---: | ---: |
| Train | 15,667 | 6,357 |
| Validation | 3,052 | 1,360 |
| Test | 2,944 | 1,364 |

The three group sets are pairwise disjoint. All 20 retained categories appear
in every partition. The historical selection required train ≥100, validation
≥1 and test ≥30 per category. This use of label support restricts the
population studied; it does not use test predictions to tune a model.

## SkillSpan

Mike Zhang, Kristian Nørgaard Jensen, Sif Dam Sonniks and Barbara Plank (2022),
*SkillSpan: Hard and Soft Skill Extraction from English Job Postings*,
NAACL-HLT, pp. 4962–4984. DOI: [10.18653/v1/2022.naacl-main.366](https://doi.org/10.18653/v1/2022.naacl-main.366).

The public `tech` and `house` sources contain 11,543 sentences, not the full
14.5K mentioned in the paper. The converter preserves original tokens and the
two separate BIO channels and adds sentence/split IDs. These are sentence
counts, not additional classification postings.

Training is unchanged. Evaluation removes 659 validation and 812 test rows
whose exact token tuples appear in training, leaving 2,515 and 2,757 sentences.
Dev/test overlap is reported, not additionally filtered. Job identifiers restart
by split; use `(split, source, idx)`, not `idx` alone.

## Small sample and distribution

`data/sample/` contains 1,200 real SEEK postings (400 per partition) and 400
SkillSpan sentences (200/100/100). It is selected deterministically from the
delivered partitions. Sample hashes and selection seeds are recorded in
[delivery_manifest.json](data/delivery_manifest.json). Sample metrics must not
be used as the full study's result.

The ~56 MB classification CSV and full SkillSpan CSVs are excluded from Git.
The download/reconstruction route is sufficient to regenerate them. No model
weights, credentials or local user paths belong in the published results.

## Limits and unresolved evidence

- English historical advertisements are not representative of current hiring
  in the US, Singapore, Hong Kong or China.
- Corporate aliases, staffing clients and near duplicates are not fully resolved.
- The source paper notes two very short descriptions, including one placeholder;
  no post-hoc cleanup is used to improve a score.
- JobStreet's full CSV and 115,812-entry exclusion index are missing from the
  supplied package. Historical external scores are labelled **paper-reported,
  not rerun**.
- The supplied source report carries a 2026-10-28 date, later than this
  integration's 2026-10-21 check. That date is not treated as evidence of a
  completed audit. This repository records the checks actually executed.

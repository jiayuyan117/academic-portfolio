# Eight-project research portfolio — v1.0.0

This release adds **Does the Skill Signal Help?**, a reproducible job-posting NLP
study, to Jiayu Yan's existing academic portfolio. The English homepage now
offers Data Science and Business Analytics reading routes across eight projects.

## Research evidence

- Reconstructs the archived 21,663-posting, 20-category SEEK cohort from two
  fixed public releases, checking 22,213 source references and employer isolation.
- Reproduces the full classification ablation: test Macro-F1 **0.7406** for
  TF-IDF, **0.5003** for the Skill + Knowledge lexicon, and **0.7348** for fusion.
  The fusion-minus-text employer-cluster interval is **[−0.0176, +0.0070]**.
- Completes a shared-sample comparison: TF-IDF **0.7272**, three-epoch TextCNN
  **0.3679**, and frozen MiniLM + logistic regression **0.6705**. Text-length
  and training budgets differ and are documented.
- Evaluates Skill and Knowledge spans separately, with paired job-cluster
  intervals and explicit disclosure of the 300-iteration optimization limit.
- Preserves predictions, fixed sample IDs, configurations and artifact hashes.
  Routine CI recomputes metrics and trains a small real-data sample; it does
  not retrain every full-data model.

## Presentation and reproducibility

The NLP project includes an English research brief, three generated figures,
a data card, methods, team attribution, third-party notices, pinned environments,
source downloader, portable task runner and dedicated GitHub Actions workflow.
The site is checked at desktop and mobile widths with external network requests
blocked. Original project directories 01–07 remain stable.

## Evidence boundaries

The original work is a team coursework study, not a peer-reviewed publication.
AI-assisted portfolio integration is disclosed. No independently timestamped
preregistration was supplied. The historical JobStreet experiment is labelled
as paper-reported because its external CSV and exclusion index were not supplied.
The reconstruction preserves the delivered cohort; it does not recover the
missing original split-generation script.

Portfolio: https://jiayuyan117.github.io/academic-portfolio/

Research brief:
https://jiayuyan117.github.io/academic-portfolio/projects/08-nlp-job-postings/report.html

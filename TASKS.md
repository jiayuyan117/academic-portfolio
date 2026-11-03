# Portfolio curation — 2026-11-03

Baseline: clean `442e832`, equal to origin/main after fetch. The newer project 11
is preserved. Scope: admissions presentation by programme focus, not country rankings.

- [x] Audit homepage, bilingual README, project summaries, provenance and saved evidence.
- [x] Implement selected / supporting / optional hierarchy and consistent routes.
- [x] Verify changed delivery, core evidence and catalog regression tests (limits below).
- [ ] Commit, push main, compare remote SHA and inspect Pages deployment.

| Project | Placement and evidence reviewed |
| --- | --- |
| 01 | Supplement: 20-day forecast, 252 stored numerical checks; overlaps 09, limited holdout. |
| 02 | Selected quantitative alternative: 334 checks; FEVD 32.4% vs 0.35% exposes identification sensitivity. |
| 03 | Supplement for BA: denominator/source audit; unresolved historical records and charging break remain visible. |
| 04 | Supplement for BA: 17,379 hourly rows, 731 dates reconciled; offline charts. |
| 05 | Selected: 43,824 hours, 2,067 missing, 155-hour longest gap; observed-only analysis. |
| 06 | Optional coursework archive: collection/synthetic status unknown. Preserve data and sensitivity outputs. |
| 07 | Engineering supplement: AVL/department invariants and reference-model tests. |
| 08 | Selected: source manifest, employer-disjoint cohort and prediction-level verification. |
| 09 | Selected: temporal splits, saved predictions, 24 intervals and six result tables. |
| 10 | Engineering supplement: revision pagination, persistence and HTTP tests; AI implementation credited. |
| 11 | Optional simulated measurement study: preserve newer contribution, synthetic ground truth and AI disclosure. |

Audit corrections: README 06 incorrectly implied no customer-cluster sensitivity
exists; saved findings already include 2,000 user-cluster draws, separate from
unadjusted original tests. Browser checker expected nine cards despite eleven.
Chinese reproduction table omitted 09–11. Original coursework authorship follows
the author's declaration; teacher frameworks, textbook topic and AI implementation
remain separately credited.

## Verification in this delivery

- PASS: `tools/check_delivery.py`, stored evidence for 01–06, 08–09,
  all eleven homepage anchors/resources and bilingual README local targets.
  Markdown fragment existence is not checked by that helper.
- PASS: project 10 `run.ps1 test`: 13 groups, zero failures, JDK 21.
- PASS: project 06 unittest discovery: 11 tests, including whole-user resampling.
- PASS: `tools/check_browser.py --browser <installed Chrome>`: 1280/375/320px,
  selected view and expanded archive, deep link to archived project, route controls,
  briefs 03–09, scenario controls and four charts with HTTP(S) blocked.
  Screenshots are local ignored artifacts under `.runtime/browser-checks`.
- PASS: `git -c core.whitespace=cr-at-eol diff --check`; CRLF is preserved per
  repository attributes. HTML reviewed with `git diff --text`, not an XML parser.
- BLOCKED: 08 `run.py verify` and 09 `verify.py` both stop at missing `sklearn`
  in the installed CPython 3.12 environment. Saved manifests/links passed, but
  this is not a fresh numerical rerun of either project. No new dependencies installed.
- Not rerun: expensive model training, 01/02 notebook execution, 03–05 figure
  rebuilds, 07 Maven suite and 11 simulation. Their existing evidence is historical.
- Pages legacy build endpoint returned public HTTP 404; Actions and live page
  are checked separately after publication.

# Review implementation and verification

This change implements the recommendations in the supplied 2026-10-21 academic
portfolio review. Original coursework is preserved. Numerical references for
projects 01–02 are not relaxed or replaced.

| Recommendation | Implementation |
| --- | --- |
| Homepage project counts | Removed stale numerical claims from the introduction, metadata and footer; seven numbered cards with checked anchors and a reading guide. |
| CI coverage for 01–02 | Full notebook verifiers added to Linux and Windows jobs; projects 03–06 rebuild separately; Java runs through Maven/JUnit. |
| Offline project 04 charts | Four standalone Plotly HTML files embed the runtime; calendar and animation preserve their original analytical roles. Browser checks block every HTTP(S) request. |
| Requirements overwritten by runners | Dependency declarations are read-only; versions are checked and actual environments recorded separately. |
| Requirements BOM inconsistency | UTF-8 without BOM, common comment headers, and a delivery check for encoding. |
| NEV provenance | Separate source CSVs, observation-level provenance, explicit verification status, arithmetic checks and a source audit. |
| Reproducible environment | Published dependencies installed and checked on CPython 3.12.10; resolved constraints, an aggregate requirements file, a unified runner and optional Docker recipe. |
| Duplicate 01–02 verifiers | Shared `portfolio_common` module with thin project entrypoints and notebook/Python synchronization checks. |
| Repeated ARIMA fits | Fit full-training candidates once, reuse across diagnostics/forecasting/full-sample stability, and remove unused `gain`. Shorter-prefix sensitivity fits remain independent. |
| Positional NEV alignment | Join fleet and charging by year with unique-key and coverage checks; derive narrative numbers from input tables. |
| Consumer statistics and row counts | Explain ANOVA's mean estimand, add Welch and valid Welch–Yuen sensitivity checks, retain rank checks, document multiplicity and repeated-customer limits; 8,020 → 8,000 is explicit. |
| Java BST and testing | AVL insertion/deletion, one lookup for transfers, iterative department traversal, Maven/JUnit 5, ordered-input and TreeMap oracle tests. |
| Registered-user positional lookup | Select by semantic user type; reject duplicate labels and duplicate daily reconciliation keys. |
| Reproducibility positioning | Describe input hashes separately from 586 numerical comparisons; link actual CI status rather than asserting unobserved remote success. |
| Commercial implications | Each homepage card explains a decision implication and its evidence limits. |
| Reviewer reading guide | English overview, capability-based suggested routes, sequential 01–07 cards, keyboard focus and skip navigation. |
| Data-to-decision example | Consumer report defines the business question, metrics, evidence, limitations and a proposed randomized experiment; no experiment or causal result is invented. |

## Verification evidence

Local validation uses Windows x86-64, CPython 3.12.10, Temurin JDK 17 and
Maven 3.9.9. The following were actually run:

- All declared Python dependencies installed successfully; `pip check` found no
  broken requirements. Package-index availability was verified rather than
  assuming the review's newer version numbers were invalid.
- Project 01 executed cleared notebook outputs and compared **11 tables / 252
  numeric values**; project 02 compared **8 tables / 334 values**. Original
  `rtol=1e-6`, `atol=1e-8` and all **3 + 5 input hashes** passed.
- All 28 shared-verifier regression tests passed. They cover input changes,
  dependency mismatch, numerical boundaries, notebook errors, English output,
  model reuse and external HTML/CSS resources.
- Project 03 passed 23 regression tests and rebuilt seven derived CSVs and
  16 decodable 300-dpi figures. Provenance records separate 21 externally
  supported observations, 93 coursework observations, two unresolved
  observations and one scenario assumption. The corrected 2021 PHEV value,
  2025 charging scope break and denominator labels propagate to both figure sets.
- Project 04 rebuilt all four HTML charts; semantic tests include date
  reconciliation, duplicate dates, reordered user labels and embedded assets.
  All six tests passed.
- Project 05 rebuilt seven figures. Headline statistics use **41,757 observed
  hours**, excluding all **2,067** missing hours. The separate short-gap policy
  audit permits 176 interpolations and leaves 1,891 missing; interpolated values
  do not enter the headline analysis.
- Project 06 rebuilt seven figures and regenerated its README. Seven inference
  tests passed, including independent SciPy checks for Welch/Yuen calculations.
- Project 07 passed **33 JUnit tests**, with zero failures, errors or skips;
  this includes ordered sets of 50,000 employees and a 20,000-level department tree.
- Browser verification opened local files with HTTP(S) blocked, rendered all
  four charts and checked the homepage at 1280px and 375px widths. Screenshots
  were inspected; animation controls were moved clear of the title.
- Workflow YAML parsed successfully. Homepage local links and expected
  generated artifacts passed the delivery checker.

## Review follow-up

Independent source reviews found and corrected a duplicate-date reconciliation
gap, incomplete HTML/CSS offline-resource checks, and the observed/imputed
distinction in project 05. Java control
blocks were expanded for clarity. A suspected `nest-asyncio2` typo was rejected
after inspecting installed `ipykernel 7.4.0` metadata: it explicitly requires
`nest-asyncio2>=1.7.0`.

## Boundaries of this evidence

- Historical NEV observations without retrieved supporting evidence remain
  labelled unverified. Traceability and arithmetic validation do not certify
  all external statistics. See [the source audit](NEV_SOURCE_AUDIT.md).
- The Docker recipe has not been executed locally; Docker is not installed.
  Linux and Windows GitHub-hosted jobs must run on the eventual pushed commit
  before remote CI success can be claimed.
- Existing historical Office deliverables may contain superseded figures;
  the project README identifies the current analytical artifacts.
- Local verification does not mean GitHub or Pages has been updated. Remote
  publication requires an authenticated GitHub session with repository write
  permission and a successful push/deployment.

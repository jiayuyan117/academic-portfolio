# Reproduce the portfolio

Use **CPython 3.12** for projects 01–06 and **JDK 17 + Maven 3.9**
for project 07. Run commands from the repository root unless stated otherwise.
The public reports and charts are committed, so reading them requires no Python
installation. Rebuilding requires downloading packages once.

Project 01's original strict numerical reference is supported on **Windows
x86-64**. Project 02 is checked on Windows and Linux; 03–07 are checked on
Linux as well as the local Windows validation. On macOS/Linux, select projects
02–06 rather than using the all-project command below. A Linux project 01 run
still executes the checks and fails on excessive drift; it is not silently skipped.

## Python: a clean, isolated environment

```bash
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell, instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install -c constraints.txt -r requirements.txt
python -m pip check
python tools/rebuild.py
```

To rebuild only one project, use `python tools/rebuild.py --project 01`.
The runner uses the same Python executable for every subprocess, sets UTF-8
output and single-threaded BLAS, and stops immediately on a failed command.
For a smaller installation, use a project's `requirements.txt` in place of
the root file, with the same root `constraints.txt`.

The exact declared versions were successfully installed together on Windows
x86-64 with CPython 3.12.10 on 2026-10-21; `pip check` found no conflicts.
These are published releases, not prerelease specifications. `constraints.txt`
also records the resolved transitive dependency versions. Platform-specific
dependencies may differ, and the CI jobs provide separate platform evidence.
This is a version constraint snapshot, not a hash-locked package mirror.

The first Linux CI run of project 01 produced a drift-model `MAE_z` of
`4.5313198708117`, versus the original Windows `4.531076030729077`.
The difference exceeds `rtol=1e-6, atol=1e-8`. The complete Windows CI run
passed all 252 comparisons. CI therefore runs project 01 in its validated
Windows environment; it neither loosens the tolerance nor replaces the reference.
See [the recorded failure](https://github.com/jiayuyan117/academic-portfolio/actions/runs/39584285722/job/119169217969).

The existing numerical reference environment is retained deliberately.
Downgrading a statistics library without measuring the numerical consequences
would weaken reproducibility. Requirements are declarations: running an
analysis does **not** update them. Version upgrades should be deliberate,
with the numerical regression checks reviewed before accepting new results.

## What the checks mean

- **01–02:** verify input SHA-256 hashes, execute cleared notebooks, reject
  execution errors and unexpected Chinese content, and compare the numeric
  output tables with committed references at `rtol=1e-6`. Reference values are
  not automatically replaced when a check fails.
- **03:** rebuild the data audit and bilingual industry figures; source
  traceability and arithmetic checks do not turn unverified numbers into
  verified statistics.
- **04:** reconcile hourly and daily demand, then rebuild four standalone
  interactive charts.
- **05–06:** rebuild figures, underlying tables and `outputs/findings.json`.
  The 04 and 06 pipelines also regenerate their project READMEs. The 05 README,
  root overviews and homepage are maintained separately and must be checked
  when results change.
- **07:** run deterministic and randomized reference-model tests, including
  ordered employee IDs and structural invariants.

Rebuilding intentionally updates generated notebooks, HTML, figures, tables,
environment records and manifests. This is different from modifying an input
dataset or a dependency declaration. Original coursework in `source_materials/`
is retained unchanged. Git attributes preserve input CSV bytes across platforms.

## Java

```bash
mvn -B -f projects/07-workforce-system-java/pom.xml verify
```

See the project's README for the lightweight `javac` demonstration and the
scope of the data structure tests.

## Delivery checks

```bash
python tools/check_delivery.py
python -m unittest discover -s portfolio_common/tests -v
python -m unittest discover -s projects/03-china-nev-industry-analytics/tests -v
python -m unittest discover -s projects/04-bike-sharing-interactive-visualization/tests -v
python -m unittest discover -s projects/06-consumer-behaviour-matplotlib/tests -v
```

For a real browser check, install the optional testing tools:

```bash
python -m pip install -r tools/requirements-browser.txt
python -m playwright install chromium
python tools/check_browser.py
```

The browser check blocks all HTTP(S) requests, opens the committed files
directly, checks that all four interactive charts render, and checks the homepage
at desktop and mobile widths. Screenshots are written to `.runtime/browser-checks/`
and are excluded from Git.

## Optional Python container

```bash
docker build -t academic-portfolio .
docker run --rm academic-portfolio
```

The Dockerfile fixes the Python patch version and Debian release and installs
the same dependency constraints. It includes CJK fonts for the Chinese figures.
It rebuilds Python projects 02–06 inside the Linux container; project 01 requires
the documented Windows reference environment, and Java is tested separately.
Building the image requires network access. Container execution is a supported
recipe only to the extent recorded in the delivery verification report; do not
infer a successful Docker run from the presence of this file alone.

## Reading offline

Download or clone the repository before disconnecting. The 01–02 HTML reports
embed figures; project 04's generated charts embed their plotting libraries.
Other projects provide PNG figures. GitHub source links and data-source
citations still require a network connection.

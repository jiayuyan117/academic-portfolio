param([ValidateSet("all", "test")][string]$Mode = "all")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    New-Item -ItemType Directory -Force build | Out-Null
    & javac --release 17 -encoding UTF-8 -d build java/src/CartEventLog.java java/src/Simulate.java java/test/CartEventLogTest.java
    if ($LASTEXITCODE -ne 0) { throw "Compilation failed" }
    & java -cp build CartEventLogTest
    if ($LASTEXITCODE -ne 0) { throw "Java tests failed" }
    if ($Mode -eq "all") {
        & java -cp build Simulate data
        if ($LASTEXITCODE -ne 0) { throw "Simulation failed" }
        & python analysis/analyze.py | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Analysis failed" }
    }
    & python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Findings tests failed" }
} finally { Pop-Location }

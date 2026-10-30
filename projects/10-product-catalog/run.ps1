param([ValidateSet("test", "serve")][string]$Mode = "test")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    New-Item -ItemType Directory -Force build | Out-Null
    & javac --release 17 -encoding UTF-8 -d build src/Catalog.java src/CatalogServer.java test/CatalogTest.java
    if ($LASTEXITCODE -ne 0) { throw "Compilation failed" }
    if ($Mode -eq "test") { & java -cp build CatalogTest }
    else { & java -cp build CatalogServer }
    if ($LASTEXITCODE -ne 0) { throw "Java execution failed" }
} finally { Pop-Location }

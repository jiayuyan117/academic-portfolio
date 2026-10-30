# 10 · Product Catalog: Protecting Small Data Changes

An AI-assisted engineering supplement for Jiayu Yan's academic portfolio, newly
implemented from the **product-management topic** of a Java Web textbook example.
This is not a claim of independently completed historical coursework, research,
production deployment, real users or measured business impact.

[Architecture brief / 双语简报](PROJECT.html) · [Source and contribution statement](PROVENANCE.md)

## Question and scope

Can a small catalog reject invalid money, stale edits and failed saves without
silently changing its records? The implementation provides create, search, edit
and delete through a local browser interface. SKU is unique and immutable during
editing; names support Unicode; prices use integer CNY cents; stock is a
nonnegative integer. The initial catalog is empty. Any example products entered
for demonstration are synthetic.

Project 07 already covers in-memory trees and workforce membership invariants.
This supplement instead covers HTTP input boundaries, file persistence, restart
recovery and competing edits. It deliberately uses **JDK HttpServer and a versioned
TSV snapshot**, not JSP, Servlet, JDBC or SSH. The local JDK was available but Maven
was not; avoiding downloaded dependencies makes this bounded exercise reproducible.
There is no database/SQL claim and no copied textbook implementation.

## Run locally

Requires a full JDK 17 or newer (`java` and `javac` on PATH). No Maven, Python,
external server, database password or network download is needed.

From this project directory on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 test
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 serve
```

The execution policy applies only to that PowerShell process. Alternatively,
compile directly; these commands also work in a POSIX shell:

```sh
mkdir build
javac --release 17 -encoding UTF-8 -d build src/Catalog.java src/CatalogServer.java test/CatalogTest.java
java -cp build CatalogTest
java -cp build CatalogServer
```

If `build` already exists, skip `mkdir`. Open **http://127.0.0.1:8080** (use this
literal host, not `localhost`). Stop with Ctrl+C. Restarting restores
`data/catalog.tsv`; the entire local data directory is Git-ignored. An alternative
file and port can be passed as `java -cp build CatalogServer data/demo.tsv 8081`.
Use only one server per data file. Do not delete the lock file while running.

Try creating SKU `NOTE-1`, name `Notebook`, price `19.90`, stock `8`. Open the
catalog in two tabs. Save an edit in one tab, then submit the old form in the
other: the latter returns **409**, requiring a reload. Search matches name or SKU
case-insensitively. Delete is immediate and has no undo.

**GitHub Pages hosts PROJECT.html only; it cannot run this Java backend.**
There is no browser simulation disguised as a running server.

## Design and boundaries

`CatalogServer` handles exact routes, form parsing and escaped HTML;
`Catalog` validates immutable records, checks versions and commits snapshots.
Writes are synchronized within a process; a file lock excludes another opener.
Each successful mutation increments a persistent global revision. Deleting and
recreating a SKU therefore cannot make an old form valid again.

A write builds a candidate snapshot, flushes a temporary file, then requests an
atomic replacement in the same directory. Memory changes only after replacement
succeeds. Unsupported atomic moves fail rather than silently use a weaker
fallback. Corrupt snapshots fail startup and are retained for inspection.
This is a small file store, not an ACID database: parent-directory fsync,
power-loss recovery guarantees, backup/restore and multi-host coordination are
not implemented. Do not manually edit storage while the process is running.

The server binds to IPv4 loopback, checks the Host header, uses an unpredictable
per-process form token, rejects foreign Origin headers and escapes stored text.
It also limits form bodies to 8 KiB, queries to 2 KiB and catalogs to 1,000 rows.
No authentication, authorization, TLS, audit trail, request timeout framework,
pagination or production load testing is provided. Do not expose it through a
proxy or use it for sensitive records. Snapshot writes are O(n); full-page
rendering and four worker threads are appropriate only to this small local demo.

## Actual verification

On 2026-10-30, Windows / Temurin **21.0.12.1**, compilation with `--release 17`
and the dependency-free test runner produced:

```text
PASS exact money and invalid numeric formats
PASS CRUD, Unicode search, validation and restart
PASS stale edit, duplicate create and delete/recreate ABA
PASS two competing edits: exactly one commits
PASS second opener lock exclusion and lock release
PASS corrupt snapshots fail closed and retain bytes
PASS failed storage commit does not publish memory
PASS HTTP CRUD, escaping, conflict and method semantics
PASS HTTP CSRF, cross-origin, malformed and oversized requests
PASS strict form parsing
RESULT: 10 tests passed, 0 failed
```

Tests use temporary directories and actual loopback HTTP requests, not mocked
responses. Lock exclusion is tested with two openers in one JVM (the underlying
OS file-lock mechanism is used); no separate-process crash test was performed.
The failed-save test makes the destination an occupied directory and checks that
memory remains unchanged. It does not simulate a power failure. JDK 17 runtime,
Linux/macOS and visual browser rendering were not tested. No workflow was added,
modified or invoked for this supplement.

## 中文说明

这是本次新编写的 AI 辅助工程补充，主题来自教材第 5 章商品管理示例。
教材源代码、数据库配置及压缩包均未转载；不宣称用户独立完成了这份实现，
也不宣称有真实用户、实习业务数据或研究成果。第 13 章会员管理未采用。

实现覆盖商品增删改查、金额与库存校验、文件持久化、并发版本冲突及
HTTP 表单边界。与项目 07 的内存数据结构侧重点不同。本机实际运行了
10 组测试并全部通过；静态简报不能执行 Java 服务。详细来源与分工见
[PROVENANCE.md](PROVENANCE.md)。未来可在需要时替换为 JDBC 事务存储，
补充用户权限及审计；这些属于未实现的后续工作。

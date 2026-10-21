# 07 · Workforce System in Java

**Independent undergraduate coursework · Data structures and information systems**

This project models an organization as a department tree and indexes employees in a self-balancing AVL tree. Adding, transferring, and removing an employee must preserve the correspondence between the two structures. Ordered IDs do not turn the employee index into a linear chain.

## What it demonstrates

- AVL insertion and deletion with cached heights and single/double rotations.
- Immutable `Employee` records with salary represented as nonnegative `long` integer cents.
- A single employee-node lookup during transfer; transferring replaces the record without changing its ID or the tree shape.
- Department membership sets, iterative department subtree counts, immutable ID-ordered snapshots, and inclusive salary-range queries.
- A `verify()` method that checks strict ID ordering, actual versus cached heights, AVL balance, exact department membership, and total counts.
- JUnit 5 tests using an independent `TreeMap` oracle and a reproducible `Random(42)` operation sequence.

## Business behavior

- Department `0` is the organization root and may directly contain employees. Other department IDs must be positive and unique, with an existing parent. `count(id)` includes both direct employees and every descendant department.
- Employee IDs must be positive and unique. Names must be nonblank. A record's department is checked against this organization when it is added; constructing a record alone does not create or validate a department.
- Salary is an exact amount in cents: `650000` represents `6500.00` currency units. Currency, pay period, taxes, and payroll calculations are outside this model. Zero and `Long.MAX_VALUE` cents are accepted without conversion to floating point.
- `find(id)` returns `null` for an absent ID. Invalid department IDs, duplicate employee IDs, missing employees during removal/transfer, and invalid salary ranges throw `IllegalArgumentException`. As before, passing a null record to `add` throws `NullPointerException`.
- A transfer to the current department is a no-op. A transfer between departments preserves ID, name, and salary. Previously returned records and lists remain unchanged.
- `sortedEmployees()` and `salaryRange(minimum, maximum)` return immutable snapshots ordered by employee ID. The salary range includes both endpoints; it is not sorted by salary.
- Deleting a node with two children preserves the successor's complete record and department membership. Deleted employee IDs can subsequently be reused.
- Rejected validation operations leave the organization unchanged. This is not a transactional guarantee under resource exhaustion or concurrent access.

## Build and verification

Use JDK 17 or newer and Maven 3.8 or newer. Run these commands from this project directory:

```sh
mvn clean test
java -cp target/classes Workforce
```

The Maven compiler targets Java 17. JUnit Jupiter 5.11.4 and Surefire 3.5.2 discover and run the tests; no `-ea` flag or custom test runner is required. The first Maven run needs access to a Maven repository to resolve plugins and test dependencies. The application itself has no external runtime dependencies.

Source files follow Maven's standard layout:

```text
pom.xml
src/main/java/Workforce.java
src/test/java/WorkforceTest.java
```

For the standalone demonstration without Maven or JUnit, from this project directory in PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path target/demo | Out-Null
javac --release 17 -d target/demo src/main/java/Workforce.java
java -cp target/demo Workforce
```

In a POSIX shell, replace the directory-creation line with `mkdir -p target/demo`. The JUnit test source requires Maven-resolved test dependencies and is not part of the standalone `javac` command.

The test suite covers:

- All four insertion rotations, deletion rotations including a balanced heavy child, root/leaf/one-child/two-child deletion, and successor replacement across departments.
- Ascending and descending insertion of **50,000 employees per case**, transfer of every third employee, then alternating minimum/maximum deletion until empty. Checkpoints compare the entire result and department counts with `TreeMap`, call `verify()`, and check a logarithmic height bound; there is no machine-dependent timing assertion.
- **5,000 mixed operations using `Random(42)`**, including successful and rejected additions, removals, transfers, and lookups. Each step compares sorted records, department counts, a salary range, and structural invariants against the reference model.
- A **20,000-level department hierarchy**, invalid inputs, duplicate IDs, same-department transfers, immutable snapshots, inclusive salary endpoints, maximum employee ID, and maximum salary.
- Deliberately corrupted cached heights, balance, ordering, and membership, ensuring that `verify()` rejects invalid states. These structural tests use reflection without exposing mutable internals through the application API.

The dataset sizes above describe test inputs. On 2026-10-21, `mvn verify`
with Temurin 17 and Maven 3.9.9 on Windows completed **33 JUnit tests:
0 failures, 0 errors, 0 skipped**. Subsequent runs report their own results in
`target/surefire-reports`; CI execution status is available from the root README.

## Complexity and design limits

Let `n` be the employee count, `d` the department count, and `s` the number of departments in the requested subtree.

| Operation | Time | Additional working space |
| --- | --- | --- |
| `find` | O(log n) worst-case AVL search | O(1) |
| `add`, `remove` | O(log n) AVL work; expected/amortized O(1) membership/map updates | O(log n) recursive stack |
| `transfer` | One O(log n) search; expected/amortized O(1) membership/map updates | O(1) |
| `addDepartment` | Expected/amortized O(1) | O(1) new department, excluding container resizing |
| `sortedEmployees`, `salaryRange` | O(n) | O(n) snapshots plus O(log n) traversal stack |
| `count` | O(s), using each membership set's size | O(s) explicit stack in the worst case |
| `verify` | Expected O(n + d) | O(n) membership map, O(log n) employee stack, O(d) department stack |

AVL height is O(log n), so insertion, deletion, and employee traversal recursion stays logarithmic even for ordered IDs. Department trees need not be balanced; their counts use an explicit stack. Membership uses `LinkedHashSet` for expected constant-time updates and iteration proportional to the current membership size. Hash-table operations and occasional container resizing do not have the same per-operation worst-case guarantee as the AVL index itself. Space entries exclude persistent storage for added records and temporary allocation during container resizing.

Salary queries scan the ID index; there is no secondary salary index. `verify()` is an explicit diagnostic and is not automatically run after production mutations. It validates states reachable through this API and the documented invariants; it is not a general recovery tool for arbitrary reflective corruption of the department graph.

This is a single-threaded, in-memory teaching system with synthetic records. It has no persistence, concurrency control, authorization, department deletion/reparenting, or payroll processing. Counts use `int`, and data volume is limited by available heap. It is not a production HR or payroll application.

The project is independently completed coursework. The implementation and tests were refined for this portfolio with AI assistance; see the repository's AI-use statement.

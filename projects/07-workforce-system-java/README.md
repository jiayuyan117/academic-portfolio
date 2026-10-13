# 07 · Workforce System in Java

**Independent undergraduate coursework · Data structures and information systems**

This project models an organization as a department tree and indexes employees in a binary search tree. The interesting part is the invariant between the two structures: adding, transferring, and removing an employee must never leave a stale department membership behind.

## What it demonstrates

- Explicit validation for IDs, departments, names, salary ranges, and duplicate records.
- Immutable employee records with salary represented as integer cents.
- Department subtree counts, sorted employee traversal, and salary-range queries.
- A `verify()` method that checks organization membership, uniqueness, ordering, and total counts.
- A seeded behavioral test suite compared with a `TreeMap` reference model.

## Verification

```text
PASS: 2013 checks; 1000 seeded operations;
invariant checks after every operation.
```

Run with JDK 17 or newer:

```bash
javac Workforce.java WorkforceTest.java
java Workforce
java WorkforceTest
```

## Design limits

The employee index is an unbalanced BST, so operations can degrade to O(n). This is a single-threaded, in-memory teaching system with synthetic records; it is not a production HR or payroll application.

The project is independently completed coursework. The implementation and tests were refined for this portfolio with AI assistance; see the repository's AI-use statement.

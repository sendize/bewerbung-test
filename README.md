# Compliance Change Detector

This repository contains a take-home assignment solution for detecting changes between two snapshots of a German regulatory register.

## Contents

- `solution/changes_detector.py` — main Part 1 script. Compares Q1 and Q2 regulation CSV files and writes `output/changes.json`.
- `solution/regulation.py` — small data model and CSV loader for regulations.
- `solution/test_detect_changes.py` — unit tests for minor changes, renumbering, and full diff behavior.
- `output/changes.json` — generated structured diff committed for review.
- `DESIGN.md` — Part 2 relevance-mapping design.
- `INSTRUCTIONS.md` — original English assignment instructions.

## Run The Detector

From the repository root:

```bash
python solution/changes_detector.py
```

The script reads:

- `data/regulations_2025_q1.csv`
- `data/regulations_2025_q2.csv`

It writes:

- `output/changes.json`

## Run Tests

```bash
python -m unittest solution/test_detect_changes.py
```

## Output Shape

Each change uses one of the Part 1 change types: `NEW`, `REPEALED`, `MODIFIED`, or `RENUMBERED`.

Minor typo-only edits are still emitted as `MODIFIED`, with `substantive: false` so downstream relevance matching can ignore them.

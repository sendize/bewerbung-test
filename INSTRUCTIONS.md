# Take-Home Assignment: Compliance Platform — Regulatory Changes ↔ Customers

Welcome! This assignment is a simplified version of the real work we do at Acurento (and WP Engineers) on our **Legal Register Platform** — a system that tracks German environmental and safety regulations and helps our customers remain compliant.

With this assignment, we want to understand your **system and product thinking** — not just how cleanly you write code.

## Time Budget — Please Respect It

**Maximum 3–4 hours** for all three parts combined. After 4 hours, please stop, even if everything is not finished. Briefly note what you had to leave out and why — this prioritization is part of the evaluation. We explicitly do not evaluate who spends the most time on the assignment.

---

## Background (60 Seconds Reading)

German industrial companies are subject to a wide range of environmental and safety regulations (BImSchG, KrWG, GefStoffV, WHG, etc.). These regulations change constantly — new sections are added, old ones are repealed, and thresholds are tightened.

Our platform should automatically determine:

1. **What has changed?** (Diff between snapshots of a regulatory register)
2. **Who is affected by the change?** (Which of our customers must react?)

The second question is the difficult one — and the core of this assignment.

---

## The Three Parts

### Part 1 — Code: Change Detection (~1.5 hours)

Write a script (Python preferred, language of your choice) that compares two snapshots of a regulatory register and produces a structured diff.

**Input** in `data/`:

- `regulations_2025_q1.csv` — state at the beginning of Q1 2025
- `regulations_2025_q2.csv` — state at the beginning of Q2 2025

Both CSVs (semicolon-separated, German convention) have the schema:

```text
gesetz;paragraph;titel;text_hash;status;gueltig_ab;kommentar
```

**Expected output:** `output/changes.json` containing a list of changes:

```json
[
  {
    "type": "NEW",
    "law": "GefStoffV",
    "paragraph": "§8a",
    "title": "...",
    "reason": "..."
  },
  {
    "type": "REPEALED" | "MODIFIED" | "RENUMBERED",
    ...
  }
]
```

**Edge cases we care about:**

- **Renumbering** — if a paragraph only changes its number (for example, after a new paragraph is inserted before it), it should not appear as (REPEALED + NEW). How would you detect that?
- **Substantive vs. minor changes** — some hash changes are only typo corrections (see the `kommentar` field). Should those be treated differently from content changes?
- **Repealed paragraphs remain in the register** — with the status flag `"aufgehoben"` (repealed). How do you distinguish that from a completely missing entry?

**No need for a testing marathon** — 1–2 meaningful unit tests are sufficient. Code should be readable and assumptions documented.

### Part 2 — Design: Relevance Mapping (~1.5 hours, no code)

**The core of the assignment.** Pure design exercise.

**Given:**

- The changes produced by your script in Part 1
- `data/customer_profiles.json` — six customer profiles from different industries (plant operators, logistics, chemicals, water utilities, etc.) with different properties (facilities, handled hazardous materials, water usage, location, size)

**Question:** How does your system determine **which change affects which customer**?

Provide **three deliverables** — sketches or prose, **no code**:

#### 1. Data Model Sketch

(ER diagram, structured list, or any format that communicates your idea quickly.)

How would you store:

- Customer properties in a way that they can be matched?
- Applicability rules of a regulation (e.g., "applies to facilities ≥ 5 t/h classified as 3.1.1 under the 4th BImSchV")?

#### 2. Matching Logic in Prose

(1–2 pages)

For **each change** from Part 1, explain which of the six customers would be affected — and why (or why not).

Where do false positives and false negatives arise? How do you handle uncertainty?

#### 3. UI Sketch for the Review Workflow

(Any medium: paper photo, ASCII, Figma, HTML, etc.)

For uncertain matches, a consultant must review them manually. Sketch the screen.

What does the consultant see?
What actions can they take?
What helps them make a decision quickly?

**What we evaluate:**

- **Realism** — not a simplistic "tag everything and we're done" solution
- **Handling uncertainty** — false positives waste consultant time, false negatives can result in customer penalties. How do you balance that?
- **Clear separation** between master data (customer, regulation), rules (who is affected), and inference (what action follows)

### Part 3 — Creative: Add-ons & Extensions (~1 hour)

Imagine Parts 1 and 2 have been built and are running in production. What is still missing so that our **consultants love the system** and our **customers are willing to pay more for it**?

#### Format

1. List **3–5 add-on features**, each with a 2–3 sentence description.
2. Choose **one** of them and write a **one-page deep dive**:
   - What exactly are you building?
   - Why is it valuable (for consultants OR customers)?
   - High-level implementation sketch (components, data flow, key decisions)
   - What is the biggest risk or challenge?

There is no "correct" answer. We want to see how you think about the product.

---

## What We Evaluate

| Part | Weight | What We Look For |
|------|--------|------------------|
| Part 1 — Correctness | 20% | Diff is correct; renumbering trap identified |
| Part 1 — Code Quality | 10% | Readable, ≥1 test, assumptions documented |
| Part 2 — Data Model | 20% | Realistic, extensible, clear separation of concerns |
| Part 2 — Matching Logic | 20% | Addresses uncertainty, concrete per example |
| Part 2 — UI Sketch | 10% | Actually helps consultants; not just a data dump |
| Part 3 — Add-on List | 10% | At least 3 meaningful ideas, clear prioritization |
| Part 3 — Deep Dive | 10% | Concrete and aware of risks |

---

## What Happens Next

If the assignment receives a positive evaluation, we will invite you to a **60–90 minute live walkthrough**:

- You guide us through your code, design, and add-on proposal
- We challenge specific decisions and assumptions
- Collaborative live extension: we introduce a new scenario and you show how you would adapt the system and/or UI

---

## Submission

- **Git repository** (GitHub/GitLab link) or **ZIP file** via email
- README in the repository: How do I run your script?
- Commit the output file `output/changes.json` to the repository
- Design deliverables (data model, matching logic, UI sketch, add-ons) should be visible in the project root (e.g., `DESIGN.md`, `ADDONS.md`, or PDF)

If you have any questions, feel free to reach out — we will respond within 24 hours.

Good luck!

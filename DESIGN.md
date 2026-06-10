# Part 2 — Design: Relevance Mapping

## 1. Data Model Sketch

### Entities

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│    Customer     │       │  ApplicabilityRule   │       │   Regulation    │
├─────────────────┤       ├─────────────────────┤       ├─────────────────┤
│ id (PK)         │◄──────│ regulation_key       │──────►│ key (PK)        │
│ name            │  M:N  │ customer_attribute   │  1:N │ gesetz          │
│ branche         │       │ attribute_operator    │      │ paragraph       │
│ mitarbeiter     │       │ attribute_value       │      │ titel           │
│ standort        │       │ threshold_value       │      │ status          │
│ anlagen[]       │       │ effective_from        │      │ text_hash       │
│ gefahrstoffe[]  │       │ effective_to          │      │ kommentar       │
│ wassernutzung   │       │ confidence            │      └─────────────────┘
│ abfallarten[]   │       │ reviewed_by           │
│ stoerfall_verord│       │ reviewed_at           │
└─────────────────┘       │ review_status         │
                          │ rule_type             │
                          └─────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   ChangeCustomerMatch                            │
├──────────────────────────────────────────────────────────────────┤
│ id (PK)                                                         │
│ change_id  ──► changes[] (from output/changes.json)             │
│ customer_id ──► Customer.id                                     │
│ applicability_rule_id ──► ApplicabilityRule.id                  │
│ confidence: HIGH | MEDIUM | LOW                                 │
│ match_reason: text explanation                                  │
│ review_status: AUTO_APPROVED | NEEDS_REVIEW | REJECTED          │
│ consultant_notes: free text                                     │
│ reviewed_at: timestamp                                          │
└──────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**Separation of concerns:**
- **Master data** (Customer, Regulation) — facts about the world
- **Rules** (ApplicabilityRule) — declarative mapping: "this regulation applies when customer has these properties"
- **Inference** (ChangeCustomerMatch) — computed: which customers need to react to which change

**Why rules, not tags:** Tagging every regulation with every affected customer is not scalable. Rules encode the *logic* ("applies to Anlagen ≥ 5 t/h classified as 3.1.1"), so new customers auto-match and new thresholds can be evaluated without manual re-tagging.

### ApplicabilityRule Schema (Detailed)

```json
{
  "rule_id": "AR-BImSchG-5-311",
  "regulation_key": ["BImSchG", "§5"],
  "rule_type": "THRESHOLD",
  "conditions": [
    {
      "path": "anlagen_4_bimschv[].nummer",
      "operator": "IN",
      "value": ["3.1.1"]
    },
    {
      "path": "anlagen_4_bimschv[].kapazitaet_t_h",
      "operator": "GTE",
      "value": 5.0
    }
  ],
  "logic": "AND",
  "effective_from": "2025-04-01",
  "confidence": "HIGH"
}
```

---

## 2. Matching Logic — Per Change, Per Customer

### Change 1: BImSchG §5 — MODIFIED (substantive)
> Schwellenwert für genehmigungsbedürftige Anlagen Nr. 3.1.1 von 10 t/h auf 5 t/h gesenkt.

| Customer | Affected? | Reasoning |
|---|---|---|
| **K-001 Müller Eisengießerei** | **YES — HIGH** | Has Anlage 3.1.1 at 8 t/h. Old threshold: 10 t/h (below → not affected). New threshold: 5 t/h (above → now subject to full operator duties). This is a direct, high-impact hit. |
| K-002 Logistik Schmidt | No | No 4.BImSchV Anlagen at all. |
| K-003 Vetter Lebensmittel | No | Has Anlage 7.4 (Schlachtanlage), not 3.1.1. Different Anlage number → threshold change irrelevant. |
| K-004 Bauunternehmen Klein | No | No 4.BImSchV Anlagen. |
| **K-005 ChemPro Industries** | **MEDIUM — uncertain** | Has Anlagen 4.1.1 and 9.1.1, not 3.1.1. Directly: no. But §5 covers "Pflichten der Betreiber genehmigungsbedürftiger Anlagen" generally — the threshold change could indicate broader tightening of operator duties worth flagging for review. |
| K-006 Stadtwerke Bernau | No | No 4.BImSchV Anlagen. |

**False positive risk:** K-005 is a borderline case. Flagging a large chemical manufacturer for a threshold change that doesn't apply to their Anlage type wastes consultant time. Mitigation: rule-based matching only flags K-001; K-005 would only appear if a consultant manually broadens the search.

---

### Change 2: KrWG §7 — MODIFIED (minor / typo correction)
> Sprachliche Klarstellung in Absatz 2 (Tippfehler-Korrektur); keine inhaltliche Änderung.

| Customer | Affected? | Reasoning |
|---|---|---|
| All six customers | **No** | The `kommentar` field explicitly states no substantive change. System should auto-filter this out — no customer notification needed. |

**Design note:** This is the "substantive vs minor" edge case. The system checks `_is_typo_only()` on the kommentar and skips matching entirely for `MINOR_CHANGE` types. The change is logged for audit but does not enter the relevance pipeline.

---

### Change 3: WHG §3 — REPEALED
> Begriffsbestimmungen aufgehoben durch Artikel 4 des Gesetzes vom 18.02.2025; Begriffe nun im neuen Begriffskatalog des UmweltrahmenG.

| Customer | Affected? | Reasoning |
|---|---|---|
| K-001 Müller | No | Has Industriewasser-Entnahme but WHG §3 was a definitions paragraph. Repeal of definitions is a structural change — impact depends on whether definitions changed substantively. |
| K-002 Logistik | No | No water operations. |
| **K-003 Vetter Lebensmittel** | **MEDIUM** | Has "Abwasserdirekteinleitung in Vorfluter (genehmigt)". WHG definitions underpin their wastewater permit. If definitions changed, permit conditions may need reinterpretation. |
| K-004 Bauunternehmen Klein | No | No water operations. |
| **K-005 ChemPro Industries** | **MEDIUM** | Has "Grundwasser-Entnahme + Direkteinleitung von Prozessabwasser". Heavy water user — definitions affect groundwater classification and discharge limits. |
| **K-006 Stadtwerke Bernau** | **HIGH** | Core business is Trinkwasser-Förderung from 4 Brunnen in Wasserschutzgebieten. WHG definitions are central to their entire compliance framework. Definitions moved to UmweltrahmenG — they need to know where to look now. |

**False negative risk:** If the definitions didn't actually change (just relocated), K-003 and K-005 might be over-alerted. Mitigation: the consultant review screen shows the old and new definition sources side by side so the consultant can quickly assess whether the move is purely structural or carries substantive changes.

---

### Change 4: BImSchG §15 → §15a — RENUMBERED (content changed)
> Umnummeriert nach Einfügung eines neuen §15 (Datenübermittlung an Behörden).

| Customer | Affected? | Reasoning |
|---|---|---|
| **K-001 Müller** | **YES — HIGH** | Has genehmigungsbedürftige Anlage 3.1.1. §15 "Anzeige bei Änderungen" governs their obligation to report plant modifications. Renumbering means their internal compliance checklists and references need updating. Content changed → obligations may have shifted. |
| K-002 Logistik | No | No genehmigungsbedürftige Anlage. |
| **K-003 Vetter** | **YES — HIGH** | Has genehmigungsbedürftige Anlage 7.4. Same reasoning as K-001. |
| K-004 Bauunternehmen Klein | No | No genehmigungsbedürftige Anlage. |
| **K-005 ChemPro** | **YES — HIGH** | Has two genehmigungsbedürftige Anlagen (4.1.1, 9.1.1). Directly affected. |
| K-006 Stadtwerke Bernau | No | No genehmigungsbedürftige Anlage. |

**False positive risk:** Low. The renumbered paragraph's content changed — any customer with a genehmigungsbedürftige Anlage should be notified. The rule: `IF customer.anlagen_4_bimschv.length > 0 THEN match`.

---

### Change 5: GefStoffV §8a — NEW
> Neuer Paragraph: Schutzmaßnahmen bei Tätigkeiten mit krebserzeugenden Stoffen der Kategorie 1A oder 1B.

| Customer | Affected? | Reasoning |
|---|---|---|
| **K-001 Müller** | **YES — HIGH** | Handles Cadmium-Verbindungen (CMR 1B) and Formaldehyd (CMR 1B). Direct match on CMR category. |
| K-002 Logistik | No | Only handles Diesel (CMR 2), not 1A/1B. |
| K-003 Vetter | No | No CMR substances. NaOH and Ammoniak are not CMR 1A/1B. |
| K-004 Bauunternehmen Klein | No | No Gefahrstoffe at all. |
| **K-005 ChemPro** | **YES — HIGH** | Explicitly handles "verschiedene CMR-Stoffe (Kategorie 1A und 1B)". Direct, unambiguous match. |
| K-006 Stadtwerke Bernau | No | Only handles Chlor (not CMR). |

**False negative risk:** The customer profile lists CMR categories explicitly. If a customer has CMR substances not flagged with a category, they'd be missed. Mitigation: flag unmatched customers whose `gefahrstoffe` list is non-empty but has `cmr_kategorie: null` for consultant review.

---

### Summary Matrix

```
Change                    K-001    K-002    K-003    K-004    K-005    K-006
────────────────────────────────────────────────────────────────────────────
BImSchG §5 MODIFIED       HIGH       -        -        -     MED        -
KrWG §7 MINOR              -         -        -        -      -         -
WHG §3 REPEALED           -         -      MED        -     MED      HIGH
BImSchG §15→15a RENUM     HIGH       -     HIGH        -    HIGH        -
GefStoffV §8a NEW         HIGH       -        -        -    HIGH        -
```

### Handling Uncertainty

Three confidence tiers:

| Tier | Behavior |
|---|---|
| **HIGH** | Auto-notify customer. No consultant review needed. |
| **MEDIUM** | Enters consultant review queue. Must be approved or dismissed before customer notification. |
| **LOW** | Logged for audit only. Consultant review optional. |

**Balancing false positives vs false negatives:** The system errs toward false positives (over-notification) for HIGH-impact changes (NEW, MODIFIED-substantive). For structural changes (REPEALED definitions, RENUMBERED), it uses MEDIUM to trigger review. Minor changes (MINOR_CHANGE) are filtered out entirely — false negative risk is acceptable here because the content didn't change.

---

## 3. UI Sketch — Consultant Review Screen

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ACURENTO COMPLIANCE PLATFORM  │  Consultant Review  │  🔔 3 pending items      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Change Card ─────────────────────────────────────────────────────────────┐  │
│  │  WHG §3 — Begriffsbestimmungen                                          │  │
│  │  Type: REPEALED  │  Confidence: MEDIUM                                   │  │
│  │  "Aufgehoben durch Artikel 4 des Gesetzes vom 18.02.2025; Begriffe      │  │
│  │   nun im neuen Begriffskatalog des UmweltrahmenG"                        │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ── Affected Customers (2 pending) ──────────────────────────────────────────  │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  K-006  Stadtwerke Bernau Wasserversorgung         [HIGH confidence]     │  │
│  │  Match rule: AR-WHG-water-ops (wassernutzung != null)                    │  │
│  │  Rationale: Core business is water supply. WHG definitions are           │  │
│  │             central to their compliance framework.                       │  │
│  │                                                                          │  │
│  │  [✓ Approve & Notify]   [✗ Dismiss]   [📝 Add Note]                     │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  K-005  ChemPro Industries GmbH                      [MED confidence]    │  │
│  │  Match rule: AR-WHG-water-ops (wassernutzung != null)                    │  │
│  │  Rationale: Grundwasser-Entnahme + Direkteinleitung. Definitions          │  │
│  │             may affect groundwater classification.                        │  │
│  │                                                                          │  │
│  │  [✓ Approve & Notify]   [✗ Dismiss]   [📝 Add Note]                     │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ── Evidence Panel (click customer row to expand) ──────────────────────────  │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Customer Properties:                                                    │  │
│  │    wassernutzung: "Grundwasser-Entnahme + Direkteinleitung..."            │  │
│  │    abfallarten: ["Lösemittelabfälle", "Reaktionsrückstände", ...]         │  │
│  │                                                                          │  │
│  │  Old Regulation: WHG §3 (Begriffsbestimmungen, 2009-07-31)               │  │
│  │  New Source: UmweltrahmenG Begriffskatalog (in Kraft 01.07.2025)         │  │
│  │                                                                          │  │
│  │  Quick Diff: [Show Side-by-Side]  ← helps consultant decide              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ── Batch Actions ─────────────────────────────────────────────────────────  │
│  [Approve All]  [Dismiss All]  [Escalate to Senior Consultant]                │
│                                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### What the Consultant Sees

1. **Change card** at top — law, paragraph, type, confidence, reason text. Always visible.
2. **Customer match list** — each matched customer with confidence level, matching rule ID, and rationale.
3. **Evidence panel** — expandable per customer. Shows the customer's relevant properties, the old and new regulation sources, and a diff link for side-by-side comparison.
4. **Per-customer actions** — Approve (notify), Dismiss (skip), Add Note (attach context for future audits).
5. **Batch actions** — approve or dismiss all remaining matches at once. Escalation option for complex cases.

### What Helps the Consultant Decide Quickly

- **Confidence color coding:** green (HIGH), yellow (MEDIUM), gray (LOW). At a glance, the consultant knows which items need attention.
- **Rule ID in match rationale:** every match traces back to a specific ApplicabilityRule. If a rule is producing too many false positives, the consultant can flag the rule itself for adjustment, not just the individual match.
- **Side-by-side diff link:** for REPEALED/RENUMBERED changes where the content moved to a new source, the consultant can compare old vs new text without leaving the screen.
- **Customer property highlight:** only the relevant properties are shown (e.g., `wassernutzung` for a WHG change), reducing cognitive load.

### Actions Available

| Action | Effect |
|---|---|
| **Approve & Notify** | Customer receives notification. Match is logged as AUTO_APPROVED → APPROVED. |
| **Dismiss** | Customer is skipped. Reason must be provided if confidence was HIGH. |
| **Add Note** | Free-text annotation attached to the match. Does not change status. |
| **Escalate** | Flags the match for a senior consultant or domain expert. |
| **Adjust Rule** | Opens the ApplicabilityRule editor inline. Allows tightening or loosening the matching condition. |

import json
import os
from difflib import SequenceMatcher

from regulation import Regulation

MINOR_CHANGE_KEYWORDS = [
    "tippfehler",
    "sprachlich",
    "klarstellung",
    "keine inhaltliche",
    "formatierung",
]
RENAMING_TITLE_THRESHOLD = 0.7


def is_minor_change(kommentar: str) -> bool:
    """Return True when the comment indicates a non-substantive edit."""
    if not kommentar:
        return False
    text = kommentar.lower()
    return any(keyword in text for keyword in MINOR_CHANGE_KEYWORDS)


def _title_similarity(title1: str, title2: str) -> float:
    """Return a fuzzy title similarity score for renumbering detection."""
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def detect_renumberings(removed: list[Regulation], added: list[Regulation]):
    """Match removed and added regulations that likely represent renumberings.

    Prefer exact content-hash matches. If the content changed during the renumbering,
    fall back to title similarity within the same law. Each added regulation can only
    be paired once.

    Returns (renumbered_pairs, remaining_removed, remaining_added).
    Each pair is (old_reg, new_reg).
    """
    renumbered = []
    paired_removed = set()
    paired_added = set()

    # Try to pair removed and added entries before classifying them as repealed/new.
    for old_reg in sorted(removed, key=lambda reg: reg.keys):
        best_match = None
        best_score = 0.0

        for new_reg in sorted(added, key=lambda reg: reg.keys):
            if new_reg.keys in paired_added:
                continue
            if old_reg.gesetz != new_reg.gesetz:
                continue

            # Same content under a new paragraph number is the strongest signal.
            if old_reg.text_hash == new_reg.text_hash:
                best_match = new_reg
                best_score = 2.0
                break

            # If the text changed during renumbering, title similarity is the fallback.
            score = _title_similarity(old_reg.titel, new_reg.titel)
            if score >= RENAMING_TITLE_THRESHOLD and score > best_score:
                best_match = new_reg
                best_score = score

        if best_match is not None:
            renumbered.append((old_reg, best_match))
            paired_removed.add(old_reg.keys)
            paired_added.add(best_match.keys)

    remaining_removed = [reg for reg in removed if reg.keys not in paired_removed]
    remaining_added = [reg for reg in added if reg.keys not in paired_added]

    return renumbered, remaining_removed, remaining_added


def detect_changes(older_file: str, newer_file: str) -> list[dict]:
    """Compare two register snapshots and return Part 1 change records."""
    # Load both register snapshots. CSV parsing intentionally stays in Regulation.
    old_regulations = Regulation.from_csv(older_file)
    new_regulations = Regulation.from_csv(newer_file)

    # Use (law, paragraph) as the stable identity for direct comparisons.
    old_key_dict = {reg.keys: reg for reg in old_regulations}
    new_key_dict = {reg.keys: reg for reg in new_regulations}
    common_keys = old_key_dict.keys() & new_key_dict.keys()

    removed_regs = [old_key_dict[k] for k in old_key_dict.keys() - new_key_dict.keys()]
    added_regs = [new_key_dict[k] for k in new_key_dict.keys() - old_key_dict.keys()]

    changes = []

    # Entries with the same key can be modified or repealed via status flag.
    for k in sorted(common_keys):
        old_reg = old_key_dict[k]
        new_reg = new_key_dict[k]

        # Repealed paragraphs may remain in the register with status "aufgehoben".
        if old_reg.status == "in_force" and new_reg.status == "aufgehoben":
            changes.append(
                {
                    "type": "REPEALED",
                    "law": old_reg.gesetz,
                    "paragraph": old_reg.paragraph,
                    "title": old_reg.titel,
                    "reason": f"Status changed to 'aufgehoben' (repealed). {new_reg.kommentar}".strip(),
                }
            )
            continue

        # Hash changes are always MODIFIED; substantive=false marks typo-only edits.
        if old_reg.text_hash != new_reg.text_hash:
            minor = is_minor_change(new_reg.kommentar)
            changes.append(
                {
                    "type": "MODIFIED",
                    "law": new_reg.gesetz,
                    "paragraph": new_reg.paragraph,
                    "title": new_reg.titel,
                    "substantive": not minor,
                    "reason": new_reg.kommentar or "Content hash changed",
                }
            )
            continue

        # Other status transitions are treated as substantive modifications.
        if old_reg.status != new_reg.status:
            changes.append(
                {
                    "type": "MODIFIED",
                    "law": new_reg.gesetz,
                    "paragraph": new_reg.paragraph,
                    "title": new_reg.titel,
                    "substantive": True,
                    "reason": f"Status changed from '{old_reg.status}' to '{new_reg.status}'",
                }
            )

    renumbered, remaining_removed, remaining_added = detect_renumberings(
        removed_regs, added_regs
    )

    # Renumbered entries are reported once, not as REPEALED + NEW.
    for old_reg, new_reg in renumbered:
        hash_changed = old_reg.text_hash != new_reg.text_hash
        minor = hash_changed and is_minor_change(new_reg.kommentar)
        changes.append(
            {
                "type": "RENUMBERED",
                "law": new_reg.gesetz,
                "old_paragraph": old_reg.paragraph,
                "new_paragraph": new_reg.paragraph,
                "title": new_reg.titel,
                "content_changed": hash_changed,
                "substantive": hash_changed and not minor,
                "reason": new_reg.kommentar
                or f"Renumbered from {old_reg.paragraph} to {new_reg.paragraph}",
            }
        )

    # Entries still missing after renumbering detection are true removals.
    for reg in sorted(remaining_removed, key=lambda old_reg: old_reg.keys):
        changes.append(
            {
                "type": "REPEALED",
                "law": reg.gesetz,
                "paragraph": reg.paragraph,
                "title": reg.titel,
                "reason": "Entry removed from register entirely",
            }
        )

    # Entries still new after renumbering detection are true additions.
    for reg in sorted(remaining_added, key=lambda new_reg: new_reg.keys):
        changes.append(
            {
                "type": "NEW",
                "law": reg.gesetz,
                "paragraph": reg.paragraph,
                "title": reg.titel,
                "reason": reg.kommentar or "New regulation added to register",
            }
        )

    return changes


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "..", "data")
    out_dir = os.path.join(base, "..", "output")

    older_file = os.path.join(data_dir, "regulations_2025_q1.csv")
    newer_file = os.path.join(data_dir, "regulations_2025_q2.csv")

    changes = detect_changes(older_file, newer_file)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "changes.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(changes)} changes to {out_path}")


if __name__ == "__main__":
    main()

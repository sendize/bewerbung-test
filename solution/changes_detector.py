import os
import json

from regulation import Regulation


def _is_typo_only(kommentar: str) -> bool:
    """Check if the kommentar indicates only a typo/minor correction."""
    typo_keywords = ["tippfehler", "sprachliche klarstellung", "keine inhaltliche"]
    return any(kw in kommentar.lower() for kw in typo_keywords)


def _titles_similar(title1: str, title2: str) -> bool:
    """Heuristic: titles are similar if they share a long common substring."""
    t1, t2 = title1.lower(), title2.lower()
    if t1 == t2:
        return True
    # Check for common substring >= 20 chars
    for i in range(len(t1)):
        for j in range(i + 20, len(t1) + 1):
            if t1[i:j] in t2:
                return True
    return False


def detect_renumberings(removed, added):
    """Match removed and added regs that are renumberings (same content, different paragraph).

    Returns (renumbered_pairs, remaining_removed, remaining_added).
    Each pair is (old_reg, new_reg).
    """
    remaining_removed = list(removed)
    remaining_added = list(added)
    renumbered = []

    for old_reg in removed:
        best_match = None
        for new_reg in remaining_added:
            if old_reg.gesetz != new_reg.gesetz:
                continue
            if _titles_similar(old_reg.titel, new_reg.titel):
                best_match = new_reg
                break
        if best_match is not None:
            renumbered.append((old_reg, best_match))
            remaining_added.remove(best_match)
            remaining_removed.remove(old_reg)

    return renumbered, remaining_removed, remaining_added


def main():
    # Declare filepaths.
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "..", "data")
    out_dir = os.path.join(base, "..", "output")

    # Declare the files.
    older_file = os.path.join(data_dir, "regulations_2025_q1.csv")
    newer_file = os.path.join(data_dir, "regulations_2025_q2.csv")

    # Get regulations.
    old_regulations = Regulation.from_csv(older_file)
    new_regulations = Regulation.from_csv(newer_file)

    # Build key dicts (gesetz, paragraph).
    old_key_dict = {reg.keys: reg for reg in old_regulations}
    new_key_dict = {reg.keys: reg for reg in new_regulations}
    common_keys = old_key_dict.keys() & new_key_dict.keys()

    removed_regs = [old_key_dict[k] for k in old_key_dict.keys() - new_key_dict.keys()]
    added_regs = [new_key_dict[k] for k in new_key_dict.keys() - old_key_dict.keys()]

    changes = []

    # --- Common keys: check for modifications, status changes, and minor changes ---
    for k in common_keys:
        old_reg = old_key_dict[k]
        new_reg = new_key_dict[k]

        # Status change: in_force -> aufgehoben means REPEALED
        if old_reg.status == "in_force" and new_reg.status == "aufgehoben":
            changes.append({
                "type": "REPEALED",
                "law": new_reg.gesetz,
                "paragraph": new_reg.paragraph,
                "title": new_reg.titel,
                "reason": new_reg.kommentar or "Status changed to aufgehoben",
            })
            continue

        # Hash changed -> content changed
        if old_reg.text_hash != new_reg.text_hash:
            if _is_typo_only(new_reg.kommentar):
                changes.append({
                    "type": "MINOR_CHANGE",
                    "law": new_reg.gesetz,
                    "paragraph": new_reg.paragraph,
                    "title": new_reg.titel,
                    "reason": new_reg.kommentar or "Minor correction (no substantive change)",
                })
            else:
                changes.append({
                    "type": "MODIFIED",
                    "law": new_reg.gesetz,
                    "paragraph": new_reg.paragraph,
                    "title": new_reg.titel,
                    "reason": new_reg.kommentar or "Content hash changed (substantive modification)",
                })
            continue

        # Status change: aufgehoben -> in_force means reinstated
        if old_reg.status != new_reg.status:
            changes.append({
                "type": "MODIFIED",
                "law": new_reg.gesetz,
                "paragraph": new_reg.paragraph,
                "title": new_reg.titel,
                "reason": f"Status changed from '{old_reg.status}' to '{new_reg.status}'",
            })

    # --- Detect renumberings among removed/added ---
    renumbered, remaining_removed, remaining_added = detect_renumberings(
        removed_regs, added_regs
    )

    for old_reg, new_reg in renumbered:
        changes.append({
            "type": "RENUMBERED",
            "law": new_reg.gesetz,
            "paragraph": new_reg.paragraph,
            "title": new_reg.titel,
            "reason": f"Renumbered from {old_reg.paragraph} to {new_reg.paragraph}. "
                      + (new_reg.kommentar or ""),
        })

    # --- Remaining removed entries (no match found -> truly repealed/removed) ---
    for reg in remaining_removed:
        changes.append({
            "type": "REPEALED",
            "law": reg.gesetz,
            "paragraph": reg.paragraph,
            "title": reg.titel,
            "reason": "Entry no longer present in register",
        })

    # --- Remaining added entries (no match found -> truly new) ---
    for reg in remaining_added:
        changes.append({
            "type": "NEW",
            "law": reg.gesetz,
            "paragraph": reg.paragraph,
            "title": reg.titel,
            "reason": reg.kommentar or "New regulation added to register",
        })

    # Output to file.
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "changes.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(changes, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(changes)} changes to {out_path}")


if __name__ == "__main__":
    main()

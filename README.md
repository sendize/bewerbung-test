# Bewerbungsaufgabe: Compliance-Plattform — Gesetzesänderungen ↔ Kunden

Willkommen! Diese Aufgabe ist ein vereinfachtes Abbild der realen Arbeit, die wir bei
Acurento (und WP Engineers) an unserer **Rechtskataster-Plattform** machen — einem System, das deutsche
Umwelt- und Sicherheits-Regulierungen verfolgt und unseren Kunden hilft, compliant zu bleiben.

Wir wollen mit dieser Aufgabe Ihr **System- und Produktdenken** verstehen — nicht nur,
wie sauber Sie Code schreiben.

## Zeitbudget — bitte einhalten

**Maximal 3–4 Stunden** für alle drei Teile zusammen. Nach 4 Stunden bitte stoppen,
auch wenn nicht alles fertig ist. Notieren Sie kurz, was Sie weglassen mussten und warum
— diese Priorisierung ist Teil der Bewertung. Wir bewerten ausdrücklich nicht, wer am
meisten Zeit investiert.

---

## Hintergrund (60 Sekunden Lesen)

Deutsche Industriebetriebe unterliegen einer Vielzahl von Umwelt- und Sicherheits­
gesetzen (BImSchG, KrWG, GefStoffV, WHG ...). Diese Gesetze ändern sich ständig —
neue Paragraphen kommen, alte werden aufgehoben, Schwellenwerte werden verschärft.

Unsere Plattform soll automatisch erkennen:
1. **Was hat sich geändert?** (Diff zwischen Snapshots eines Gesetzes-Registers)
2. **Wen betrifft die Änderung?** (Welche unserer Kunden müssen reagieren?)

Die zweite Frage ist die schwere — und das Herzstück dieser Aufgabe.

---

## Die drei Teile

### Teil 1 — Code: Change Detection (~1.5 Stunden)

Schreiben Sie ein Skript (Python bevorzugt, Sprache frei), das zwei Snapshots eines
Gesetzes-Registers vergleicht und einen strukturierten Diff produziert.

**Eingabe** in `data/`:
- `regulations_2025_q1.csv` — Stand Anfang Q1 2025
- `regulations_2025_q2.csv` — Stand Anfang Q2 2025

Beide CSVs (Semikolon-getrennt, deutsche Konvention) haben das Schema:

```
gesetz;paragraph;titel;text_hash;status;gueltig_ab;kommentar
```

**Erwartete Ausgabe:** `output/changes.json` mit einer Liste von Änderungen:

```json
[
  {
    "typ": "NEU",
    "gesetz": "GefStoffV",
    "paragraph": "§8a",
    "titel": "...",
    "begründung": "..."
  },
  {
    "typ": "AUFGEHOBEN" | "GEÄNDERT" | "UMNUMMERIERT",
    ...
  }
]
```

**Edge Cases, auf die wir achten:**

- **Umnummerierungen** — wenn ein Paragraph nur die Nummer wechselt (z. B. nach
  Einfügung eines neuen Paragraphen davor), darf das nicht als (AUFGEHOBEN + NEU)
  rauspurzeln. Wie erkennen Sie das?
- **Substantielle vs. minimale Änderungen** — manche Hash-Änderungen sind nur
  Tippfehler-Korrekturen (siehe `kommentar`-Feld). Sollte das anders behandelt
  werden als eine inhaltliche Änderung?
- **Aufgehobene Paragraphen bleiben im Register** — mit Status-Flag "aufgehoben".
  Wie unterscheiden Sie das von "Eintrag fehlt komplett"?

**Kein Test-Marathon nötig** — 1–2 sinnvolle Unit-Tests reichen. Code soll lesbar sein,
Annahmen dokumentiert.

### Teil 2 — Design: Relevanz-Zuordnung (~1.5 Stunden, **kein Code**)

**Das Herzstück der Aufgabe.** Reine Design-Übung.

**Gegeben:**
- Die Änderungen, die Ihr Skript aus Teil 1 produziert
- `data/customer_profiles.json` — sechs Kundenprofile aus verschiedenen Branchen
  (Anlagenbetreiber, Logistik, Chemie, Wasserversorgung etc.) mit unterschiedlichen
  Eigenschaften (Anlagen, gehandhabte Gefahrstoffe, Wassernutzung, Standort, Größe)

**Frage:** Wie entscheidet Ihr System, **welche Änderung welchen Kunden betrifft**?

Liefern Sie **drei Deliverables** — alle als Skizzen oder Prosa, **kein Code**:

1. **Datenmodell-Skizze** (ER-Diagramm, strukturierte Liste, oder was Sie schnell
   ausdrücken können). Wie speichern Sie:
   - die Eigenschaften eines Kunden so, dass sie matchbar sind?
   - die Anwendbarkeits­regeln einer Regulation (z. B. "gilt für Anlagen ≥ 5 t/h
     der Nummer 3.1.1 in 4.BImSchV")?

2. **Matching-Logik in Prosa** (1–2 Seiten). Gehen Sie für **jede** der Änderungen
   aus Teil 1 durch, welcher der sechs Kunden betroffen wäre — und warum (oder warum
   nicht). Wo entstehen False Positives, wo False Negatives? Wie gehen Sie mit
   Unsicherheit um?

3. **UI-Skizze für Review-Workflow** (Medium frei: Papier-Foto, ASCII, Figma, HTML).
   Bei unsicheren Matches muss ein:e Berater:in nachschauen. Skizzieren Sie die
   Bildschirm-Ansicht. Was sieht die Beraterin? Was kann sie tun? Was hilft ihr,
   schnell zu entscheiden?

**Was wir bewerten:**
- **Realismus** — keine "wir taggen alles und gut ist"-Lösung
- **Umgang mit Unsicherheit** — False Positives kosten Beraterzeit, False Negatives
  kosten Kundenstrafen — wie balancieren Sie das?
- **Klare Trennung** zwischen Stammdaten (Kunde, Regulation), Regeln (wer ist
  betroffen?) und Inferenz (welche Aktion folgt?)

### Teil 3 — Kreativ: Add-Ons & Erweiterungen (~1 Stunde)

Stellen Sie sich vor, Teile 1 + 2 sind gebaut und in Produktion. Was fehlt noch,
damit unsere **Berater:innen das System lieben** und unsere **Kunden bereit sind,
mehr dafür zu zahlen**?

**Format:**

1. **Listen Sie 3–5 Add-On-Features** mit jeweils 2–3 Sätzen Beschreibung
2. **Wählen Sie eines aus** und schreiben Sie eine **1-seitige Vertiefung**:
   - Was genau bauen Sie?
   - Warum ist es wertvoll (für Berater:innen ODER Kunden)?
   - Grobe Umsetzungsskizze (Komponenten, Datenfluss, kritische Entscheidungen)
   - Was ist das größte Risiko / der größte Stolperstein?

Es gibt keine "richtige" Antwort. Wir wollen sehen, wie Sie über das Produkt denken.

---

## Was wir bewerten

| Teil | Gewicht | Worauf wir achten |
|---|---|---|
| Teil 1 — Korrektheit | 20 % | Diff korrekt; Umnummerierungs-Falle erkannt |
| Teil 1 — Code-Qualität | 10 % | Lesbar, ≥1 Test, Annahmen dokumentiert |
| Teil 2 — Datenmodell | 20 % | Realistisch, erweiterbar, Trennung Stammdaten/Regeln klar |
| Teil 2 — Matching-Logik | 20 % | Geht auf Unsicherheit ein, konkret pro Beispiel |
| Teil 2 — UI-Skizze | 10 % | Hilft Berater:in wirklich; nicht nur Datendump |
| Teil 3 — Add-On-Liste | 10 % | Mind. 3 sinnvolle Ideen, klare Priorisierung |
| Teil 3 — Vertiefung | 10 % | Konkret, mit Risiko-Bewusstsein |

---

## Wie es danach weitergeht

Wenn die Aufgabe positiv bewertet wird, laden wir Sie zu einem **60–90-minütigen
Live-Walkthrough** ein:
- Sie führen uns durch Code, Design und Add-On-Vorschlag
- Wir hinterfragen einzelne Entscheidungen
- Gemeinsame Live-Erweiterung: wir bringen ein neues Szenario mit; Sie zeigen,
  wie Sie System und/oder UI entsprechend anpassen würden

---

## Abgabe

- **Git-Repository** (GitHub/GitLab Link) oder **ZIP-Datei** per E-Mail
- README im Repo: Wie führe ich Ihr Skript aus?
- Output-Datei `output/changes.json` ins Repo committen
- Design-Deliverables (Datenmodell, Matching-Logik, UI-Skizze, Add-Ons) im
  Hauptverzeichnis sichtbar (z. B. als `DESIGN.md`, `ADDONS.md` oder PDF)

Bei Fragen melden Sie sich gerne — Antwort innerhalb 24 h.

Viel Erfolg!

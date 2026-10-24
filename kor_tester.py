"""Kör testordrarna genom tolkningen och sparar varje resultat som JSON."""

import json
import re
from datetime import datetime
from pathlib import Path

from tolka import tolka_meddelande


REFERENSDATUM = datetime(2026, 10, 27, 7, 45)
PROJEKTMAPP = Path(__file__).resolve().parent
TESTFIL = PROJEKTMAPP / "testordrar.md"
RESULTATKATALOG = PROJEKTMAPP / "testresultat"


def las_tester(text: str) -> list[dict[str, str | int]]:
    """Läser testmeddelanden från Markdown-filen och tar bort testkommentarer."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    rubriker = list(re.finditer(r"^##\s+(\d+)\s+[–-]\s+(.+)$", text, re.MULTILINE))
    tester = []

    for index, rubrik in enumerate(rubriker):
        slut = rubriker[index + 1].start() if index + 1 < len(rubriker) else len(text)
        avsnitt = text[rubrik.end():slut]
        avsnitt = re.sub(r"(?m)^---\s*$", "", avsnitt).strip()

        avsandare_match = re.search(r"^\*\*(?:Från|SMS från):\*\*\s*(.+)$", avsnitt, re.MULTILINE)
        amne_match = re.search(r"^\*\*(?:Ämne|Subject):\*\*\s*(.*)$", avsnitt, re.MULTILINE)
        if not avsandare_match:
            raise ValueError(f"Test {rubrik.group(1)} saknar avsändare.")

        avsandare = avsandare_match.group(1).strip()
        if avsandare.endswith(" (SMS)"):
            avsandare = avsandare.removesuffix(" (SMS)").strip()

        meddelande = avsnitt
        meddelande = re.sub(r"(?m)^\*\*(?:Från|SMS från):\*\*.*$\n?", "", meddelande)
        meddelande = re.sub(r"(?m)^\*\*(?:Ämne|Subject):\*\*.*$\n?", "", meddelande)
        meddelande = meddelande.strip()
        if amne_match:
            amne = amne_match.group(1).strip()
            meddelande = f"Ämne: {amne}\n\n{meddelande}" if amne else meddelande

        tester.append({
            "nummer": int(rubrik.group(1)),
            "namn": rubrik.group(2).strip(),
            "avsandare": avsandare,
            "meddelande": meddelande,
        })

    if len(tester) != 20:
        raise ValueError(f"Förväntade 20 tester i {TESTFIL.name}, hittade {len(tester)}.")
    return tester


def kor() -> None:
    tester = las_tester(TESTFIL.read_text(encoding="utf-8"))
    RESULTATKATALOG.mkdir(exist_ok=True)
    sammanfattningsrader = ["Test | Meddelandetyp | Ordrar | Saknade uppgifter"]

    for test in tester:
        resultat = tolka_meddelande(
            meddelande=test["meddelande"],
            avsandare=test["avsandare"],
            mottagen=REFERENSDATUM,
        )
        fil = RESULTATKATALOG / f"{test['nummer']:02d}.json"
        fil.write_text(
            json.dumps(resultat, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        antal_saknade = sum(len(order.get("saknas", [])) for order in resultat["ordrar"])
        sammanfattningsrader.append(
            f"{test['nummer']:02d} – {test['namn']} | {resultat['meddelandetyp']} "
            f"| {len(resultat['ordrar'])} | {antal_saknade}"
        )

    sammanfattning = "\n".join(sammanfattningsrader) + "\n"
    (RESULTATKATALOG / "sammanfattning.txt").write_text(sammanfattning, encoding="utf-8")
    print(sammanfattning, end="")
    print(f"\nResultat sparade i {RESULTATKATALOG}")


if __name__ == "__main__":
    kor()

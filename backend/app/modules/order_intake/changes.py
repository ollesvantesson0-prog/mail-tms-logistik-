"""
Ändringar och avbokningar: hitta ordern ett meddelande gäller och slå ihop ändringen.

En tolkad ändring innehåller bara de fält som ändras (resten är tomt), så
sammanslagningen skriver bara över fält som har ett värde i ändringen.
Kunduppgifterna ändras aldrig: en ändring kommer från samma kund.
"""

import re
from typing import Any

PLATSETIKETTER = {
    "foretag": "företag",
    "adress": "adress",
    "postnummer": "postnummer",
    "ort": "ort",
    "datum": "datum",
    "tid_fran": "tid från",
    "tid_till": "tid till",
}
GODSETIKETTER = {
    "antal": "antal",
    "typ": "typ",
    "beskrivning": "beskrivning",
    "vikt_kg": "vikt (kg)",
    "matt": "mått",
}
KRAVETIKETTER = {
    "bakgavellyft": "bakgavellyft",
    "kran": "kran",
    "kyl": "kyl",
    "temperatur": "temperatur",
    "adr": "ADR",
    "un_nummer": "UN-nummer",
    "barhjalp": "bärhjälp",
    "akut": "akut",
    "aterkommande": "återkommande",
}


def normalisera_referens(referens: str) -> str:
    """'bb 2291', 'BB-2291' och '#BB2291' ska räknas som samma referens."""
    return re.sub(r"[\s\-#.]", "", referens or "").upper()


def hitta_mal_order(galler_order: str, kandidater: list[tuple[str, str, dict]]) -> str | None:
    """
    Returnerar id för ordern vars kundreferens matchar, annars None.
    `kandidater` är (order_id, status, tolkad order). Vid flera träffar vinner en
    ensam godkänd order; annars räknas det som osäkert och människan får välja.
    """
    sokt = normalisera_referens(galler_order)
    if not sokt:
        return None
    traffar = [
        (order_id, status)
        for order_id, status, order in kandidater
        if normalisera_referens(order.get("kundreferens", "")) == sokt
    ]
    godkanda = [order_id for order_id, status in traffar if status == "approved"]
    if len(traffar) == 1:
        return traffar[0][0]
    return godkanda[0] if len(godkanda) == 1 else None


def har_varde(varde: Any) -> bool:
    return varde not in (None, "", False)


def sla_ihop_falt(gammal: dict, andring: dict) -> dict:
    return {**gammal, **{falt: varde for falt, varde in andring.items() if har_varde(varde)}}


def sla_ihop_lista(gammal: list[dict], andring: list[dict]) -> list[dict]:
    """Slår ihop rad för rad. Extra rader i ändringen läggs till."""
    resultat = [dict(rad) for rad in gammal]
    for index, rad in enumerate(andring):
        if index < len(resultat):
            resultat[index] = sla_ihop_falt(resultat[index], rad)
        elif any(har_varde(varde) for varde in rad.values()):
            resultat.append(dict(rad))
    return resultat


def sla_ihop(mal: dict, andring: dict) -> dict:
    """Ny version av målordern med ändringens ifyllda fält inlagda."""
    return {
        **mal,
        "kundreferens": andring.get("kundreferens") or mal.get("kundreferens", ""),
        "upphamtning": sla_ihop_falt(mal.get("upphamtning", {}), andring.get("upphamtning", {})),
        "leveranser": sla_ihop_lista(mal.get("leveranser", []), andring.get("leveranser", [])),
        "gods": sla_ihop_lista(mal.get("gods", []), andring.get("gods", [])),
        "krav": sla_ihop_falt(mal.get("krav", {}), andring.get("krav", {})),
    }


def visa(varde: Any) -> str:
    if varde is True:
        return "ja"
    if varde in (None, "", False):
        return "–"
    return str(varde)


def jamfor_falt(fore: dict, efter: dict, etiketter: dict, prefix: str) -> list[dict]:
    return [
        {"falt": f"{prefix} {etikett}", "fore": visa(fore.get(falt)), "efter": visa(efter.get(falt))}
        for falt, etikett in etiketter.items()
        if visa(fore.get(falt)) != visa(efter.get(falt))
    ]


def jamfor_lista(fore: list[dict], efter: list[dict], etiketter: dict, namn: str) -> list[dict]:
    rader = []
    for index in range(max(len(fore), len(efter))):
        gammal = fore[index] if index < len(fore) else {}
        ny = efter[index] if index < len(efter) else {}
        rader += jamfor_falt(gammal, ny, etiketter, f"{namn} {index + 1}:")
    return rader


def forandringar(mal: dict, andring: dict) -> list[dict]:
    """Lista med {falt, fore, efter} som visar vad ändringen gör med målordern."""
    efter = sla_ihop(mal, andring)
    rader = []
    if visa(mal.get("kundreferens")) != visa(efter["kundreferens"]):
        rader.append({
            "falt": "Kundreferens",
            "fore": visa(mal.get("kundreferens")),
            "efter": visa(efter["kundreferens"]),
        })
    rader += jamfor_falt(mal.get("upphamtning", {}), efter["upphamtning"], PLATSETIKETTER, "Upphämtning")
    rader += jamfor_lista(mal.get("leveranser", []), efter["leveranser"], PLATSETIKETTER, "Leverans")
    rader += jamfor_lista(mal.get("gods", []), efter["gods"], GODSETIKETTER, "Gods")
    rader += jamfor_falt(mal.get("krav", {}), efter["krav"], KRAVETIKETTER, "Krav")
    return rader

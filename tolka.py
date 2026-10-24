"""Bakåtkompatibel import för skript som fortfarande använder tolka.py."""

from backend.app.modules.order_intake.interpreter import (
    ORDER_SCHEMA,
    SYSTEMPROMPT,
    VECKODAGAR,
    kalender,
    tolka_meddelande,
)

__all__ = [
    "ORDER_SCHEMA",
    "SYSTEMPROMPT",
    "VECKODAGAR",
    "kalender",
    "tolka_meddelande",
]


if __name__ == "__main__":
    from datetime import datetime
    import json

    exempel = """Ämne: Transport torsdag

Hej!
Vi behöver hjälp med en transport på torsdag.
Hämtning: Bergqvists Bygg AB, Industrivägen 14, 433 61 Sävedalen, mellan 07–09.
Leverans: Byggarbetsplats Kvarnbacken, Kvarnbacksgatan 3, 431 37 Mölndal, före 12:00.
4 EUR-pallar gipsskivor, ca 3 200 kg totalt.
Mottagaren har ingen truck så bakgavellyft behövs.
Vår ref: BB-2291

Mvh
Linda Ek
Bergqvists Bygg AB
070-123 45 67"""

    resultat = tolka_meddelande(
        meddelande=exempel,
        avsandare="linda.ek@bergqvistsbygg.se",
        mottagen=datetime(2026, 10, 27, 7, 45),
    )
    print(json.dumps(resultat, indent=2, ensure_ascii=False))

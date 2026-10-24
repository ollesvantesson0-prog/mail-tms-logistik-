"""
Tolkar ett ostrukturerat ordermeddelande (mejl/SMS) till en strukturerad order.

Kör från terminalen för att testa:
uv run python -m backend.app.modules.order_intake.interpreter
"""

import json
from datetime import datetime, timedelta

import anthropic
from dotenv import load_dotenv

# Läser in ANTHROPIC_API_KEY från .env-filen
load_dotenv()

MODELL = "claude-opus-5-5"

VECKODAGAR = ["måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag", "söndag"]


# ---------------------------------------------------------------------------
# JSON-schemat som Claude måste följa.
# Med "structured outputs" garanterar API:et att svaret alltid matchar schemat.
# Alla fält är obligatoriska; saknad info anges som tom sträng "" eller null.
# ---------------------------------------------------------------------------

def text():
    return {"type": "string"}


def objekt(falt):
    """Hjälpfunktion: ett JSON-objekt där alla fält är obligatoriska."""
    return {
        "type": "object",
        "properties": falt,
        "required": list(falt.keys()),
        "additionalProperties": False,
    }


def plats():
    return objekt({
        "foretag": text(),
        "adress": text(),
        "postnummer": text(),
        "ort": text(),
        "datum": {"type": "string", "description": "YYYY-MM-DD eller tom"},
        "tid_fran": {"type": "string", "description": "HH:MM eller tom"},
        "tid_till": {"type": "string", "description": "HH:MM eller tom"},
    })


ORDER_SCHEMA = objekt({
    "meddelandetyp": {
        "type": "string",
        "enum": ["ny_order", "andring", "avbokning", "prisforfragan", "ej_order"],
    },
    "ordrar": {
        "type": "array",
        "items": objekt({
            "kund": objekt({
                "foretag": text(),
                "kontaktperson": text(),
                "telefon": text(),
                "epost": text(),
            }),
            "kundreferens": text(),
            "upphamtning": plats(),
            "leveranser": {"type": "array", "items": plats()},
            "gods": {
                "type": "array",
                "items": objekt({
                    "antal": {"type": ["integer", "null"]},
                    "typ": {
                        "type": "string",
                        "enum": ["EUR-pall", "kolli", "fat", "bur", "lastmeter", "annat"],
                    },
                    "beskrivning": text(),
                    "vikt_kg": {"type": ["number", "null"]},
                    "matt": text(),
                }),
            },
            "krav": objekt({
                "bakgavellyft": {"type": "boolean"},
                "kran": {"type": "boolean"},
                "kyl": {"type": "boolean"},
                "temperatur": text(),
                "adr": {"type": "boolean"},
                "un_nummer": text(),
                "barhjalp": {"type": "boolean"},
                "akut": {"type": "boolean"},
                "aterkommande": {"type": "boolean"},
            }),
            "galler_order": {
                "type": "string",
                "description": "Ordernummer/referens som en ändring eller avbokning gäller",
            },
            "saknas": {"type": "array", "items": text()},
            "osakerheter": {"type": "array", "items": text()},
        }),
    },
    "sammanfattning": text(),
})


SYSTEMPROMPT = """Du är en assistent åt en transportledare på ett svenskt åkeri.
Du får ett inkommande meddelande (mejl eller SMS, på svenska eller engelska) och ska göra om det till strukturerade ordrar enligt JSON-schemat.

Regler:
1. GISSA ALDRIG. Fyll bara i det som faktiskt står i meddelandet (eller avsändarens adress/telefon). Allt annat lämnas tomt ("" eller null) och viktig saknad info skrivs i "saknas" (t.ex. "leveransadress", "vikt", "upphämtningstid").
2. Relativa datum ("imorgon", "fredag", "nästa måndag") räknas från meddelandets mottagningstid. Använd kalendern du får. Om ett datum redan har passerat eller är tvetydigt: skriv det i "osakerheter".
3. Motsägelser (t.ex. olika veckodagar eller datum i ämnesraden och meddelandetexten) ska alltid uttryckligen skrivas i "osakerheter", med båda värdena angivna. Ta även upp uppgiften i "saknas" om mottagaren behöver bekräfta den. Välj inte tyst den ena.
4. Meddelandetyp:
   - ny_order: en beställning av transport
   - andring: ändrar en befintlig order (fyll i "galler_order" och bara de fält som ändras; nämn i "saknas" bara sådant som behövs för ändringen)
   - avbokning: avbokar en befintlig order (fyll i "galler_order")
   - prisforfragan: vill ha pris/offert, inte boka
   - ej_order: allt annat (fakturafrågor, allmänna frågor). Då är "ordrar" en tom lista.
   - Om avsändaren beskriver ett planerat transportbehov och frågar om ni kan utföra det, skapa ett utkast med ny_order även om detaljer saknas och lista nödvändig information i "saknas". Om frågan uttryckligen gäller pris/offert ska den fortfarande klassas som prisforfragan. Använd ej_order för allmänna frågor utan ett konkret transportbehov.
   En prisförfrågan med konkreta transportuppgifter får gärna ha en order med uppgifterna ifyllda.
5. Ett meddelande kan innehålla flera ordrar, t.ex. olika dagar eller olika upphämtningar. En upphämtning med flera stopp är EN order med flera leveranser.
6. Kunden är den som beställer (oftast avsändaren), inte mottagaren av godset.
7. Krav-flaggor sätts till true bara om meddelandet säger det. "akut" = brådskande/så fort som möjligt. "aterkommande" = fast/återkommande körning.
8. Tider skrivs HH:MM. "Före 12" betyder tid_till 12:00; "från 05:30" betyder tid_fran 05:30.
9. "sammanfattning" är EN mening på svenska.
"""


def kalender(mottagen: datetime) -> str:
    """Skapar en liten kalender för de kommande 14 dagarna, så att Claude inte behöver räkna själv."""
    rader = []
    for i in range(14):
        dag = mottagen + timedelta(days=i)
        rader.append(f"{VECKODAGAR[dag.weekday()]} {dag:%Y-%m-%d}")
    return "\n".join(rader)


def tolka_meddelande(meddelande: str, avsandare: str, mottagen: datetime) -> dict:
    """Skickar ett meddelande till Claude och returnerar den tolkade ordern som en dict."""
    client = anthropic.Anthropic()

    anvandartext = f"""Mottagningstid: {VECKODAGAR[mottagen.weekday()]} {mottagen:%Y-%m-%d %H:%M}
Avsändare: {avsandare}

Kalender (idag och framåt):
{kalender(mottagen)}

<meddelande>
{meddelande}
</meddelande>"""

    svar = client.beta.messages.create(
        model=MODELL,
        max_tokens=16000,
        system=SYSTEMPROMPT,
        messages=[{"role": "user", "content": anvandartext}],
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": ORDER_SCHEMA},
        },
        # Om modellens säkerhetsfilter skulle neka anropet provas en annan modell automatiskt.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )

    if svar.stop_reason == "refusal":
        raise RuntimeError("Claude vägrade tolka meddelandet.")
    if svar.stop_reason == "max_tokens":
        raise RuntimeError("Svaret blev för långt och klipptes av.")

    # Svaret är garanterat giltig JSON enligt schemat
    json_text = next(block.text for block in svar.content if block.type == "text")
    return json.loads(json_text)


if __name__ == "__main__":
    # Testa med order 1 från testordrar.md
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

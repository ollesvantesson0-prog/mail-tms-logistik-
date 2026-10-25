"""
AI-förslag på dagsplanering: vilken bil och förare som tar vilket jobb.

Förslaget sparas inte. Transportledaren väljer vilka delar som ska genomföras.
"""

import json
from datetime import date

import anthropic
from dotenv import load_dotenv

from backend.app.modules.order_intake.interpreter import MODELL, VECKODAGAR

load_dotenv()

SYSTEMPROMPT = """Du är planeringsassistent åt en transportledare på ett svenskt åkeri.
Du får dagens fordon, förare, redan planerade jobb och jobb som ska planeras. Föreslå vilket fordon och vilken förare som ska ta varje oplanerat jobb.

Hårda krav (bryt aldrig mot dessa; kan ett jobb inte planeras, lägg det i "ej_planerbara" med anledning):
- Kyl, bakgavellyft och kran: jobbet kräver det → fordonet måste ha det.
- ADR (farligt gods): både fordonet och föraren måste vara godkända.
- Ett jobbs vikt och pallar får inte överstiga fordonets kapacitet. Okänd kapacitet (null) är ok men nämn det.
- En förare kan bara köra ett fordon per dag. Har ett fordon redan en förare den dagen, använd samma förare.
- Bara fordon och förare som finns i listorna.

Gör sedan en så bra plan som möjligt:
- Samla jobb som ligger nära varandra geografiskt och vars tidsfönster går att köra efter varandra på samma bil.
- Undvik jobb på samma bil med tidsfönster som krockar, med hänsyn till ungefärlig körtid mellan orterna.
- Fördela hellre på färre bilar om det går, men inte så att tider riskerar att missas.
- Föreslå en förare för varje fordon som får jobb om det finns lediga förare; annars lämna driver_id tomt.

"motivering" är en kort mening på svenska per jobb. Var ärlig om osäkerheter, t.ex. okänd vikt eller tight tid.
"sammanfattning" är 1–3 meningar om planen som helhet.
"""


def plats_text(plats: dict) -> str:
    delar = [plats.get("foretag", ""), plats.get("adress", ""), plats.get("ort", "")]
    tid = "–".join(t for t in (plats.get("tid_fran", ""), plats.get("tid_till", "")) if t)
    text = ", ".join(d for d in delar if d) or "okänd plats"
    return f"{text} ({plats.get('datum') or 'inget datum'}{' ' + tid if tid else ''})"


def jobb_underlag(order_id: str, order: dict) -> dict:
    return {
        "id": order_id,
        "kund": order.get("kund", {}).get("foretag", ""),
        "upphamtning": plats_text(order.get("upphamtning", {})),
        "leveranser": [plats_text(plats) for plats in order.get("leveranser", [])],
        "gods": [
            {k: rad.get(k) for k in ("antal", "typ", "beskrivning", "vikt_kg")}
            for rad in order.get("gods", [])
        ],
        "krav": {k: v for k, v in order.get("krav", {}).items() if v},
    }


def schema(order_ids: list[str], vehicle_ids: list[str], driver_ids: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "forslag": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "enum": order_ids},
                        "vehicle_id": {"type": "string", "enum": vehicle_ids},
                        "driver_id": {"type": "string", "enum": [*driver_ids, ""]},
                        "motivering": {"type": "string"},
                    },
                    "required": ["order_id", "vehicle_id", "driver_id", "motivering"],
                    "additionalProperties": False,
                },
            },
            "ej_planerbara": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "enum": order_ids},
                        "anledning": {"type": "string"},
                    },
                    "required": ["order_id", "anledning"],
                    "additionalProperties": False,
                },
            },
            "sammanfattning": {"type": "string"},
        },
        "required": ["forslag", "ej_planerbara", "sammanfattning"],
        "additionalProperties": False,
    }


def foresla_plan(
    datum: str,
    fordon: list[dict],
    forare: list[dict],
    planerade: list[dict],
    oplanerade: list[tuple[str, dict]],
) -> dict:
    """
    `fordon` och `forare` är dicts med id och egenskaper. `planerade` är redan
    planerade jobb (med vehicle_id/driver_id). `oplanerade` är (order_id, tolkad order).
    """
    client = anthropic.Anthropic()

    veckodag = VECKODAGAR[date.fromisoformat(datum).weekday()]
    underlag = {
        "fordon": fordon,
        "forare": forare,
        "redan_planerade_jobb": planerade,
        "jobb_att_planera": [jobb_underlag(order_id, order) for order_id, order in oplanerade],
    }
    anvandartext = f"""Dag att planera: {veckodag} {datum}

<underlag>
{json.dumps(underlag, ensure_ascii=False, indent=2)}
</underlag>"""

    svar = client.beta.messages.create(
        model=MODELL,
        max_tokens=16000,
        system=SYSTEMPROMPT,
        messages=[{"role": "user", "content": anvandartext}],
        output_config={
            # Planering kräver eftertanke (geografi, tider, kapacitet).
            "effort": "high",
            "format": {
                "type": "json_schema",
                "schema": schema(
                    [order_id for order_id, _ in oplanerade],
                    [bil["id"] for bil in fordon],
                    [person["id"] for person in forare],
                ),
            },
        },
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )

    if svar.stop_reason == "refusal":
        raise RuntimeError("Claude vägrade planera.")
    if svar.stop_reason == "max_tokens":
        raise RuntimeError("Svaret blev för långt och klipptes av.")

    json_text = next(block.text for block in svar.content if block.type == "text")
    return json.loads(json_text)

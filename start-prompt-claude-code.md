# Startprompt till Claude Code – Orderintag v1

Lägg `testordrar.md` i en tom projektmapp, öppna terminalen där, starta `claude` och klistra in allt under strecket.

---

Jag bygger en MVP av en AI-assistent för transportledare på åkerier. Version 1 ska BARA göra en sak: ta en ostrukturerad orderförfrågan (mejl eller SMS, på svenska eller engelska) och göra om den till en strukturerad order som en människa sedan godkänner eller rättar.

Jag är nybörjare på kod. Förklara kort vad du gör i varje steg och håll koden enkel och läsbar hellre än smart.

## Teknik
- Python
- Anthropic API (Claude) för tolkningen. API-nyckeln ligger i en `.env`-fil som `ANTHROPIC_API_KEY`. Lägg `.env` i `.gitignore`.
- Streamlit för gränssnittet
- Spara ordrar lokalt i en SQLite-databas (eller en JSON-fil om det är enklare till att börja med)

## Vad AI:n ska returnera (JSON)
Ett meddelande kan innehålla noll, en eller flera ordrar. Returnera:

```
{
  "meddelandetyp": "ny_order" | "andring" | "avbokning" | "prisforfragan" | "ej_order",
  "ordrar": [
    {
      "kund": { "foretag": "", "kontaktperson": "", "telefon": "", "epost": "" },
      "kundreferens": "",
      "upphamtning": { "foretag": "", "adress": "", "postnummer": "", "ort": "", "datum": "YYYY-MM-DD", "tid_fran": "HH:MM", "tid_till": "HH:MM" },
      "leveranser": [
        { "foretag": "", "adress": "", "postnummer": "", "ort": "", "datum": "YYYY-MM-DD", "tid_fran": "HH:MM", "tid_till": "HH:MM" }
      ],
      "gods": [ { "antal": 0, "typ": "EUR-pall | kolli | fat | bur | lastmeter | annat", "beskrivning": "", "vikt_kg": 0, "matt": "" } ],
      "krav": { "bakgavellyft": false, "kran": false, "kyl": false, "temperatur": "", "adr": false, "un_nummer": "", "barhjalp": false, "akut": false, "aterkommande": false },
      "galler_order": "",
      "saknas": [ "lista på viktig info som saknas" ],
      "osakerheter": [ "saker som är tvetydiga eller motsägelsefulla" ]
    }
  ],
  "sammanfattning": "en mening på svenska"
}
```

Viktiga regler i prompten till Claude:
- GISSA ALDRIG. Det som inte står i meddelandet ska vara tomt och läggas i `saknas`.
- Relativa datum ("imorgon", "fredag") räknas från meddelandets mottagningstid, som skickas med i anropet.
- Motsägelser (t.ex. "onsdag" i ämnet men "torsdag" i texten) läggs i `osakerheter`.
- Använd Claudes tool use / strukturerad output så att svaret alltid är giltig JSON.

## Gränssnitt (Streamlit)
1. **Inkorg:** en textruta där jag klistrar in ett meddelande plus fält för avsändare och mottagningstid. Knapp: "Tolka".
2. **Granska:** visa den tolkade ordern som redigerbara fält. Det som saknas eller är osäkert ska markeras rött/gult. Knappar: "Godkänn" och "Kasta".
3. **Orderlista:** tabell med godkända ordrar (kund, från, till, datum, gods, status). Knapp för att exportera som CSV.

## Testning
- Läs in `testordrar.md` och gör ett skript `kor_tester.py` som kör alla 20 meddelanden genom tolkningen och sparar resultaten i `testresultat/`. Referensdatum: tisdag 2026-10-27 07:45.
- Skriv ut en kort sammanställning: meddelandetyp per test och antal saknade fält.

## Ordning
Bygg i den här ordningen och stanna efter varje steg så att jag kan testa:
1. Projektstruktur, `.env`, en funktion som tolkar ett meddelande och skriver ut JSON i terminalen
2. `kor_tester.py` mot alla testordrar
3. Streamlit-gränssnittet
4. Spara och lista godkända ordrar plus CSV-export

Bygg INTE: inloggning, TMS-integration, mejlkoppling, röst, prissättning, ruttplanering. Det kommer senare.

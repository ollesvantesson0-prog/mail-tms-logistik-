# AI Trafikledning

Det här projektet byggs steg för steg till en lokal plattform för
trafikledning. Just nu finns en FastAPI-server, en Next.js-yta, PostgreSQL,
grundläggande konton och företagskopplingar.

## Starta lokalt

1. Installera och starta Docker Desktop.
2. Kopiera `.env.example` till `.env`. En Anthropic API-nyckel behövs först när
   AI-tolkningen kopplas in via webbappen.
3. Öppna en terminal i projektmappen och kör:

   ```bash
   docker compose up --build
   ```

- Webbapp: http://localhost:3000
- API-dokumentation: http://localhost:8000/docs
- API-hälsokontroll: http://localhost:8000/api/health
- PostgreSQL: localhost:5432
- Inloggning/registrering: http://localhost:3000/login

Stoppa tjänsterna med `Ctrl+C`. Databasens lokala data sparas i en Docker-volym.
Kör `docker compose down` för att stoppa tjänsterna utan att radera datan.

## Vad delarna gör

- **Next.js (`frontend/`)** visar webbsidorna i webbläsaren.
- **FastAPI (`backend/app/`)** tar emot API-anrop från webbappen.
- **PostgreSQL (`db` i Docker Compose)** lagrar företag, användare,
  medlemskap, ordrar, fordon, förare och inloggningssessioner.
- **Ordertolkningen (`backend/app/modules/order_intake/`)** är den befintliga
  Python-tolkningen, flyttad till en egen modul.

Registrera ett utvecklingskonto på `/login`, så skapas ett företag och en
ägarmedlemskapspost. Inloggning använder en slumpmässig HttpOnly-kaka; dess
hash lagras i databasen och utloggning återkallar sessionen. Företagsåtkomst
kontrolleras genom medlemskap. En användare får 404 om den begär ett företag
den inte tillhör.

Databasschemat skapas/uppdateras automatiskt med Alembic när backend-containern
startar. Kör du backend utan Docker uppdaterar du databasen själv efter en
ny migration:

```bash
uv run alembic -c backend/alembic.ini upgrade head
```

## Orderflödet

1. **Inkorg** (`/inbox`): klistra in ett mejl eller SMS och tryck "Tolka".
2. **Godkänn** (`/approve`): granska och rätta varje tolkad order. Rött betyder
   att viktig information saknas och gult att något är osäkert. Godkänn eller kasta.
   Ändringar och avbokningar kopplas till den befintliga ordern via kundreferensen,
   och du ser vad som ändras (före → efter) innan du genomför det.
   "Skriv svarsutkast" låter AI:n skriva ett svar till kunden med frågor om det
   som saknas, eller en bekräftelse. Du kopierar det eller öppnar det i
   mejlprogrammet. Inget skickas automatiskt.
3. **Ordrar** (`/orders`): se ordrar per status, välj fordon och förare för
   godkända ordrar och exportera dem som CSV.

4. **Planering** (`/plan`): en dag i taget, med en kolumn för oplanerade jobb och en
   per bil. Lägg jobb på bilar och välj förare för dagen, eller tryck "Föreslå plan
   med AI". Fasta regler varnar när ett jobb inte passar en bil (kyl, bakgavellyft,
   kran, ADR, vikt, pallplatser), både för dina egna val och för AI:ns förslag.

5. **Förarna** (`/driver/<länk>`): under Flotta skapar du en personlig länk per
   förare och skickar den med SMS. Föraren ser sina jobb för dagen i mobilen,
   med karta och telefonnummer, och trycker Hämtat, Levererat, Försenad eller
   Avvikelse (med text och foto). Det syns direkt i planeringsvyn. Ingen app och ingen
   inloggning behövs. En ny länk eller "Spärra länk" stänger den gamla.

6. **Uppföljning** (`/followup`): det som behöver uppmärksamhet just nu. Det kan
   vara avvikelser och förseningar från förarna, jobb som borde ha hämtats eller
   levererats enligt tidsfönstren, eller dagens jobb utan bil eller förare. Här
   ser du också dagens siffror och dagens leveranser. "Skriv kundbesked" låter
   AI:n skriva ett leverans-, avvikelse- eller förseningsbesked som du skickar
   själv. "Markera hanterad" tar bort punkten från listan.

**Flotta** (`/fleet`): lägg till, ändra och inaktivera åkeriets fordon och förare,
med egenskaper som maxlast, pallplatser, kyl, bakgavellyft, kran och ADR.

Det här är en **lokal inlärningsversion**, inte redo för riktiga verksamhetsdata.
Självregistrering blockeras i produktionsläge. Innan driftsättning behövs bland
annat ett säkert flöde för att bjuda in användare, hantering av hemligheter,
HTTPS, säkerhetsgranskning och fler tester.

## Kodens mappar

- `backend/app/api/` – API-routes
- `backend/app/core/` – konfiguration och gemensamma regler
- `backend/app/db/` – databasanslutning och migrationer
- `backend/app/models/` – databasmodeller
- `backend/app/modules/` – fristående verksamhetsfunktioner
- `frontend/app/` – webbappens sidor och layout

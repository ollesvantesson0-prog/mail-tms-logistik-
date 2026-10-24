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
startar. De andra webbplatserna är ännu platshållare; det finns inga API:er för
att skapa eller lista verksamhetsordrar, fordon eller förare än.

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

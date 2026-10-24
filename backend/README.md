# Backend

FastAPI-applikationen startas i Docker Compose tillsammans med databasen och
webbappen. API-dokumentationen finns på `/docs`.

Ordertolkningen ligger i `app/modules/order_intake/interpreter.py`. Den går
också att importera från projektroten som `tolka.tolka_meddelande` medan äldre
testskript och Streamlit-appen finns kvar.

## Första databastabellerna

- `companies` är åkerier.
- `users` är personliga konton med lösenordshash, aldrig klartextlösenord.
- `memberships` kopplar användare till företag och innehåller användarens roll.
- `orders`, `vehicles` och `drivers` har alla ett obligatoriskt `company_id`.
- `user_sessions` lagrar hash av den slumpmässiga inloggningsnyckeln så att
  utloggning kan återkalla en session.

Ändringar i databasschemat sparas som Alembic-migrationer under `migrations/`.
Docker kör migrationerna innan API-servern startar.

## Utvecklingsändpunkter

- `POST /api/auth/register` skapar ett företag, ett ägarkonto och loggar in.
- `POST /api/auth/login` loggar in och sätter en HttpOnly-kaka.
- `POST /api/auth/logout` återkallar den aktuella sessionen.
- `GET /api/auth/me` visar kontot och dess företag.
- `GET /api/companies/{company_id}` provar medlemskapskontrollen.

## Ordrar

Alla ligger under `/api/companies/{company_id}/orders` och kräver medlemskap i
företaget.

- `POST /interpret` tolkar ett meddelande med Claude. Varje tolkad order sparas
  med status `pending`. Ett meddelande utan order sparar ingenting.
- `GET ""` listar ordrar, valfritt filtrerat med `?status=pending|approved|discarded`.
- `GET /{order_id}` visar en order.
- `PUT /{order_id}` sparar rättningar av en order som väntar på granskning.
- `POST /{order_id}/approve` och `POST /{order_id}/discard` granskar ordern. Efter
  det är den låst.
- `GET /export.csv` exporterar godkända ordrar.

Tolkningen, originalmeddelandet och meddelandetypen sparas i `orders.details`.

Självregistrering är avsiktligt bara aktiverad i utvecklingsläge. Inloggningen
är en grund för lärande och behöver utökas och granskas innan produktionsbruk.

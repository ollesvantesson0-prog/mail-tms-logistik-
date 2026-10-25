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
- `PUT /{order_id}/assignment` med `{"vehicle_id": ..., "driver_id": ...}` tilldelar
  fordon och förare till en godkänd order. `null` tar bort tilldelningen. Bara aktiva
  fordon och förare i det egna åkeriet kan väljas.
- `GET /export.csv` exporterar godkända ordrar, med fordon och förare.

Tolkningen, originalmeddelandet och meddelandetypen sparas i `orders.details`.

### Ändringar och avbokningar

- Vid tolkningen letas ordern upp vars kundreferens matchar `galler_order`
  ("BB 2291" = "BB-2291"). Finns flera träffar vinner en ensam godkänd order,
  annars väljer människan. Logiken finns i `app/modules/order_intake/changes.py`.
- `PUT /{order_id}/target` med `{"mal_order_id": ...}` väljer målordern för hand.
- `approve` på en ändring skriver ifyllda fält till målordern (kunduppgifterna
  ändras aldrig). En avbokning sätter målordern till `cancelled`. Själva
  ändringsraden får status `applied`, och målordern får en post i `historik`.
- Svaret innehåller `mal_order` och `forandringar` (före/efter per fält).

## Flotta

Under `/api/companies/{company_id}` och med samma medlemskapskontroll:

- `GET /vehicles`, `POST /vehicles`, `PUT /vehicles/{vehicle_id}`. Registreringsnummer
  sparas utan mellanslag och med versaler. Samma nummer två gånger i ett åkeri ger 409.
- `GET /drivers`, `POST /drivers`, `PUT /drivers/{driver_id}`.

Fordon och förare tas inte bort. De inaktiveras med `is_active: false`.

Självregistrering är avsiktligt bara aktiverad i utvecklingsläge. Inloggningen
är en grund för lärande och behöver utökas och granskas innan produktionsbruk.

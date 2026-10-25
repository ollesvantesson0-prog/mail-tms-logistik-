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

### Svarsutkast

- `POST /{order_id}/reply-draft` låter Claude skriva ett svar till kunden
  (`app/modules/order_intake/reply.py`): frågor om det som saknas eller är osäkert,
  annars en bekräftelse, på kundens språk och som SMS om kunden skrev SMS.
  Utkastet sparas i `details.svarsutkast` och skickas aldrig automatiskt.

## Flotta

Under `/api/companies/{company_id}` och med samma medlemskapskontroll:

- `GET /vehicles`, `POST /vehicles`, `PUT /vehicles/{vehicle_id}`. Registreringsnummer
  sparas utan mellanslag och med versaler. Samma nummer två gånger i ett åkeri ger 409.
- `GET /drivers`, `POST /drivers`, `PUT /drivers/{driver_id}`.

Fordon har egenskaperna `max_weight_kg`, `pallet_places`, `has_tail_lift`,
`has_cooling`, `has_crane` och `adr_approved`. Förare har `has_adr_license`.
Fordon och förare tas inte bort. De inaktiveras med `is_active: false`.

## Förare

- `POST /api/companies/{company_id}/drivers/{driver_id}/link` skapar förarens
  personliga länk (`/driver/<nyckel>`). Bara en hash av nyckeln sparas, och en ny
  länk ersätter den gamla. `DELETE` på samma adress spärrar länken.
- `GET /api/driver/{nyckel}?datum=YYYY-MM-DD` visar förarens godkända jobb för dagen.
  Ingen inloggning krävs: nyckeln är förarens behörighet.
- `POST /api/driver/{nyckel}/jobs/{order_id}/events` med `type` `picked_up`,
  `delivered`, `delay` (text krävs) eller `deviation` (text och/eller foto som
  base64, max 3 MB).
  Händelserna sparas i `order_events`, och `orders.execution_status` uppdateras.
- `GET /api/companies/{company_id}/orders/{order_id}/events/{event_id}/photo` visar
  fotot för trafikledaren.

## Uppföljning

- `GET /api/companies/{company_id}/followup?nu=YYYY-MM-DDTHH:MM` (webbläsarens lokala
  tid) listar ohanterade avvikelser och förseningar, jobb vars tidsfönster har
  passerat utan rapport, och dagens jobb utan bil eller förare. Svaret innehåller
  också dagens siffror och dagens levererade jobb. Reglerna är fasta, inte AI.
- `POST /orders/{order_id}/events/{event_id}/handle` markerar en händelse som hanterad.
- `POST /orders/{order_id}/notice-draft` med `{"event_id": ...}` eller
  `{"typ": "delay"}` låter Claude skriva ett kundbesked (`skriv_kundbesked` i
  `app/modules/order_intake/reply.py`). Händelsetiden skickas i svensk tid.

## Planering

- `GET /api/companies/{company_id}/planning?datum=YYYY-MM-DD` ger dagens godkända
  jobb per bil, oplanerade jobb, varningar och förare. Ett jobbs dag är
  upphämtningsdatumet, annars första leveransdatumet.
- `POST /api/companies/{company_id}/planning/suggest` med `{"datum": ...}` låter
  Claude föreslå bil och förare för dagens oplanerade jobb
  (`app/modules/planning/planner.py`). Förslaget sparas inte. Det genomförs via
  `PUT /orders/{id}/assignment`.
- De fasta reglerna i `app/modules/planning/checks.py` kontrollerar kyl,
  bakgavellyft, kran, ADR (fordon och förare), vikt och pallplatser, och de
  används både för planen och för AI:ns förslag.

Självregistrering är avsiktligt bara aktiverad i utvecklingsläge. Inloggningen
är en grund för lärande och behöver utökas och granskas innan produktionsbruk.

"""Streamlit-gränssnitt för att tolka och granska ordermeddelanden."""

from datetime import date, datetime, time

import anthropic
import streamlit as st

from tolka import tolka_meddelande


st.set_page_config(page_title="Orderintag", page_icon="🚚", layout="wide")

PLATSFALT = [
    ("foretag", "Företag"),
    ("adress", "Adress"),
    ("postnummer", "Postnummer"),
    ("ort", "Ort"),
    ("datum", "Datum (ÅÅÅÅ-MM-DD)"),
    ("tid_fran", "Tid från"),
    ("tid_till", "Tid till"),
]


def textfalt(label: str, value: str, key: str) -> str:
    return st.text_input(label, value=value or "", key=key)


def redigera_plats(plats: dict, prefix: str) -> dict:
    redigerad = {}
    kolumner = st.columns(2)
    for index, (falt, etikett) in enumerate(PLATSFALT):
        with kolumner[index % 2]:
            redigerad[falt] = textfalt(etikett, plats.get(falt, ""), f"{prefix}_{falt}")
    return redigerad


def redigera_order(order: dict, index: int, version: int) -> dict:
    prefix = f"v{version}_order{index}"
    redigerad = dict(order)

    st.markdown("**Kund**")
    kund = {}
    kolumner = st.columns(2)
    for position, (falt, etikett) in enumerate([
        ("foretag", "Företag"),
        ("kontaktperson", "Kontaktperson"),
        ("telefon", "Telefon"),
        ("epost", "E-post"),
    ]):
        with kolumner[position % 2]:
            kund[falt] = textfalt(etikett, order["kund"].get(falt, ""), f"{prefix}_kund_{falt}")
    redigerad["kund"] = kund
    redigerad["kundreferens"] = textfalt(
        "Kundreferens", order.get("kundreferens", ""), f"{prefix}_kundreferens"
    )
    redigerad["galler_order"] = textfalt(
        "Gäller order", order.get("galler_order", ""), f"{prefix}_galler_order"
    )

    st.markdown("**Upphämtning**")
    redigerad["upphamtning"] = redigera_plats(order["upphamtning"], f"{prefix}_upphamtning")

    st.markdown("**Leveranser**")
    redigerade_leveranser = []
    for leverans_index, leverans in enumerate(order.get("leveranser", [])):
        with st.expander(f"Leverans {leverans_index + 1}", expanded=True):
            redigerade_leveranser.append(
                redigera_plats(leverans, f"{prefix}_leverans{leverans_index}")
            )
    redigerad["leveranser"] = redigerade_leveranser

    st.markdown("**Gods**")
    redigerat_gods = []
    for gods_index, gods in enumerate(order.get("gods", [])):
        gods_prefix = f"{prefix}_gods{gods_index}"
        with st.expander(f"Gods {gods_index + 1}", expanded=True):
            antal_text = textfalt(
                "Antal", "" if gods.get("antal") is None else str(gods["antal"]),
                f"{gods_prefix}_antal",
            )
            typalternativ = ["EUR-pall", "kolli", "fat", "bur", "lastmeter", "annat"]
            typ = st.selectbox(
                "Typ",
                typalternativ,
                index=typalternativ.index(gods["typ"]),
                key=f"{gods_prefix}_typ",
            )
            beskrivning = textfalt(
                "Beskrivning", gods.get("beskrivning", ""), f"{gods_prefix}_beskrivning"
            )
            vikt_text = textfalt(
                "Vikt (kg)",
                "" if gods.get("vikt_kg") is None else str(gods["vikt_kg"]),
                f"{gods_prefix}_vikt",
            )
            matt = textfalt("Mått", gods.get("matt", ""), f"{gods_prefix}_matt")
            redigerat_gods.append({
                "antal": antal_text,
                "typ": typ,
                "beskrivning": beskrivning,
                "vikt_kg": vikt_text,
                "matt": matt,
            })
    redigerad["gods"] = redigerat_gods

    st.markdown("**Krav**")
    krav = {}
    krav_etiketter = {
        "bakgavellyft": "Bakgavellyft",
        "kran": "Kran",
        "kyl": "Kyl",
        "adr": "ADR",
        "barhjalp": "Bärhjälp",
        "akut": "Akut",
        "aterkommande": "Återkommande",
    }
    kravkolumner = st.columns(3)
    for position, (falt, etikett) in enumerate(krav_etiketter.items()):
        with kravkolumner[position % 3]:
            krav[falt] = st.checkbox(
                etikett, value=order["krav"].get(falt, False), key=f"{prefix}_krav_{falt}"
            )
    krav["temperatur"] = textfalt(
        "Temperatur", order["krav"].get("temperatur", ""), f"{prefix}_krav_temperatur"
    )
    krav["un_nummer"] = textfalt(
        "UN-nummer", order["krav"].get("un_nummer", ""), f"{prefix}_krav_un_nummer"
    )
    redigerad["krav"] = krav

    st.markdown("**Saknas och osäkerheter**")
    redigerad["saknas"] = [
        rad.strip()
        for rad in st.text_area(
            "Saknas (en uppgift per rad)",
            value="\n".join(order.get("saknas", [])),
            key=f"{prefix}_saknas",
        ).splitlines()
        if rad.strip()
    ]
    redigerad["osakerheter"] = [
        rad.strip()
        for rad in st.text_area(
            "Osäkerheter (en uppgift per rad)",
            value="\n".join(order.get("osakerheter", [])),
            key=f"{prefix}_osakerheter",
        ).splitlines()
        if rad.strip()
    ]
    return redigerad


def konvertera_gods(godslista: list[dict]) -> list[dict]:
    konverterad = []
    for index, gods in enumerate(godslista, start=1):
        antal_text = gods["antal"].strip()
        vikt_text = gods["vikt_kg"].strip()
        try:
            antal = int(antal_text) if antal_text else None
        except ValueError as error:
            raise ValueError(f"Gods {index}: antal måste vara ett heltal.") from error
        try:
            vikt = float(vikt_text.replace(",", ".")) if vikt_text else None
        except ValueError as error:
            raise ValueError(f"Gods {index}: vikten måste vara ett tal.") from error
        konverterad.append({
            **gods,
            "antal": antal,
            "vikt_kg": vikt,
        })
    return konverterad


st.title("Orderintag")
st.caption("Klistra in en förfrågan, tolka den och granska utkastet innan det godkänns.")

if "tolkning" not in st.session_state:
    st.session_state.tolkning = None
if "version" not in st.session_state:
    st.session_state.version = 0
if "granskningsstatus" not in st.session_state:
    st.session_state.granskningsstatus = ""

st.header("Inkorg")
with st.form("inkorg"):
    meddelande = st.text_area("Meddelande", height=220)
    avsandare = st.text_input("Avsändare")
    kol1, kol2 = st.columns(2)
    with kol1:
        mottagningsdatum = st.date_input("Mottagningsdatum", value=date.today())
    with kol2:
        mottagningstid = st.time_input("Mottagningstid", value=time(9, 0))
    tolka = st.form_submit_button("Tolka", type="primary")

if tolka:
    if not meddelande.strip():
        st.error("Klistra in ett meddelande innan du tolkar.")
    else:
        try:
            resultat = tolka_meddelande(
                meddelande=meddelande,
                avsandare=avsandare,
                mottagen=datetime.combine(mottagningsdatum, mottagningstid),
            )
        except (anthropic.APIError, RuntimeError) as error:
            st.error(f"Kunde inte tolka meddelandet: {error}")
        else:
            st.session_state.tolkning = resultat
            st.session_state.version += 1
            st.session_state.granskningsstatus = ""

if st.session_state.granskningsstatus == "godkand":
    st.success("Granskningen är godkänd. Sparande till orderlistan kommer i nästa steg.")
elif st.session_state.granskningsstatus == "kastad":
    st.info("Utkastet har kastats.")

resultat = st.session_state.tolkning
if resultat is not None:
    st.header("Granska")
    with st.form(f"granskning_{st.session_state.version}"):
        typer = ["ny_order", "andring", "avbokning", "prisforfragan", "ej_order"]
        meddelandetyp = st.selectbox(
            "Meddelandetyp",
            typer,
            index=typer.index(resultat["meddelandetyp"]),
            key=f"v{st.session_state.version}_meddelandetyp",
        )
        sammanfattning = st.text_input(
            "Sammanfattning",
            value=resultat.get("sammanfattning", ""),
            key=f"v{st.session_state.version}_sammanfattning",
        )
        redigerade_ordrar = []

        if not resultat["ordrar"]:
            st.info("Tolkningen innehåller inga ordrar.")
        for index, order in enumerate(resultat["ordrar"]):
            with st.expander(f"Order {index + 1}", expanded=True):
                if order.get("saknas"):
                    st.error("Saknas: " + "; ".join(order["saknas"]))
                if order.get("osakerheter"):
                    st.warning("Osäkerheter: " + "; ".join(order["osakerheter"]))
                redigerade_ordrar.append(redigera_order(order, index, st.session_state.version))

        godkann = st.form_submit_button("Godkänn", type="primary")
        kasta = st.form_submit_button("Kasta")

    if godkann:
        try:
            for order in redigerade_ordrar:
                order["gods"] = konvertera_gods(order["gods"])
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state.tolkning = {
                "meddelandetyp": meddelandetyp,
                "ordrar": redigerade_ordrar,
                "sammanfattning": sammanfattning,
            }
            st.session_state.granskningsstatus = "godkand"
            st.rerun()
    if kasta:
        st.session_state.tolkning = None
        st.session_state.granskningsstatus = "kastad"
        st.rerun()

"use client";

import { GODSTYPER, tomPlats, tomtGods, type Gods, type Krav, type Plats, type TolkadOrder } from "../lib/api";

const PLATSFALT: [keyof Plats, string][] = [
  ["foretag", "Företag"],
  ["adress", "Adress"],
  ["postnummer", "Postnummer"],
  ["ort", "Ort"],
  ["datum", "Datum"],
  ["tid_fran", "Tid från"],
  ["tid_till", "Tid till"],
];

const KRAVFLAGGOR: [keyof Krav, string][] = [
  ["bakgavellyft", "Bakgavellyft"],
  ["kran", "Kran"],
  ["kyl", "Kyl"],
  ["adr", "ADR"],
  ["barhjalp", "Bärhjälp"],
  ["akut", "Akut"],
  ["aterkommande", "Återkommande"],
];

// Fält som en transportledare behöver för att kunna planera en ny körning.
// Är de tomma markeras de rött.
const VIKTIGA_PLATSFALT: (keyof Plats)[] = ["adress", "ort", "datum"];

type Props = {
  order: TolkadOrder;
  meddelandetyp: string;
  onChange: (order: TolkadOrder) => void;
};

function Falt({
  label,
  value,
  onChange,
  viktig = false,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  viktig?: boolean;
  type?: string;
}) {
  const saknas = viktig && value.trim() === "";
  return (
    <label className={saknas ? "field-missing" : undefined}>
      {label}
      <input onChange={(event) => onChange(event.target.value)} type={type} value={value} />
    </label>
  );
}

function talEllerNull(value: string): number | null {
  const tal = Number(value.replace(",", "."));
  return value.trim() === "" || Number.isNaN(tal) ? null : tal;
}

function PlatsFalt({
  plats,
  onChange,
  viktig,
}: {
  plats: Plats;
  onChange: (plats: Plats) => void;
  viktig: boolean;
}) {
  return (
    <div className="field-grid">
      {PLATSFALT.map(([falt, etikett]) => (
        <Falt
          key={falt}
          label={etikett}
          onChange={(value) => onChange({ ...plats, [falt]: value })}
          type={falt === "datum" ? "date" : falt.startsWith("tid") ? "time" : "text"}
          value={plats[falt]}
          viktig={viktig && VIKTIGA_PLATSFALT.includes(falt)}
        />
      ))}
    </div>
  );
}

function Lista({ label, rader, onChange }: { label: string; rader: string[]; onChange: (rader: string[]) => void }) {
  return (
    <label>
      {label}
      <textarea
        onChange={(event) => onChange(event.target.value.split("\n"))}
        rows={Math.max(2, rader.length)}
        value={rader.join("\n")}
      />
      <span>En uppgift per rad.</span>
    </label>
  );
}

export default function OrderEditor({ order, meddelandetyp, onChange }: Props) {
  // För ändringar och avbokningar är det ordernumret som är viktigt, inte alla adresser.
  const nyKorning = meddelandetyp === "ny_order" || meddelandetyp === "prisforfragan";

  function set<K extends keyof TolkadOrder>(falt: K, value: TolkadOrder[K]) {
    onChange({ ...order, [falt]: value });
  }

  function setLeverans(index: number, plats: Plats) {
    set("leveranser", order.leveranser.map((leverans, i) => (i === index ? plats : leverans)));
  }

  function setGods(index: number, gods: Gods) {
    set("gods", order.gods.map((rad, i) => (i === index ? gods : rad)));
  }

  const saknas = order.saknas.filter((rad) => rad.trim());
  const osakerheter = order.osakerheter.filter((rad) => rad.trim());

  return (
    <div className="auth-form">
      {saknas.length > 0 && (
        <div className="alert alert-missing">
          <strong>Saknas</strong>
          <ul>{saknas.map((rad, i) => <li key={i}>{rad}</li>)}</ul>
        </div>
      )}
      {osakerheter.length > 0 && (
        <div className="alert alert-uncertain">
          <strong>Osäkerheter</strong>
          <ul>{osakerheter.map((rad, i) => <li key={i}>{rad}</li>)}</ul>
        </div>
      )}

      <h3>Kund</h3>
      <div className="field-grid">
        <Falt
          label="Företag"
          onChange={(value) => set("kund", { ...order.kund, foretag: value })}
          value={order.kund.foretag}
          viktig
        />
        <Falt
          label="Kontaktperson"
          onChange={(value) => set("kund", { ...order.kund, kontaktperson: value })}
          value={order.kund.kontaktperson}
        />
        <Falt
          label="Telefon"
          onChange={(value) => set("kund", { ...order.kund, telefon: value })}
          value={order.kund.telefon}
        />
        <Falt
          label="E-post"
          onChange={(value) => set("kund", { ...order.kund, epost: value })}
          value={order.kund.epost}
        />
        <Falt label="Kundreferens" onChange={(value) => set("kundreferens", value)} value={order.kundreferens} />
        <Falt
          label="Gäller order"
          onChange={(value) => set("galler_order", value)}
          value={order.galler_order}
          viktig={!nyKorning}
        />
      </div>

      <h3>Upphämtning</h3>
      <PlatsFalt onChange={(plats) => set("upphamtning", plats)} plats={order.upphamtning} viktig={nyKorning} />

      <h3>Leveranser</h3>
      {order.leveranser.map((leverans, index) => (
        <fieldset className="sub-card" key={index}>
          <legend>Leverans {index + 1}</legend>
          <PlatsFalt onChange={(plats) => setLeverans(index, plats)} plats={leverans} viktig={nyKorning} />
          <button
            className="link-button"
            onClick={() => set("leveranser", order.leveranser.filter((_, i) => i !== index))}
            type="button"
          >
            Ta bort leverans
          </button>
        </fieldset>
      ))}
      <button
        className="secondary-button"
        onClick={() => set("leveranser", [...order.leveranser, tomPlats()])}
        type="button"
      >
        + Lägg till leverans
      </button>

      <h3>Gods</h3>
      {order.gods.map((gods, index) => (
        <fieldset className="sub-card" key={index}>
          <legend>Gods {index + 1}</legend>
          <div className="field-grid">
            <Falt
              label="Antal"
              onChange={(value) => setGods(index, { ...gods, antal: talEllerNull(value) })}
              type="number"
              value={gods.antal === null ? "" : String(gods.antal)}
              viktig={nyKorning}
            />
            <label>
              Typ
              <select
                onChange={(event) => setGods(index, { ...gods, typ: event.target.value as Gods["typ"] })}
                value={gods.typ}
              >
                {GODSTYPER.map((typ) => <option key={typ}>{typ}</option>)}
              </select>
            </label>
            <Falt
              label="Beskrivning"
              onChange={(value) => setGods(index, { ...gods, beskrivning: value })}
              value={gods.beskrivning}
            />
            <Falt
              label="Vikt (kg)"
              onChange={(value) => setGods(index, { ...gods, vikt_kg: talEllerNull(value) })}
              type="number"
              value={gods.vikt_kg === null ? "" : String(gods.vikt_kg)}
            />
            <Falt label="Mått" onChange={(value) => setGods(index, { ...gods, matt: value })} value={gods.matt} />
          </div>
          <button
            className="link-button"
            onClick={() => set("gods", order.gods.filter((_, i) => i !== index))}
            type="button"
          >
            Ta bort gods
          </button>
        </fieldset>
      ))}
      <button className="secondary-button" onClick={() => set("gods", [...order.gods, tomtGods()])} type="button">
        + Lägg till gods
      </button>

      <h3>Krav</h3>
      <div className="checkbox-grid">
        {KRAVFLAGGOR.map(([falt, etikett]) => (
          <label className="checkbox" key={falt}>
            <input
              checked={order.krav[falt] as boolean}
              onChange={(event) => set("krav", { ...order.krav, [falt]: event.target.checked })}
              type="checkbox"
            />
            {etikett}
          </label>
        ))}
      </div>
      <div className="field-grid">
        <Falt
          label="Temperatur"
          onChange={(value) => set("krav", { ...order.krav, temperatur: value })}
          value={order.krav.temperatur}
        />
        <Falt
          label="UN-nummer"
          onChange={(value) => set("krav", { ...order.krav, un_nummer: value })}
          value={order.krav.un_nummer}
          viktig={order.krav.adr}
        />
      </div>

      <h3>Saknas och osäkerheter</h3>
      <Lista label="Saknas" onChange={(rader) => set("saknas", rader)} rader={order.saknas} />
      <Lista label="Osäkerheter" onChange={(rader) => set("osakerheter", rader)} rader={order.osakerheter} />
    </div>
  );
}

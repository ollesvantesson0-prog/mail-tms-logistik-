"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, type Gods, type Krav, type Plats } from "../../lib/api";

type DriverEvent = { id: string; type: string; note: string; created_at: string; has_photo: boolean };

type Job = {
  id: string;
  vehicle: string | null;
  kund: { foretag: string; kontaktperson: string; telefon: string };
  kundreferens: string;
  upphamtning: Plats;
  leveranser: Plats[];
  gods: Gods[];
  krav: Krav;
  execution_status: "picked_up" | "delivered" | null;
  events: DriverEvent[];
};

type Day = { driver: string; company: string; datum: string; jobb: Job[] };

const KRAV: [keyof Krav, string][] = [
  ["kyl", "Kyl"],
  ["bakgavellyft", "Bakgavellyft"],
  ["kran", "Kran"],
  ["adr", "Farligt gods (ADR)"],
  ["barhjalp", "Bärhjälp"],
  ["akut", "Akut"],
];

const HANDELSER: Record<string, string> = { picked_up: "Hämtat", delivered: "Levererat", deviation: "Avvikelse" };

function idag(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}

function flytta(datum: string, dagar: number): string {
  const day = new Date(`${datum}T12:00:00`);
  day.setDate(day.getDate() + dagar);
  return day.toISOString().slice(0, 10);
}

function tid(plats: Plats): string {
  if (plats.tid_fran && plats.tid_till) return `${plats.tid_fran}–${plats.tid_till}`;
  if (plats.tid_fran) return `från ${plats.tid_fran}`;
  if (plats.tid_till) return `senast ${plats.tid_till}`;
  return "";
}

function karta(plats: Plats): string {
  const adress = [plats.adress, plats.postnummer, plats.ort].filter(Boolean).join(", ") || plats.foretag;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(adress)}`;
}

/** Förminskar fotot till max 1280 px och gör det till JPEG, så att det går snabbt att skicka. */
async function forminska(fil: File): Promise<string> {
  const bild = await createImageBitmap(fil);
  const skala = Math.min(1, 1280 / Math.max(bild.width, bild.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bild.width * skala);
  canvas.height = Math.round(bild.height * skala);
  canvas.getContext("2d")!.drawImage(bild, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.75).split(",")[1];
}

function Stopp({ rubrik, plats }: { rubrik: string; plats: Plats }) {
  return (
    <div className="stop">
      <span className="stop-label">{rubrik}</span>
      <strong>{plats.foretag || plats.ort || "Okänd plats"}</strong>
      <span>{[plats.adress, [plats.postnummer, plats.ort].filter(Boolean).join(" ")].filter(Boolean).join(", ")}</span>
      {tid(plats) && <span className="stop-time">{tid(plats)}</span>}
      <a className="driver-link" href={karta(plats)} rel="noreferrer" target="_blank">
        Öppna karta
      </a>
    </div>
  );
}

function JobbKort({ job, onReport }: { job: Job; onReport: (body: object) => Promise<void> }) {
  const [avvikelse, setAvvikelse] = useState(false);
  const [note, setNote] = useState("");
  const [foto, setFoto] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  async function report(body: object) {
    setBusy(true);
    try {
      await onReport(body);
    } finally {
      setBusy(false);
    }
  }

  async function sendAvvikelse() {
    await report({
      type: "deviation",
      note,
      photo_base64: foto ? await forminska(foto) : null,
      photo_type: foto ? "image/jpeg" : null,
    });
    setAvvikelse(false);
    setNote("");
    setFoto(null);
  }

  const krav = KRAV.filter(([key]) => job.krav[key]);
  const status = job.execution_status;

  return (
    <article className={`driver-job ${status ?? ""}`}>
      <header>
        <strong>{job.kund.foretag || "Okänd kund"}</strong>
        <span className="driver-status">
          {status === "delivered" ? "✓ Levererat" : status === "picked_up" ? "Hämtat" : "Ej påbörjat"}
        </span>
      </header>
      {job.kundreferens && <span className="muted">Ref: {job.kundreferens}</span>}

      <Stopp plats={job.upphamtning} rubrik="Hämta" />
      {job.leveranser.map((plats, index) => (
        <Stopp key={index} plats={plats} rubrik={job.leveranser.length > 1 ? `Lämna ${index + 1}` : "Lämna"} />
      ))}

      <div className="driver-goods">
        {job.gods.map((gods, index) => (
          <span key={index}>
            {[gods.antal, gods.typ, gods.beskrivning].filter(Boolean).join(" ")}
            {gods.vikt_kg ? ` · ${gods.vikt_kg} kg` : ""}
          </span>
        ))}
        {krav.length > 0 && <strong>{krav.map(([, label]) => label).join(" · ")}</strong>}
        {job.krav.temperatur && <span>Temperatur: {job.krav.temperatur}</span>}
      </div>

      {job.kund.telefon && (
        <a className="driver-link" href={`tel:${job.kund.telefon.replace(/[\s-]/g, "")}`}>
          Ring {job.kund.kontaktperson || "kunden"} ({job.kund.telefon})
        </a>
      )}

      {job.events.length > 0 && (
        <ul className="driver-events">
          {job.events.map((event) => (
            <li key={event.id}>
              {new Date(event.created_at).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" })}{" "}
              {HANDELSER[event.type] ?? event.type}
              {event.note && `: ${event.note}`}
              {event.has_photo && " (foto)"}
            </li>
          ))}
        </ul>
      )}

      {avvikelse ? (
        <div className="driver-deviation">
          <textarea
            onChange={(event) => setNote(event.target.value)}
            placeholder="Vad har hänt? T.ex. skadad pall, stängt, fel adress"
            rows={3}
            value={note}
          />
          <label className="driver-photo">
            {foto ? `Foto valt: ${foto.name}` : "Ta foto (valfritt)"}
            <input
              accept="image/*"
              capture="environment"
              onChange={(event) => setFoto(event.target.files?.[0] ?? null)}
              type="file"
            />
          </label>
          <div className="driver-buttons">
            <button className="driver-button warn" disabled={busy || (!note.trim() && !foto)} onClick={sendAvvikelse} type="button">
              {busy ? "Skickar…" : "Skicka avvikelse"}
            </button>
            <button className="driver-button ghost" disabled={busy} onClick={() => setAvvikelse(false)} type="button">
              Avbryt
            </button>
          </div>
        </div>
      ) : (
        <div className="driver-buttons">
          {status === null && (
            <button className="driver-button" disabled={busy} onClick={() => report({ type: "picked_up" })} type="button">
              Hämtat
            </button>
          )}
          {status !== "delivered" && (
            <button className="driver-button" disabled={busy} onClick={() => report({ type: "delivered" })} type="button">
              Levererat
            </button>
          )}
          <button className="driver-button ghost" disabled={busy} onClick={() => setAvvikelse(true)} type="button">
            Avvikelse
          </button>
        </div>
      )}
    </article>
  );
}

export default function DriverPage() {
  const { token } = useParams<{ token: string }>();
  const [datum, setDatum] = useState(idag);
  const [day, setDay] = useState<Day | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api<Day>(`/api/driver/${token}?datum=${datum}`)
      .then((result) => {
        setDay(result);
        setError("");
      })
      .catch((fetchError: Error) => setError(fetchError.message));
  }, [token, datum]);

  useEffect(load, [load]);

  async function report(jobId: string, body: object) {
    try {
      const job = await api<Job>(`/api/driver/${token}/jobs/${jobId}/events`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setDay((current) => current && { ...current, jobb: current.jobb.map((row) => (row.id === job.id ? job : row)) });
      setError("");
    } catch (reportError) {
      setError(reportError instanceof Error ? reportError.message : "Kunde inte skicka. Försök igen.");
    }
  }

  const klara = day?.jobb.filter((job) => job.execution_status === "delivered").length ?? 0;

  return (
    <div className="driver-page">
      <header className="driver-header">
        <span className="muted">{day?.company}</span>
        <h1>Hej {day?.driver ?? ""}!</h1>
        <div className="driver-date">
          <button className="driver-button ghost" onClick={() => setDatum(flytta(datum, -1))} type="button">
            ←
          </button>
          <strong>
            {new Date(`${datum}T12:00:00`).toLocaleDateString("sv-SE", { weekday: "long", day: "numeric", month: "long" })}
          </strong>
          <button className="driver-button ghost" onClick={() => setDatum(flytta(datum, 1))} type="button">
            →
          </button>
        </div>
        {day && day.jobb.length > 0 && (
          <span className="muted">
            {klara} av {day.jobb.length} jobb klara
            {day.jobb[0].vehicle && ` · Bil ${day.jobb[0].vehicle}`}
          </span>
        )}
      </header>

      {error && <p className="error-message" role="alert">{error}</p>}
      {day === null && !error && <p className="muted">Hämtar dina jobb…</p>}
      {day?.jobb.length === 0 && <p className="driver-empty">Inga jobb den här dagen.</p>}
      {day?.jobb.map((job) => <JobbKort job={job} key={job.id} onReport={(body) => report(job.id, body)} />)}
    </div>
  );
}

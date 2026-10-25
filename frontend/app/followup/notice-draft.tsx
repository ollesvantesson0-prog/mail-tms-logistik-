"use client";

import { useState } from "react";

import { api, ordersUrl } from "../lib/api";

type Draft = { amne: string; text: string; epost: string; telefon: string };

type Props = {
  companyId: string;
  orderId: string;
  /** {event_id} för en förarhändelse, eller {typ: "delay"} för en upptäckt försening. */
  request: { event_id: string } | { typ: "delay" };
  label: string;
};

/** Knapp som låter AI:n skriva ett kundbesked, och visar utkastet för granskning. Inget skickas. */
export default function NoticeDraft({ companyId, orderId, request, label }: Props) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function generate() {
    setBusy(true);
    setError("");
    try {
      setDraft(
        await api<Draft>(ordersUrl(companyId, `/${orderId}/notice-draft`), {
          method: "POST",
          body: JSON.stringify(request),
        }),
      );
    } catch (draftError) {
      setError(draftError instanceof Error ? draftError.message : "Kunde inte skriva beskedet.");
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    await navigator.clipboard.writeText(draft!.amne ? `${draft!.amne}\n\n${draft!.text}` : draft!.text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  if (!draft) {
    return (
      <>
        <button className="secondary-button" disabled={busy} onClick={generate} type="button">
          {busy ? "Skriver…" : label}
        </button>
        {error && <span className="error-message">{error}</span>}
      </>
    );
  }

  const telefon = draft.telefon.replace(/[\s-]/g, "");
  return (
    <div className="notice-draft auth-form">
      {draft.amne && (
        <label>
          Ämne
          <input onChange={(event) => setDraft({ ...draft, amne: event.target.value })} value={draft.amne} />
        </label>
      )}
      <label>
        Kundbesked
        <textarea onChange={(event) => setDraft({ ...draft, text: event.target.value })} rows={6} value={draft.text} />
        <span>Läs igenom innan du skickar.</span>
      </label>
      <div className="row-actions start">
        <button className="link-button neutral" onClick={copy} type="button">
          {copied ? "Kopierat!" : "Kopiera"}
        </button>
        {draft.epost && (
          <a
            className="link-button neutral"
            href={`mailto:${encodeURIComponent(draft.epost)}?subject=${encodeURIComponent(draft.amne)}&body=${encodeURIComponent(draft.text)}`}
          >
            Öppna i mejlprogrammet
          </a>
        )}
        {telefon && (
          <a className="link-button neutral" href={`sms:${telefon}?body=${encodeURIComponent(draft.text)}`}>
            Skicka SMS
          </a>
        )}
        <button className="link-button" onClick={() => setDraft(null)} type="button">
          Stäng
        </button>
      </div>
    </div>
  );
}

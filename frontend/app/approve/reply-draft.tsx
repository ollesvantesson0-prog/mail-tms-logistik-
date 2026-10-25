"use client";

import { useEffect, useState } from "react";

import { api, ordersUrl, type Order } from "../lib/api";

type Props = {
  companyId: string;
  order: Order;
  /** Sparar formulärets ändringar först, så att utkastet bygger på det du ser. */
  prepare: () => Promise<unknown>;
  onSaved: (order: Order) => void;
  onError: (message: string) => void;
};

/** AI-utkast till svar till kunden. Inget skickas automatiskt. */
export default function ReplyDraft({ companyId, order, prepare, onSaved, onError }: Props) {
  const [amne, setAmne] = useState(order.svarsutkast?.amne ?? "");
  const [text, setText] = useState(order.svarsutkast?.text ?? "");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  // Visa det nya utkastet när AI:n har skrivit ett.
  useEffect(() => {
    setAmne(order.svarsutkast?.amne ?? "");
    setText(order.svarsutkast?.text ?? "");
  }, [order.svarsutkast]);

  async function generate() {
    setBusy(true);
    onError("");
    try {
      await prepare();
      onSaved(await api<Order>(ordersUrl(companyId, `/${order.id}/reply-draft`), { method: "POST" }));
    } catch (draftError) {
      onError(draftError instanceof Error ? draftError.message : "Kunde inte skriva svarsutkastet.");
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    await navigator.clipboard.writeText(amne ? `${amne}\n\n${text}` : text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  const mottagare = order.meddelande.avsandare.trim();
  const arEpost = mottagare.includes("@");
  const arTelefon = /^[+\d][\d\s-]{5,}$/.test(mottagare);
  const mailto = `mailto:${encodeURIComponent(mottagare)}?subject=${encodeURIComponent(amne)}&body=${encodeURIComponent(text)}`;
  const sms = `sms:${mottagare.replace(/[\s-]/g, "")}?body=${encodeURIComponent(text)}`;

  return (
    <section className="reply-draft">
      <h3>Svar till kunden</h3>
      {!order.svarsutkast && !text ? (
        <p className="muted">
          Låt AI:n skriva ett utkast: frågor om det som saknas, eller en bekräftelse om allt är klart.
        </p>
      ) : (
        <div className="auth-form">
          {(amne || arEpost) && (
            <label>
              Ämne
              <input onChange={(event) => setAmne(event.target.value)} value={amne} />
            </label>
          )}
          <label>
            Meddelande
            <textarea onChange={(event) => setText(event.target.value)} rows={10} value={text} />
            <span>Läs igenom och rätta innan du skickar. Ändringar här sparas inte.</span>
          </label>
        </div>
      )}
      <div className="button-row compact">
        <button className="secondary-button" disabled={busy} onClick={generate} type="button">
          {busy ? "Skriver… (några sekunder)" : order.svarsutkast ? "Skriv om utkastet" : "Skriv svarsutkast"}
        </button>
        {text && (
          <>
            <button className="secondary-button" onClick={copy} type="button">
              {copied ? "Kopierat!" : "Kopiera"}
            </button>
            {arEpost && (
              <a className="secondary-button" href={mailto}>
                Öppna i mejlprogrammet
              </a>
            )}
            {arTelefon && (
              <a className="secondary-button" href={sms}>
                Öppna som SMS
              </a>
            )}
          </>
        )}
      </div>
    </section>
  );
}

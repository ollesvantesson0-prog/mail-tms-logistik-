"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { api, MEDDELANDETYPER, ordersUrl, useCompanyId, type Order } from "../lib/api";

type InterpretResult = {
  meddelandetyp: string;
  sammanfattning: string;
  ordrar: Order[];
};

/** Nuvarande lokala tid i formatet som <input type="datetime-local"> vill ha. */
function nu(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

export default function InboxPage() {
  const { companyId, error: companyError } = useCompanyId();
  const [meddelande, setMeddelande] = useState("");
  const [avsandare, setAvsandare] = useState("");
  const [mottagen, setMottagen] = useState(nu);
  const [result, setResult] = useState<InterpretResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const svar = await api<InterpretResult>(ordersUrl(companyId, "/interpret"), {
        method: "POST",
        body: JSON.stringify({ meddelande, avsandare, mottagen }),
      });
      setResult(svar);
      setMeddelande("");
      setAvsandare("");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Kunde inte tolka meddelandet.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <p className="eyebrow">Arbetsyta</p>
      <h1>Inkorg</h1>
      <p className="description">
        Klistra in ett mejl eller SMS. AI:n gör om det till orderutkast som du sedan
        granskar under Godkänn.
      </p>
      <section className="placeholder">
        <form className="auth-form" onSubmit={submit}>
          <label>
            Meddelande
            <textarea
              maxLength={20000}
              onChange={(event) => setMeddelande(event.target.value)}
              required
              rows={12}
              value={meddelande}
            />
          </label>
          <div className="field-row">
            <label>
              Avsändare
              <input
                onChange={(event) => setAvsandare(event.target.value)}
                placeholder="namn@foretag.se eller telefonnummer"
                value={avsandare}
              />
            </label>
            <label>
              Mottagen
              <input
                onChange={(event) => setMottagen(event.target.value)}
                required
                type="datetime-local"
                value={mottagen}
              />
              <span>Relativa datum som "imorgon" räknas från den här tiden.</span>
            </label>
          </div>
          <button className="primary-button" disabled={busy || !companyId} type="submit">
            {busy ? "Tolkar… (kan ta en halv minut)" : "Tolka"}
          </button>
        </form>
        {(error || companyError) && (
          <p className="error-message" role="alert">{error || companyError}</p>
        )}
      </section>

      {result && (
        <section className="placeholder" role="status">
          <p className="eyebrow">{MEDDELANDETYPER[result.meddelandetyp] ?? result.meddelandetyp}</p>
          <p>{result.sammanfattning}</p>
          {result.ordrar.length === 0 ? (
            <p className="muted">Meddelandet innehöll ingen order, så inget sparades.</p>
          ) : (
            <Link className="primary-button" href="/approve">
              Granska {result.ordrar.length === 1 ? "ordern" : `${result.ordrar.length} ordrar`}
            </Link>
          )}
        </section>
      )}
    </>
  );
}

"use client";

import { useState } from "react";

import { api } from "../lib/api";

type Props = {
  companyId: string;
  driver: { id: string; name: string; phone: string; has_link: boolean };
};

/** Skapar förarens personliga länk och hjälper trafikledaren att skicka den. */
export default function DriverLink({ companyId, driver }: Props) {
  const [url, setUrl] = useState("");
  const [hasLink, setHasLink] = useState(driver.has_link);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const base = `/api/companies/${companyId}/drivers/${driver.id}/link`;

  async function create() {
    if (hasLink && !window.confirm(`${driver.name}s gamla länk slutar fungera. Skapa en ny?`)) return;
    setError("");
    try {
      const { path } = await api<{ path: string }>(base, { method: "POST" });
      setUrl(`${window.location.origin}${path}`);
      setHasLink(true);
    } catch (linkError) {
      setError(linkError instanceof Error ? linkError.message : "Kunde inte skapa länken.");
    }
  }

  async function revoke() {
    if (!window.confirm(`Spärra ${driver.name}s länk?`)) return;
    await api(base, { method: "DELETE" });
    setUrl("");
    setHasLink(false);
  }

  async function copy() {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  const smsText = `Hej ${driver.name}! Här är din länk till dagens körningar: ${url}`;

  return (
    <div className="driver-link-cell">
      <button className="link-button neutral" onClick={create} type="button">
        {hasLink ? "Ny förarlänk" : "Skapa förarlänk"}
      </button>
      {hasLink && !url && (
        <button className="link-button" onClick={revoke} type="button">
          Spärra länk
        </button>
      )}
      {url && (
        <div className="driver-link-box">
          <code>{url}</code>
          <span className="muted">Länken visas bara nu. Skicka den till {driver.name}.</span>
          <div className="row-actions">
            <button className="link-button neutral" onClick={copy} type="button">
              {copied ? "Kopierat!" : "Kopiera"}
            </button>
            {driver.phone && (
              <a className="link-button neutral" href={`sms:${driver.phone.replace(/[\s-]/g, "")}?body=${encodeURIComponent(smsText)}`}>
                Skicka SMS
              </a>
            )}
            <a className="link-button neutral" href={url} rel="noreferrer" target="_blank">
              Öppna
            </a>
          </div>
        </div>
      )}
      {error && <span className="error-message">{error}</span>}
    </div>
  );
}

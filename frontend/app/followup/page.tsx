"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { api, ordersUrl, useCompanyId, type Order } from "../lib/api";
import JobCard from "../plan/job-card";
import NoticeDraft from "./notice-draft";

type Item = {
  typ: string;
  allvarlighet: "hog" | "medel";
  rubrik: string;
  text: string;
  order: Order;
  event_id: string | null;
};

type Followup = {
  items: Item[];
  idag: { jobb: number; ej_paborjade: number; hamtade: number; levererade: number; vantar_granskning: number };
  levererade: Order[];
};

/** Webbläsarens lokala tid, t.ex. 2026-10-29T10:15. */
function nu(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function datumFor(order: Order): string {
  return order.order.upphamtning.datum || order.order.leveranser.find((plats) => plats.datum)?.datum || "";
}

export default function FollowupPage() {
  const { companyId, error: companyError } = useCompanyId();
  const [data, setData] = useState<Followup | null>(null);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState("");

  const load = useCallback(() => {
    if (!companyId) return;
    api<Followup>(`/api/companies/${companyId}/followup?nu=${nu()}`)
      .then((result) => {
        setData(result);
        setUpdated(new Date().toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" }));
      })
      .catch((fetchError: Error) => setError(fetchError.message));
  }, [companyId]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function handle(item: Item) {
    try {
      await api(ordersUrl(companyId, `/${item.order.id}/events/${item.event_id}/handle`), { method: "POST" });
      load();
    } catch (handleError) {
      setError(handleError instanceof Error ? handleError.message : "Kunde inte markera som hanterad.");
    }
  }

  const idag = data?.idag;

  return (
    <>
      <p className="eyebrow">Arbetsyta</p>
      <h1>Uppföljning</h1>
      <p className="description">
        Det som behöver din uppmärksamhet just nu: avvikelser och förseningar från förarna,
        jobb som borde ha hämtats eller levererats, och dagens jobb utan bil eller förare.
      </p>
      {(error || companyError) && <p className="error-message" role="alert">{error || companyError}</p>}

      {idag && (
        <div className="stat-row">
          <div className="stat"><strong>{idag.jobb}</strong><span>jobb idag</span></div>
          <div className="stat"><strong>{idag.ej_paborjade}</strong><span>ej påbörjade</span></div>
          <div className="stat"><strong>{idag.hamtade}</strong><span>hämtade</span></div>
          <div className="stat"><strong>{idag.levererade}</strong><span>levererade</span></div>
          <Link className="stat" href="/approve">
            <strong>{idag.vantar_granskning}</strong>
            <span>väntar på granskning</span>
          </Link>
        </div>
      )}
      {updated && <p className="muted">Uppdateras automatiskt · senast {updated}</p>}

      {data === null && !error && <p className="muted">Hämtar…</p>}
      {data && data.items.length === 0 && (
        <section className="placeholder">
          <strong>Allt lugnt.</strong>
          <p className="muted">Inga avvikelser, förseningar eller oplanerade jobb just nu.</p>
        </section>
      )}

      <div className="followup-list">
        {data?.items.map((item) => (
          <section className={`followup-item ${item.allvarlighet}`} key={`${item.typ}-${item.order.id}-${item.event_id ?? ""}`}>
            <header>
              <strong>{item.rubrik}</strong>
              <span>{item.text}</span>
            </header>
            <JobCard companyId={companyId} order={item.order} />
            <div className="row-actions start">
              {item.event_id && (
                <NoticeDraft
                  companyId={companyId}
                  label="Skriv kundbesked"
                  orderId={item.order.id}
                  request={{ event_id: item.event_id }}
                />
              )}
              {(item.typ === "sen_upphamtning" || item.typ === "sen_leverans") && (
                <NoticeDraft
                  companyId={companyId}
                  label="Skriv förseningsbesked"
                  orderId={item.order.id}
                  request={{ typ: "delay" }}
                />
              )}
              {item.event_id && (
                <button className="secondary-button" onClick={() => handle(item)} type="button">
                  Markera hanterad
                </button>
              )}
              <Link className="secondary-button" href={`/plan?datum=${datumFor(item.order)}`}>
                Öppna planering
              </Link>
            </div>
          </section>
        ))}
      </div>

      {data && data.levererade.length > 0 && (
        <>
          <h2 className="section-title">Levererat idag</h2>
          <div className="followup-list">
            {data.levererade.map((order) => {
              const leverans = [...order.events].reverse().find((event) => event.type === "delivered");
              return (
                <section className="followup-item done" key={order.id}>
                  <JobCard companyId={companyId} order={order} />
                  {leverans && (
                    <div className="row-actions start">
                      <NoticeDraft
                        companyId={companyId}
                        label="Skriv leveransbesked"
                        orderId={order.id}
                        request={{ event_id: leverans.id }}
                      />
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        </>
      )}
    </>
  );
}

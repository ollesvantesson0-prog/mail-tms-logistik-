"use client";

import type { ReactNode } from "react";

import { ordersUrl, type Order } from "../lib/api";

const KRAV: Record<string, string> = {
  kyl: "Kyl",
  bakgavellyft: "Bakgavellyft",
  kran: "Kran",
  adr: "ADR",
  barhjalp: "Bärhjälp",
  akut: "Akut",
};

function tid(plats: { tid_fran: string; tid_till: string }): string {
  if (plats.tid_fran && plats.tid_till) return `${plats.tid_fran}–${plats.tid_till}`;
  if (plats.tid_fran) return `från ${plats.tid_fran}`;
  if (plats.tid_till) return `före ${plats.tid_till}`;
  return "";
}

type Props = {
  order: Order;
  /** Behövs för att kunna visa förarens foton. */
  companyId?: string;
  varningar?: string[];
  children?: ReactNode;
};

/** Ett jobb i planeringsvyn: kund, sträcka, tider, gods, krav och varningar. */
export default function JobCard({ order: row, companyId, varningar = [], children }: Props) {
  const order = row.order;
  const upp = order.upphamtning;
  const vikt = order.gods.reduce((sum, gods) => sum + (gods.vikt_kg ?? 0), 0);
  const krav = Object.entries(KRAV).filter(([key]) => order.krav[key as keyof typeof order.krav]);
  const avvikelser = row.events.filter((event) => event.type === "deviation");
  const klockslag = (iso: string) => new Date(iso).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" });
  const senaste = [...row.events].reverse().find((event) => event.type === row.execution_status);

  return (
    <article className={`job-card ${row.execution_status ?? ""}`}>
      <div className="job-title">
        <strong>{order.kund.foretag || "Okänd kund"}</strong>
        {row.execution_status && (
          <span className={`status-pill ${row.execution_status}`}>
            {row.execution_status === "delivered" ? "Levererad" : "Hämtad"}
            {senaste && ` ${klockslag(senaste.created_at)}`}
          </span>
        )}
      </div>
      <div className="job-route">
        <span>
          {upp.ort || upp.foretag || "?"} {tid(upp) && <span className="muted">({tid(upp)})</span>}
        </span>
        {order.leveranser.map((leverans, index) => (
          <span key={index}>
            → {leverans.ort || leverans.foretag || "?"}{" "}
            {tid(leverans) && <span className="muted">({tid(leverans)})</span>}
          </span>
        ))}
      </div>
      <span className="muted">
        {order.gods.map((gods) => [gods.antal, gods.typ].filter(Boolean).join(" ")).join(", ") || "Okänt gods"}
        {vikt > 0 && ` · ${vikt.toLocaleString("sv-SE")} kg`}
      </span>
      {krav.length > 0 && (
        <div className="job-badges">
          {krav.map(([key, label]) => <span className="badge" key={key}>{label}</span>)}
        </div>
      )}
      {avvikelser.length > 0 && (
        <ul className="job-deviations">
          {avvikelser.map((event) => (
            <li key={event.id}>
              <strong>Avvikelse {klockslag(event.created_at)}</strong>
              {event.driver_name && ` (${event.driver_name})`}
              {event.note && `: ${event.note}`}
              {event.has_photo && companyId && (
                <>
                  {" "}
                  <a href={ordersUrl(companyId, `/${row.id}/events/${event.id}/photo`)} rel="noreferrer" target="_blank">
                    Visa foto
                  </a>
                </>
              )}
            </li>
          ))}
        </ul>
      )}
      {varningar.length > 0 && (
        <ul className="job-warnings">{varningar.map((varning) => <li key={varning}>{varning}</li>)}</ul>
      )}
      {children}
    </article>
  );
}

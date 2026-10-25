"use client";

import type { ReactNode } from "react";

import type { Order } from "../lib/api";

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
  varningar?: string[];
  children?: ReactNode;
};

/** Ett jobb i planeringsvyn: kund, sträcka, tider, gods, krav och varningar. */
export default function JobCard({ order: row, varningar = [], children }: Props) {
  const order = row.order;
  const upp = order.upphamtning;
  const vikt = order.gods.reduce((sum, gods) => sum + (gods.vikt_kg ?? 0), 0);
  const krav = Object.entries(KRAV).filter(([key]) => order.krav[key as keyof typeof order.krav]);

  return (
    <article className="job-card">
      <strong>{order.kund.foretag || "Okänd kund"}</strong>
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
      {varningar.length > 0 && (
        <ul className="job-warnings">{varningar.map((varning) => <li key={varning}>{varning}</li>)}</ul>
      )}
      {children}
    </article>
  );
}

"use client";

import { useState } from "react";

import type { Driver, Order, Vehicle } from "../lib/api";

export type Suggestion = {
  order_id: string;
  vehicle_id: string;
  driver_id: string | null;
  motivering: string;
  varningar: string[];
};

export type SuggestResult = {
  forslag: Suggestion[];
  ej_planerbara: { order_id: string; anledning: string }[];
  sammanfattning: string;
};

type Props = {
  result: SuggestResult;
  orders: Order[];
  vehicles: Vehicle[];
  drivers: Driver[];
  busy: boolean;
  onApply: (chosen: Suggestion[]) => void;
  onDismiss: () => void;
};

/** AI:ns planförslag. Transportledaren väljer vilka rader som ska genomföras. */
export default function Suggestions({ result, orders, vehicles, drivers, busy, onApply, onDismiss }: Props) {
  // Förslag med varningar är inte förvalda: de ska granskas aktivt.
  const [chosen, setChosen] = useState(
    () => new Set(result.forslag.filter((rad) => rad.varningar.length === 0).map((rad) => rad.order_id)),
  );

  const orderName = (id: string) => {
    const order = orders.find((row) => row.id === id)?.order;
    if (!order) return "Okänt jobb";
    const till = order.leveranser.map((leverans) => leverans.ort || leverans.foretag).join(", ");
    return `${order.kund.foretag || "Okänd kund"}: ${order.upphamtning.ort || "?"} → ${till || "?"}`;
  };

  function toggle(id: string) {
    setChosen((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <section className="suggestions">
      <h2>AI:ns förslag</h2>
      <p>{result.sammanfattning}</p>
      {result.forslag.length > 0 && (
        <ul className="suggestion-list">
          {result.forslag.map((rad) => (
            <li key={rad.order_id}>
              <label className="checkbox">
                <input checked={chosen.has(rad.order_id)} onChange={() => toggle(rad.order_id)} type="checkbox" />
                <span>
                  <strong>{orderName(rad.order_id)}</strong> →{" "}
                  {vehicles.find((vehicle) => vehicle.id === rad.vehicle_id)?.registration_number}
                  {rad.driver_id && `, ${drivers.find((driver) => driver.id === rad.driver_id)?.name}`}
                  <br />
                  <span className="muted">{rad.motivering}</span>
                  {rad.varningar.map((varning) => (
                    <span className="suggestion-warning" key={varning}>⚠ {varning}</span>
                  ))}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {result.ej_planerbara.length > 0 && (
        <div className="alert alert-uncertain">
          <strong>Kunde inte planeras</strong>
          <ul>
            {result.ej_planerbara.map((rad) => (
              <li key={rad.order_id}>
                {orderName(rad.order_id)}: {rad.anledning}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="button-row compact">
        {result.forslag.length > 0 && (
          <button
            className="primary-button"
            disabled={busy || chosen.size === 0}
            onClick={() => onApply(result.forslag.filter((rad) => chosen.has(rad.order_id)))}
            type="button"
          >
            Genomför valda ({chosen.size})
          </button>
        )}
        <button className="secondary-button" disabled={busy} onClick={onDismiss} type="button">
          Stäng
        </button>
      </div>
    </section>
  );
}

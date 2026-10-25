"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { api, ordersUrl, useCompanyId, type Driver, type Order, type Vehicle } from "../lib/api";
import JobCard from "./job-card";
import Suggestions, { type Suggestion, type SuggestResult } from "./suggestions";

type VehicleDay = {
  vehicle: Vehicle;
  ordrar: { order: Order; varningar: string[] }[];
  vikt_kg: number;
  pallar: number;
  varningar: string[];
};

type DayPlan = {
  datum: string;
  bilar: VehicleDay[];
  ej_planerade: Order[];
  utan_datum: Order[];
  varningar: string[];
  forare: Driver[];
};

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

function veckodag(datum: string): string {
  return new Date(`${datum}T12:00:00`).toLocaleDateString("sv-SE", { weekday: "long", day: "numeric", month: "long" });
}

function kapacitet(varde: number, max: number | null, enhet: string): string {
  return max === null ? `${varde.toLocaleString("sv-SE")} ${enhet}` : `${varde.toLocaleString("sv-SE")}/${max.toLocaleString("sv-SE")} ${enhet}`;
}

export default function PlanPage() {
  const { companyId, error: companyError } = useCompanyId();
  const [datum, setDatum] = useState(idag);

  // Uppföljningen länkar hit med ?datum=YYYY-MM-DD.
  useEffect(() => {
    const fran = new URLSearchParams(window.location.search).get("datum");
    if (fran && /^\d{4}-\d{2}-\d{2}$/.test(fran)) setDatum(fran);
  }, []);
  const [plan, setPlan] = useState<DayPlan | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [thinking, setThinking] = useState(false);

  const load = useCallback(() => {
    if (!companyId) return;
    api<DayPlan>(`/api/companies/${companyId}/planning?datum=${datum}`)
      .then(setPlan)
      .catch((fetchError: Error) => setError(fetchError.message));
  }, [companyId, datum]);

  useEffect(() => {
    setPlan(null);
    setSuggestions(null);
    load();
    // Hämta om planen regelbundet så att förarnas rapporter syns utan att ladda om sidan.
    const timer = window.setInterval(load, 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  /** Sparar fordon och förare för flera jobb och läser sedan om planen. */
  async function assign(changes: { orderId: string; vehicleId: string | null; driverId: string | null }[]) {
    setBusy(true);
    setError("");
    try {
      for (const change of changes) {
        await api(ordersUrl(companyId, `/${change.orderId}/assignment`), {
          method: "PUT",
          body: JSON.stringify({ vehicle_id: change.vehicleId, driver_id: change.driverId }),
        });
      }
      load();
    } catch (assignError) {
      setError(assignError instanceof Error ? assignError.message : "Kunde inte spara planeringen.");
    } finally {
      setBusy(false);
    }
  }

  async function suggest() {
    setThinking(true);
    setError("");
    try {
      setSuggestions(
        await api<SuggestResult>(`/api/companies/${companyId}/planning/suggest`, {
          method: "POST",
          body: JSON.stringify({ datum }),
        }),
      );
    } catch (suggestError) {
      setError(suggestError instanceof Error ? suggestError.message : "Kunde inte ta fram ett förslag.");
    } finally {
      setThinking(false);
    }
  }

  async function applySuggestions(chosen: Suggestion[]) {
    await assign(chosen.map((rad) => ({ orderId: rad.order_id, vehicleId: rad.vehicle_id, driverId: rad.driver_id })));
    setSuggestions(null);
  }

  function dayDriver(bil: VehicleDay): string {
    return bil.ordrar.find((jobb) => jobb.order.driver_id)?.order.driver_id ?? "";
  }

  const activeVehicles = plan?.bilar.filter((bil) => bil.vehicle.is_active) ?? [];
  const activeDrivers = plan?.forare.filter((driver) => driver.is_active) ?? [];
  const allOrders = plan ? [...plan.ej_planerade, ...plan.bilar.flatMap((bil) => bil.ordrar.map((jobb) => jobb.order))] : [];

  return (
    <>
      <p className="eyebrow">Arbetsyta</p>
      <h1>Planering</h1>
      <p className="description">
        Dagens godkända jobb per bil. Lägg jobb på bilar själv eller låt AI:n föreslå en
        plan. Varningarna kommer från fordonens egenskaper under Flotta.
      </p>

      <div className="toolbar">
        <div className="date-nav">
          <button className="secondary-button" onClick={() => setDatum(flytta(datum, -1))} type="button">
            ←
          </button>
          <input onChange={(event) => event.target.value && setDatum(event.target.value)} type="date" value={datum} />
          <button className="secondary-button" onClick={() => setDatum(flytta(datum, 1))} type="button">
            →
          </button>
          <strong className="date-label">{veckodag(datum)}</strong>
        </div>
        <button
          className="primary-button"
          disabled={!plan || thinking || busy || plan.ej_planerade.length === 0}
          onClick={suggest}
          type="button"
        >
          {thinking ? "AI:n planerar… (kan ta en minut)" : "Föreslå plan med AI"}
        </button>
      </div>

      {(error || companyError) && <p className="error-message" role="alert">{error || companyError}</p>}
      {plan?.varningar.map((varning) => (
        <p className="alert alert-uncertain" key={varning}>⚠ {varning}</p>
      ))}
      {plan && plan.utan_datum.length > 0 && (
        <p className="muted">
          {plan.utan_datum.length} godkända ordrar saknar datum och syns inte här. Rätta dem under{" "}
          <Link href="/orders">Ordrar</Link>.
        </p>
      )}

      {plan && suggestions && (
        <Suggestions
          busy={busy}
          drivers={plan.forare}
          key={suggestions.sammanfattning}
          onApply={applySuggestions}
          onDismiss={() => setSuggestions(null)}
          orders={allOrders}
          result={suggestions}
          vehicles={plan.bilar.map((bil) => bil.vehicle)}
        />
      )}

      {plan === null && !error && <p className="muted">Hämtar planen…</p>}
      {plan && (
        <div className="plan-board">
          <section className="plan-column unplanned">
            <header>
              <h2>Oplanerade</h2>
              <span className="muted">{plan.ej_planerade.length} jobb</span>
            </header>
            {plan.ej_planerade.length === 0 && <p className="muted">Inga oplanerade jobb den här dagen.</p>}
            {plan.ej_planerade.map((order) => (
              <JobCard companyId={companyId} key={order.id} order={order}>
                <select
                  aria-label="Lägg på bil"
                  className="assign-select"
                  disabled={busy || activeVehicles.length === 0}
                  onChange={(event) => {
                    const bil = plan.bilar.find((row) => row.vehicle.id === event.target.value);
                    assign([{ orderId: order.id, vehicleId: event.target.value, driverId: bil ? dayDriver(bil) || null : null }]);
                  }}
                  value=""
                >
                  <option value="">Lägg på bil…</option>
                  {activeVehicles.map((bil) => (
                    <option key={bil.vehicle.id} value={bil.vehicle.id}>
                      {bil.vehicle.registration_number}
                      {bil.vehicle.description && ` (${bil.vehicle.description})`}
                    </option>
                  ))}
                </select>
              </JobCard>
            ))}
          </section>

          {plan.bilar.length === 0 && (
            <section className="plan-column">
              <p className="muted">
                Inga fordon än. Lägg in dem under <Link href="/fleet">Flotta</Link>.
              </p>
            </section>
          )}

          {plan.bilar.map((bil) => (
            <section className="plan-column" key={bil.vehicle.id}>
              <header>
                <h2>{bil.vehicle.registration_number}</h2>
                <span className="muted">
                  {bil.vehicle.description && `${bil.vehicle.description} · `}
                  {kapacitet(bil.vikt_kg, bil.vehicle.max_weight_kg, "kg")} ·{" "}
                  {kapacitet(bil.pallar, bil.vehicle.pallet_places, "pall")}
                </span>
                <select
                  aria-label={`Förare för ${bil.vehicle.registration_number}`}
                  className={dayDriver(bil) || bil.ordrar.length === 0 ? "assign-select" : "assign-select unassigned"}
                  disabled={busy || bil.ordrar.length === 0}
                  onChange={(event) =>
                    assign(
                      bil.ordrar.map((jobb) => ({
                        orderId: jobb.order.id,
                        vehicleId: bil.vehicle.id,
                        driverId: event.target.value || null,
                      })),
                    )
                  }
                  value={dayDriver(bil)}
                >
                  <option value="">Förare…</option>
                  {activeDrivers.map((driver) => (
                    <option key={driver.id} value={driver.id}>
                      {driver.name}
                    </option>
                  ))}
                </select>
              </header>
              {bil.varningar.map((varning) => (
                <p className="job-warnings" key={varning}>⚠ {varning}</p>
              ))}
              {bil.ordrar.length === 0 && <p className="muted">Inga jobb.</p>}
              {bil.ordrar.map((jobb) => (
                <JobCard companyId={companyId} key={jobb.order.id} order={jobb.order} varningar={jobb.varningar}>
                  <button
                    className="link-button"
                    disabled={busy}
                    onClick={() => assign([{ orderId: jobb.order.id, vehicleId: null, driverId: null }])}
                    type="button"
                  >
                    Ta bort från bilen
                  </button>
                </JobCard>
              ))}
            </section>
          ))}
        </div>
      )}
    </>
  );
}

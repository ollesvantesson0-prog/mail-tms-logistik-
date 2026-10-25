"use client";

import { useEffect, useState } from "react";

import {
  api,
  MEDDELANDETYPER,
  ordersUrl,
  STATUSAR,
  useCompanyId,
  type Driver,
  type Order,
  type OrderStatus,
  type Vehicle,
} from "../lib/api";
import Assignment from "./assignment";

function tid(plats: { datum: string; tid_fran: string; tid_till: string }): string {
  const tider = [plats.tid_fran, plats.tid_till].filter(Boolean).join("–");
  return [plats.datum, tider].filter(Boolean).join(" ");
}

export default function OrdersPage() {
  const { companyId, error: companyError } = useCompanyId();
  const [status, setStatus] = useState<OrderStatus>("approved");
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!companyId) return;
    Promise.all([
      api<Vehicle[]>(`/api/companies/${companyId}/vehicles`),
      api<Driver[]>(`/api/companies/${companyId}/drivers`),
    ])
      .then(([fetchedVehicles, fetchedDrivers]) => {
        setVehicles(fetchedVehicles);
        setDrivers(fetchedDrivers);
      })
      .catch((fetchError: Error) => setError(fetchError.message));
  }, [companyId]);

  function replaceOrder(saved: Order) {
    setOrders((current) => current!.map((order) => (order.id === saved.id ? saved : order)));
  }

  useEffect(() => {
    if (!companyId) return;
    setOrders(null);
    api<Order[]>(ordersUrl(companyId, `?status=${status}`))
      .then(setOrders)
      .catch((fetchError: Error) => setError(fetchError.message));
  }, [companyId, status]);

  return (
    <>
      <p className="eyebrow">Arbetsyta</p>
      <h1>Ordrar</h1>
      <p className="description">
        Alla ordrar som har tolkats. Välj fordon och förare för godkända ordrar och
        exportera dem som CSV.
      </p>
      {(error || companyError) && <p className="error-message" role="alert">{error || companyError}</p>}

      <div className="toolbar">
        <div className="auth-tabs" aria-label="Filtrera på status">
          {(Object.keys(STATUSAR) as OrderStatus[]).map((value) => (
            <button
              className={value === status ? "auth-tab selected" : "auth-tab"}
              key={value}
              onClick={() => setStatus(value)}
              type="button"
            >
              {STATUSAR[value]}
            </button>
          ))}
        </div>
        {companyId && (
          <a className="secondary-button" download href={ordersUrl(companyId, "/export.csv")}>
            Exportera godkända som CSV
          </a>
        )}
      </div>

      <section className="placeholder table-wrapper">
        {orders === null ? (
          <p className="muted">Hämtar ordrar…</p>
        ) : orders.length === 0 ? (
          <p className="muted">Inga ordrar med status "{STATUSAR[status]}".</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Kund</th>
                <th>Typ</th>
                <th>Från</th>
                <th>Till</th>
                <th>Upphämtning</th>
                <th>Gods</th>
                <th>Krav</th>
                <th>Fordon</th>
                <th>Förare</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((row) => {
                const { id, meddelandetyp, order } = row;
                return (
                  <tr key={id}>
                    <td>
                      {order.kund.foretag || "–"}
                      {order.kundreferens && <span className="muted"> · {order.kundreferens}</span>}
                    </td>
                    <td>{MEDDELANDETYPER[meddelandetyp] ?? meddelandetyp}</td>
                    <td>{order.upphamtning.ort || order.upphamtning.foretag || "–"}</td>
                    <td>
                      {order.leveranser
                        .map((leverans) => leverans.ort || leverans.foretag)
                        .filter(Boolean)
                        .join(", ") || "–"}
                    </td>
                    <td>{tid(order.upphamtning) || "–"}</td>
                    <td>
                      {order.gods
                        .map((gods) => [gods.antal, gods.typ, gods.beskrivning].filter(Boolean).join(" "))
                        .join("; ") || "–"}
                    </td>
                    <td>
                      {Object.entries(order.krav)
                        .filter(([, value]) => value === true)
                        .map(([key]) => key)
                        .join(", ") || "–"}
                    </td>
                    {status === "approved" ? (
                      <Assignment
                        companyId={companyId}
                        drivers={drivers}
                        onError={setError}
                        onSaved={replaceOrder}
                        order={row}
                        vehicles={vehicles}
                      />
                    ) : (
                      <>
                        <td>{row.vehicle_registration ?? "–"}</td>
                        <td>{row.driver_name ?? "–"}</td>
                      </>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}

"use client";

import { useState } from "react";

import { api, ordersUrl, type Driver, type Order, type Vehicle } from "../lib/api";

type Props = {
  companyId: string;
  order: Order;
  vehicles: Vehicle[];
  drivers: Driver[];
  onSaved: (order: Order) => void;
  onError: (message: string) => void;
};

/** Två rullistor för att välja fordon och förare till en godkänd order. */
export default function Assignment({ companyId, order, vehicles, drivers, onSaved, onError }: Props) {
  const [busy, setBusy] = useState(false);

  async function save(change: { vehicle_id?: string | null; driver_id?: string | null }) {
    setBusy(true);
    onError("");
    try {
      const saved = await api<Order>(ordersUrl(companyId, `/${order.id}/assignment`), {
        method: "PUT",
        body: JSON.stringify({ vehicle_id: order.vehicle_id, driver_id: order.driver_id, ...change }),
      });
      onSaved(saved);
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Kunde inte spara tilldelningen.");
    } finally {
      setBusy(false);
    }
  }

  // Visa aktiva val, plus det som redan är tilldelat även om det har inaktiverats.
  const vehicleOptions = vehicles.filter((vehicle) => vehicle.is_active || vehicle.id === order.vehicle_id);
  const driverOptions = drivers.filter((driver) => driver.is_active || driver.id === order.driver_id);

  return (
    <>
      <td>
        <select
          aria-label="Fordon"
          className={order.vehicle_id ? "assign-select" : "assign-select unassigned"}
          disabled={busy}
          onChange={(event) => save({ vehicle_id: event.target.value || null })}
          value={order.vehicle_id ?? ""}
        >
          <option value="">– Välj –</option>
          {vehicleOptions.map((vehicle) => (
            <option key={vehicle.id} value={vehicle.id}>
              {vehicle.registration_number}
              {vehicle.description && ` (${vehicle.description})`}
            </option>
          ))}
        </select>
      </td>
      <td>
        <select
          aria-label="Förare"
          className={order.driver_id ? "assign-select" : "assign-select unassigned"}
          disabled={busy}
          onChange={(event) => save({ driver_id: event.target.value || null })}
          value={order.driver_id ?? ""}
        >
          <option value="">– Välj –</option>
          {driverOptions.map((driver) => (
            <option key={driver.id} value={driver.id}>
              {driver.name}
            </option>
          ))}
        </select>
      </td>
    </>
  );
}

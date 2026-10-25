"use client";

import { useEffect, useState } from "react";

import { api, CHANGE_TYPES, ordersUrl, STATUSAR, type MalOrder, type Order } from "../lib/api";

type Props = {
  companyId: string;
  order: Order;
  onSaved: (order: Order) => void;
  onError: (message: string) => void;
};

function beskriv(mal: Pick<MalOrder, "kund" | "kundreferens" | "fran" | "till" | "datum">): string {
  const ref = mal.kundreferens ? ` (${mal.kundreferens})` : "";
  return `${mal.kund || "Okänd kund"}${ref}: ${mal.fran || "?"} → ${mal.till || "?"}, ${mal.datum || "inget datum"}`;
}

/** Visar vilken order en ändring/avbokning gäller och vad som kommer att hända med den. */
export default function ChangePanel({ companyId, order, onSaved, onError }: Props) {
  const [candidates, setCandidates] = useState<Order[]>([]);
  const [busy, setBusy] = useState(false);
  const isCancellation = order.meddelandetyp === "avbokning";

  useEffect(() => {
    Promise.all([
      api<Order[]>(ordersUrl(companyId, "?status=approved")),
      api<Order[]>(ordersUrl(companyId, "?status=pending")),
    ])
      .then(([approved, pending]) =>
        setCandidates(
          [...approved, ...pending].filter((candidate) => !CHANGE_TYPES.includes(candidate.meddelandetyp)),
        ),
      )
      .catch((fetchError: Error) => onError(fetchError.message));
  }, [companyId, onError]);

  async function choose(malOrderId: string) {
    setBusy(true);
    onError("");
    try {
      const saved = await api<Order>(ordersUrl(companyId, `/${order.id}/target`), {
        method: "PUT",
        body: JSON.stringify({ mal_order_id: malOrderId || null }),
      });
      onSaved(saved);
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Kunde inte välja order.");
    } finally {
      setBusy(false);
    }
  }

  const mal = order.mal_order;
  const galler = order.order.galler_order;

  return (
    <div className={mal ? "change-panel" : "change-panel alert-missing"}>
      <strong>{isCancellation ? "Avbokning" : "Ändring"} av order {galler && `"${galler}"`}</strong>
      {mal ? (
        <p>
          Gäller: {beskriv(mal)} <span className="muted">· {STATUSAR[mal.status]}</span>
        </p>
      ) : (
        <p>
          Hittade ingen order med referensen {galler ? `"${galler}"` : "(ingen referens angiven)"}. Välj
          vilken order det gäller innan du godkänner.
        </p>
      )}
      <label>
        {mal ? "Fel order? Välj en annan:" : "Välj order:"}
        <select disabled={busy} onChange={(event) => choose(event.target.value)} value={mal?.id ?? ""}>
          <option value="">– Välj –</option>
          {candidates.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {beskriv({
                kund: candidate.order.kund.foretag,
                kundreferens: candidate.order.kundreferens,
                fran: candidate.order.upphamtning.ort,
                till: candidate.order.leveranser.map((leverans) => leverans.ort || leverans.foretag).join(", "),
                datum: candidate.order.upphamtning.datum,
              })}
            </option>
          ))}
        </select>
      </label>

      {mal && isCancellation && <p>När du godkänner markeras ordern som <strong>avbokad</strong>.</p>}
      {mal && !isCancellation && (
        order.forandringar.length === 0 ? (
          <p className="muted">Ändringen ändrar inga fält. Kontrollera de tolkade fälten nedan.</p>
        ) : (
          <table className="diff-table">
            <thead>
              <tr>
                <th>Fält</th>
                <th>Före</th>
                <th>Efter</th>
              </tr>
            </thead>
            <tbody>
              {order.forandringar.map((rad) => (
                <tr key={rad.falt}>
                  <td>{rad.falt}</td>
                  <td className="diff-before">{rad.fore}</td>
                  <td className="diff-after">{rad.efter}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </div>
  );
}

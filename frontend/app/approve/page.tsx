"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  api,
  CHANGE_TYPES,
  MEDDELANDETYPER,
  ordersUrl,
  useCompanyId,
  type Order,
  type TolkadOrder,
} from "../lib/api";
import ChangePanel from "./change-panel";
import OrderEditor from "./order-editor";
import ReplyDraft from "./reply-draft";

/** Tar bort tomma rader i listorna innan ordern sparas. */
function rensa(order: TolkadOrder): TolkadOrder {
  return {
    ...order,
    saknas: order.saknas.map((rad) => rad.trim()).filter(Boolean),
    osakerheter: order.osakerheter.map((rad) => rad.trim()).filter(Boolean),
  };
}

function rubrik(order: Order): string {
  const fran = order.order.upphamtning.ort || "?";
  const till = order.order.leveranser.map((leverans) => leverans.ort || "?").join(", ") || "?";
  return `${order.order.kund.foretag || "Okänd kund"}: ${fran} → ${till}`;
}

export default function ApprovePage() {
  const { companyId, error: companyError } = useCompanyId();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [draft, setDraft] = useState<TolkadOrder | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!companyId) return;
    api<Order[]>(ordersUrl(companyId, "?status=pending"))
      .then((pending) => {
        // Äldst först, så att det som kom in först granskas först.
        const sorted = [...pending].reverse();
        setOrders(sorted);
        if (sorted.length > 0) select(sorted[0]);
      })
      .catch((fetchError: Error) => setError(fetchError.message));
  }, [companyId]);

  const selected = orders?.find((order) => order.id === selectedId) ?? null;
  const isChange = selected !== null && CHANGE_TYPES.includes(selected.meddelandetyp);
  const isCancellation = selected?.meddelandetyp === "avbokning";

  function replaceOrder(saved: Order) {
    setOrders((current) => current!.map((order) => (order.id === saved.id ? saved : order)));
  }

  function select(order: Order) {
    setSelectedId(order.id);
    setDraft(order.order);
    setError("");
  }

  async function save(): Promise<Order> {
    const saved = await api<Order>(ordersUrl(companyId, `/${selectedId}`), {
      method: "PUT",
      body: JSON.stringify({ order: rensa(draft!) }),
    });
    replaceOrder(saved);
    setDraft(saved.order);
    return saved;
  }

  async function run(action: "save" | "approve" | "discard") {
    if (action === "discard" && !window.confirm("Kasta den här ordern?")) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (action !== "discard") await save();
      if (action === "save") {
        setMessage("Ändringarna är sparade.");
        return;
      }
      await api<Order>(ordersUrl(companyId, `/${selectedId}/${action}`), { method: "POST" });
      const remaining = orders!.filter((order) => order.id !== selectedId);
      setOrders(remaining);
      setMessage(
        action === "discard"
          ? "Ordern är kastad."
          : isCancellation
            ? "Ordern är avbokad."
            : isChange
              ? "Ändringen är genomförd på ordern."
              : "Ordern är godkänd.",
      );
      if (remaining.length > 0) {
        select(remaining[0]);
      } else {
        setSelectedId("");
        setDraft(null);
      }
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Något gick fel.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <p className="eyebrow">Arbetsyta</p>
      <h1>Godkänn</h1>
      <p className="description">
        Granska och rätta AI:ns tolkning. Rött betyder att viktig information saknas,
        gult att något är osäkert.
      </p>
      {(error || companyError) && <p className="error-message" role="alert">{error || companyError}</p>}
      {message && <p className="success-message" role="status">{message}</p>}

      {orders === null && !error && !companyError && <p className="muted">Hämtar ordrar…</p>}
      {orders?.length === 0 && (
        <section className="placeholder">
          <strong>Inget att granska.</strong>
          <p className="muted">
            Tolka ett nytt meddelande i <Link href="/inbox">Inkorgen</Link>.
          </p>
        </section>
      )}

      {orders && orders.length > 0 && (
        <div className="review-layout">
          <nav aria-label="Ordrar att granska" className="review-list">
            {orders.map((order) => (
              <button
                className={order.id === selectedId ? "review-item selected" : "review-item"}
                key={order.id}
                onClick={() => select(order)}
                type="button"
              >
                <strong>{rubrik(order)}</strong>
                <span>
                  {MEDDELANDETYPER[order.meddelandetyp] ?? order.meddelandetyp}
                  {order.order.saknas.length > 0 && ` · ${order.order.saknas.length} saknas`}
                </span>
              </button>
            ))}
          </nav>

          {selected && draft && (
            <section className="placeholder">
              <p className="eyebrow">{MEDDELANDETYPER[selected.meddelandetyp] ?? selected.meddelandetyp}</p>
              <p>{selected.sammanfattning}</p>
              <details className="original-message">
                <summary>
                  Originalmeddelande från {selected.meddelande.avsandare || "okänd avsändare"},{" "}
                  {selected.meddelande.mottagen.replace("T", " ").slice(0, 16)}
                </summary>
                <pre>{selected.meddelande.text}</pre>
              </details>

              {isChange && (
                <ChangePanel companyId={companyId} onError={setError} onSaved={replaceOrder} order={selected} />
              )}

              {!isCancellation && (
                <>
                  {isChange && (
                    <p className="muted">
                      Tolkade fält i ändringen. Bara ifyllda fält ändras på ordern. Tryck "Spara utkast"
                      för att uppdatera jämförelsen ovan.
                    </p>
                  )}
                  <OrderEditor
                    key={selected.id}
                    meddelandetyp={selected.meddelandetyp}
                    onChange={setDraft}
                    order={draft}
                  />
                </>
              )}

              <ReplyDraft
                companyId={companyId}
                key={`reply-${selected.id}`}
                onError={setError}
                onSaved={replaceOrder}
                order={selected}
                prepare={save}
              />

              <div className="button-row">
                <button
                  className="primary-button"
                  disabled={busy || (isChange && !selected.mal_order)}
                  onClick={() => run("approve")}
                  type="button"
                >
                  {isCancellation ? "Avboka ordern" : isChange ? "Genomför ändringen" : "Godkänn"}
                </button>
                <button className="secondary-button" disabled={busy} onClick={() => run("save")} type="button">
                  Spara utkast
                </button>
                <button className="danger-button" disabled={busy} onClick={() => run("discard")} type="button">
                  Kasta
                </button>
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}

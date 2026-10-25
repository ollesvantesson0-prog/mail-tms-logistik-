"use client";

import { useEffect, useState, type FormEvent } from "react";

import { api } from "../lib/api";

export type Field = {
  key: string;
  label: string;
  required?: boolean;
  placeholder?: string;
};

type Resource = { id: string; is_active: boolean } & Record<string, string | boolean>;

type Props = {
  title: string;
  /** T.ex. /api/companies/{id}/vehicles */
  url: string;
  fields: Field[];
  addLabel: string;
  emptyText: string;
};

function emptyForm(fields: Field[]): Record<string, string> {
  return Object.fromEntries(fields.map((field) => [field.key, ""]));
}

/** En lista med fordon eller förare: lägg till, ändra och inaktivera. */
export default function ResourceSection({ title, url, fields, addLabel, emptyText }: Props) {
  const [items, setItems] = useState<Resource[] | null>(null);
  const [form, setForm] = useState(() => emptyForm(fields));
  const [editingId, setEditingId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Resource[]>(url)
      .then(setItems)
      .catch((fetchError: Error) => setError(fetchError.message));
  }, [url]);

  function replaceItem(saved: Resource) {
    setItems((current) => {
      const exists = current!.some((item) => item.id === saved.id);
      return exists ? current!.map((item) => (item.id === saved.id ? saved : item)) : [...current!, saved];
    });
  }

  async function send(body: Record<string, string | boolean>, id = "") {
    setBusy(true);
    setError("");
    try {
      const saved = await api<Resource>(id ? `${url}/${id}` : url, {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(body),
      });
      replaceItem(saved);
      return true;
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Kunde inte spara.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const current = items?.find((item) => item.id === editingId);
    const ok = await send({ ...form, is_active: current?.is_active ?? true }, editingId);
    if (ok) cancel();
  }

  function edit(item: Resource) {
    setEditingId(item.id);
    setForm(Object.fromEntries(fields.map((field) => [field.key, String(item[field.key] ?? "")])));
  }

  function cancel() {
    setEditingId("");
    setForm(emptyForm(fields));
  }

  function toggleActive(item: Resource) {
    const values = Object.fromEntries(fields.map((field) => [field.key, item[field.key]]));
    send({ ...values, is_active: !item.is_active }, item.id);
  }

  return (
    <section className="placeholder">
      <h2>{title}</h2>
      {items === null ? (
        <p className="muted">Hämtar…</p>
      ) : items.length === 0 ? (
        <p className="muted">{emptyText}</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                {fields.map((field) => <th key={field.key}>{field.label}</th>)}
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr className={item.is_active ? undefined : "inactive-row"} key={item.id}>
                  {fields.map((field) => <td key={field.key}>{String(item[field.key] || "–")}</td>)}
                  <td>{item.is_active ? "Aktiv" : "Inaktiv"}</td>
                  <td className="row-actions">
                    <button className="link-button neutral" disabled={busy} onClick={() => edit(item)} type="button">
                      Ändra
                    </button>
                    <button className="link-button neutral" disabled={busy} onClick={() => toggleActive(item)} type="button">
                      {item.is_active ? "Inaktivera" : "Aktivera"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form className="auth-form" onSubmit={submit}>
        <h3>{editingId ? "Ändra" : addLabel}</h3>
        <div className="field-grid">
          {fields.map((field) => (
            <label key={field.key}>
              {field.label}
              <input
                onChange={(event) => setForm({ ...form, [field.key]: event.target.value })}
                placeholder={field.placeholder}
                required={field.required}
                value={form[field.key]}
              />
            </label>
          ))}
        </div>
        <div className="button-row compact">
          <button className="primary-button" disabled={busy} type="submit">
            {editingId ? "Spara" : "Lägg till"}
          </button>
          {editingId && (
            <button className="secondary-button" onClick={cancel} type="button">
              Avbryt
            </button>
          )}
        </div>
      </form>
      {error && <p className="error-message" role="alert">{error}</p>}
    </section>
  );
}

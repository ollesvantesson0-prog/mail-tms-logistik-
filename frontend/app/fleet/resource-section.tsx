"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { api } from "../lib/api";

export type Field = {
  key: string;
  label: string;
  type?: "text" | "number" | "checkbox";
  required?: boolean;
  placeholder?: string;
};

type Value = string | number | boolean | null;
export type Resource = { id: string; is_active: boolean } & Record<string, Value>;
type FormValues = Record<string, string | boolean>;

type Props = {
  title: string;
  /** T.ex. /api/companies/{id}/vehicles */
  url: string;
  fields: Field[];
  addLabel: string;
  emptyText: string;
  /** Extra knappar per rad, t.ex. förarlänken. */
  rowActions?: (item: Resource) => ReactNode;
};

function emptyForm(fields: Field[]): FormValues {
  return Object.fromEntries(fields.map((field) => [field.key, field.type === "checkbox" ? false : ""]));
}

/** Formulärets värden som API:et vill ha dem: tal som tal, tomma tal som null. */
function toBody(fields: Field[], form: FormValues): Record<string, Value> {
  return Object.fromEntries(
    fields.map((field) => {
      const value = form[field.key];
      if (field.type === "number") return [field.key, value === "" ? null : Number(value)];
      return [field.key, value];
    }),
  );
}

function display(field: Field, value: Value): string {
  if (field.type === "checkbox") return value ? "✓" : "–";
  return value === null || value === "" ? "–" : String(value);
}

/** En lista med fordon eller förare: lägg till, ändra och inaktivera. */
export default function ResourceSection({ title, url, fields, addLabel, emptyText, rowActions }: Props) {
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

  async function send(body: Record<string, Value>, id = "") {
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
    const ok = await send({ ...toBody(fields, form), is_active: current?.is_active ?? true }, editingId);
    if (ok) cancel();
  }

  function edit(item: Resource) {
    setEditingId(item.id);
    setForm(
      Object.fromEntries(
        fields.map((field) => [
          field.key,
          field.type === "checkbox" ? Boolean(item[field.key]) : String(item[field.key] ?? ""),
        ]),
      ),
    );
  }

  function cancel() {
    setEditingId("");
    setForm(emptyForm(fields));
  }

  function toggleActive(item: Resource) {
    const values = Object.fromEntries(fields.map((field) => [field.key, item[field.key]]));
    send({ ...values, is_active: !item.is_active }, item.id);
  }

  const textFields = fields.filter((field) => field.type !== "checkbox");
  const checkboxFields = fields.filter((field) => field.type === "checkbox");

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
                {rowActions && <th />}
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr className={item.is_active ? undefined : "inactive-row"} key={item.id}>
                  {fields.map((field) => <td key={field.key}>{display(field, item[field.key])}</td>)}
                  <td>{item.is_active ? "Aktiv" : "Inaktiv"}</td>
                  {rowActions && <td>{item.is_active && rowActions(item)}</td>}
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
          {textFields.map((field) => (
            <label key={field.key}>
              {field.label}
              <input
                min={field.type === "number" ? 0 : undefined}
                onChange={(event) => setForm({ ...form, [field.key]: event.target.value })}
                placeholder={field.placeholder}
                required={field.required}
                type={field.type ?? "text"}
                value={form[field.key] as string}
              />
            </label>
          ))}
        </div>
        {checkboxFields.length > 0 && (
          <div className="checkbox-grid">
            {checkboxFields.map((field) => (
              <label className="checkbox" key={field.key}>
                <input
                  checked={form[field.key] as boolean}
                  onChange={(event) => setForm({ ...form, [field.key]: event.target.checked })}
                  type="checkbox"
                />
                {field.label}
              </label>
            ))}
          </div>
        )}
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

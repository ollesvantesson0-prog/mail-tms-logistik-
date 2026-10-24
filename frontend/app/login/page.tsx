"use client";

import { useState, type FormEvent } from "react";

type Mode = "login" | "register";

export default function LoginPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setError("");

    try {
      const response = await fetch(`/api/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(
          mode === "login"
            ? { email, password }
            : { company_name: companyName, email, password },
        ),
      });
      const result = await response.json();
      if (!response.ok) {
        const detail = result.detail;
        throw new Error(typeof detail === "string" ? detail : "Kontot kunde inte verifieras.");
      }

      const companyCount = result.companies.length;
      setMessage(
        `Du är inloggad som ${result.user.email}. Kontot har åtkomst till ${companyCount} företag.`,
      );
      window.location.assign("/inbox");
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Kunde inte kontakta servern. Kontrollera att API:t kör.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <p className="eyebrow">Konto</p>
      <h1>{mode === "login" ? "Logga in" : "Skapa åkeri och konto"}</h1>
      <p className="description">
        Den här första inloggningen är för lokal utveckling. Skapa ett åkeri eller
        logga in på ett konto som redan finns.
      </p>
      <section className="placeholder auth-card">
        <div className="auth-tabs" aria-label="Välj kontoåtgärd">
          <button
            className={mode === "login" ? "auth-tab selected" : "auth-tab"}
            onClick={() => setMode("login")}
            type="button"
          >
            Logga in
          </button>
          <button
            className={mode === "register" ? "auth-tab selected" : "auth-tab"}
            onClick={() => setMode("register")}
            type="button"
          >
            Skapa konto
          </button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && (
            <label>
              Åkeriets namn
              <input
                autoComplete="organization"
                maxLength={200}
                minLength={2}
                onChange={(event) => setCompanyName(event.target.value)}
                required
                value={companyName}
              />
            </label>
          )}
          <label>
            E-post
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label>
            Lösenord
            <input
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={mode === "register" ? 12 : 1}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
            {mode === "register" && <span>Minst 12 tecken.</span>}
          </label>
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Vänta…" : mode === "login" ? "Logga in" : "Skapa konto"}
          </button>
        </form>
        {message && <p className="success-message" role="status">{message}</p>}
        {error && <p className="error-message" role="alert">{error}</p>}
      </section>
    </>
  );
}

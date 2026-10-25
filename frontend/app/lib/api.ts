"use client";

import { useEffect, useState } from "react";

// Samma struktur som JSON-schemat i backend/app/modules/order_intake/interpreter.py.
export type Plats = {
  foretag: string;
  adress: string;
  postnummer: string;
  ort: string;
  datum: string;
  tid_fran: string;
  tid_till: string;
};

export const GODSTYPER = ["EUR-pall", "kolli", "fat", "bur", "lastmeter", "annat"] as const;

export type Gods = {
  antal: number | null;
  typ: (typeof GODSTYPER)[number];
  beskrivning: string;
  vikt_kg: number | null;
  matt: string;
};

export type Krav = {
  bakgavellyft: boolean;
  kran: boolean;
  kyl: boolean;
  temperatur: string;
  adr: boolean;
  un_nummer: string;
  barhjalp: boolean;
  akut: boolean;
  aterkommande: boolean;
};

export type TolkadOrder = {
  kund: { foretag: string; kontaktperson: string; telefon: string; epost: string };
  kundreferens: string;
  upphamtning: Plats;
  leveranser: Plats[];
  gods: Gods[];
  krav: Krav;
  galler_order: string;
  saknas: string[];
  osakerheter: string[];
};

export type OrderStatus = "pending" | "approved" | "discarded" | "applied" | "cancelled";

export type Order = {
  id: string;
  status: OrderStatus;
  created_at: string;
  meddelandetyp: string;
  sammanfattning: string;
  meddelande: { text: string; avsandare: string; mottagen: string };
  order: TolkadOrder;
  vehicle_id: string | null;
  vehicle_registration: string | null;
  driver_id: string | null;
  driver_name: string | null;
  /** Bara för ändringar och avbokningar: ordern som meddelandet gäller. */
  mal_order: MalOrder | null;
  forandringar: { falt: string; fore: string; efter: string }[];
  historik: { typ: string; tid: string; sammanfattning: string }[];
  svarsutkast: { amne: string; text: string; skapad: string } | null;
};

export type MalOrder = {
  id: string;
  status: OrderStatus;
  kund: string;
  kundreferens: string;
  fran: string;
  till: string;
  datum: string;
};

export const CHANGE_TYPES = ["andring", "avbokning"];

export type Vehicle = { id: string; registration_number: string; description: string; is_active: boolean };

export type Driver = { id: string; name: string; phone: string; is_active: boolean };

export const MEDDELANDETYPER: Record<string, string> = {
  ny_order: "Ny order",
  andring: "Ändring",
  avbokning: "Avbokning",
  prisforfragan: "Prisförfrågan",
  ej_order: "Ej order",
};

export const STATUSAR: Record<OrderStatus, string> = {
  pending: "Väntar på granskning",
  approved: "Godkänd",
  discarded: "Kastad",
  cancelled: "Avbokad",
  applied: "Genomförd ändring",
};

export function tomPlats(): Plats {
  return { foretag: "", adress: "", postnummer: "", ort: "", datum: "", tid_fran: "", tid_till: "" };
}

export function tomtGods(): Gods {
  return { antal: null, typ: "EUR-pall", beskrivning: "", vikt_kg: null, matt: "" };
}

/** Anropar backend och kastar ett fel med serverns meddelande om något gick fel. */
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
  });
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("Logga in först.");
  }
  const result = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = result?.detail;
    throw new Error(typeof detail === "string" ? detail : `Servern svarade med fel ${response.status}.`);
  }
  return result as T;
}

/** Hämtar det inloggade kontots företag. Skickar till inloggningen om ingen är inloggad. */
export function useCompanyId(): { companyId: string; error: string } {
  const [companyId, setCompanyId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ companies: { company_id: string }[] }>("/api/auth/me")
      .then((account) => {
        if (account.companies.length === 0) {
          setError("Kontot är inte kopplat till något åkeri.");
        } else {
          // Ett konto har bara ett åkeri än så länge.
          setCompanyId(account.companies[0].company_id);
        }
      })
      .catch((fetchError: Error) => setError(fetchError.message));
  }, []);

  return { companyId, error };
}

export function ordersUrl(companyId: string, rest = ""): string {
  return `/api/companies/${companyId}/orders${rest}`;
}

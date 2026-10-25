"use client";

import { useCompanyId } from "../lib/api";
import ResourceSection from "./resource-section";

export default function FleetPage() {
  const { companyId, error } = useCompanyId();

  return (
    <>
      <p className="eyebrow">Arbetsyta</p>
      <h1>Flotta</h1>
      <p className="description">
        Åkeriets fordon och förare. Egenskaperna används i planeringen för att varna när
        ett jobb inte passar en bil. Inaktivera i stället för att ta bort, så att gamla
        ordrar fortfarande visar vem som körde.
      </p>
      {error && <p className="error-message" role="alert">{error}</p>}
      {companyId && (
        <>
          <ResourceSection
            addLabel="Lägg till fordon"
            emptyText="Inga fordon än."
            fields={[
              { key: "registration_number", label: "Registreringsnummer", required: true, placeholder: "ABC123" },
              { key: "description", label: "Beskrivning", placeholder: "T.ex. distributionsbil 18 ton" },
              { key: "max_weight_kg", label: "Max last (kg)", type: "number", placeholder: "T.ex. 8000" },
              { key: "pallet_places", label: "Pallplatser", type: "number", placeholder: "T.ex. 18" },
              { key: "has_tail_lift", label: "Bakgavellyft", type: "checkbox" },
              { key: "has_cooling", label: "Kyl", type: "checkbox" },
              { key: "has_crane", label: "Kran", type: "checkbox" },
              { key: "adr_approved", label: "ADR-godkänd", type: "checkbox" },
            ]}
            title="Fordon"
            url={`/api/companies/${companyId}/vehicles`}
          />
          <ResourceSection
            addLabel="Lägg till förare"
            emptyText="Inga förare än."
            fields={[
              { key: "name", label: "Namn", required: true },
              { key: "phone", label: "Telefon", placeholder: "070-123 45 67" },
              { key: "has_adr_license", label: "ADR-behörighet", type: "checkbox" },
            ]}
            title="Förare"
            url={`/api/companies/${companyId}/drivers`}
          />
        </>
      )}
    </>
  );
}

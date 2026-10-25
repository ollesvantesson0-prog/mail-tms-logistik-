import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./styles.css";

export const metadata: Metadata = {
  title: "AI Trafikledning",
  description: "Lokal grund för plattformen AI Trafikledning",
};

const navigation = [
  { href: "/inbox", label: "Inkorg" },
  { href: "/orders", label: "Ordrar" },
  { href: "/plan", label: "Planering" },
  { href: "/fleet", label: "Flotta" },
  { href: "/approve", label: "Godkänn" },
  { href: "/login", label: "Logga in" },
];

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="sv">
      <body>
        <div className="layout">
          <aside className="sidebar">
            <Link className="brand" href="/inbox">
              AI Trafikledning
            </Link>
            <nav aria-label="Huvudmeny">
              {navigation.map((item) => (
                <Link className="nav-link" href={item.href} key={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
            <p className="sidebar-note">Lokal utvecklingsversion</p>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}

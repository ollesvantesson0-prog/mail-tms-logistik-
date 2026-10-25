import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import Shell from "./shell";
import "./styles.css";

export const metadata: Metadata = {
  title: "AI Trafikledning",
  description: "Lokal grund för plattformen AI Trafikledning",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="sv">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}

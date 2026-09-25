import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Planejamento Tributário — Importação e Conciliação",
  description: "Importação, conciliação e homologação de PGDAS-D e relatórios Alterdata",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Os PDFs vão direto do navegador para o Storage; server actions só recebem metadados.
  experimental: {
    serverActions: { bodySizeLimit: "1mb" },
  },
  poweredByHeader: false,
  async redirects() {
    return [{ source: "/", destination: "/cases", permanent: false }];
  },
};

export default nextConfig;

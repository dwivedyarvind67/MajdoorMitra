import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Serialize static generation to avoid intermittent Windows/OneDrive mkdir failures.
  experimental: { cpus: 1 },
  cacheComponents: true,
  partialPrefetching: true,
};

export default nextConfig;

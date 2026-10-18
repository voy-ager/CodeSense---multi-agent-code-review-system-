import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the root: a stray lockfile in a parent folder otherwise makes Turbopack
  // treat the whole home directory as the workspace.
  turbopack: { root: __dirname },
};

export default nextConfig;

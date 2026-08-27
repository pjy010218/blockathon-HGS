import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Keep build tracing scoped to this standalone frontend even when the
  // repository root contains tooling dependencies of its own.
  outputFileTracingRoot: process.cwd(),
  webpack(config) {
    // MetaMask SDK references this React Native-only optional peer from its
    // browser bundle. The web client uses browser storage instead.
    config.resolve.alias["@react-native-async-storage/async-storage"] = false;
    return config;
  },
};

export default nextConfig;

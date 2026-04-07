import type { NextConfig } from "next";

const protocol = process.env.NEXT_PUBLIC_IMAGE_PROTOCOL;
const hostname = process.env.NEXT_PUBLIC_IMAGE_HOSTNAME;
const port = process.env.NEXT_PUBLIC_IMAGE_PORT || "";

if (!protocol || !hostname) {
  throw new Error(
    "FATAL: Missing required Next.js Image configuration environment variables (NEXT_PUBLIC_IMAGE_PROTOCOL, NEXT_PUBLIC_IMAGE_HOSTNAME)."
  );
}

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: protocol as "http" | "https",
        hostname,
        port,
        pathname: "/**",
      },
    ],

    // Required for local MinIO / local-network image optimization in dev
    dangerouslyAllowLocalIP: true,

    // Explicit and production-safe in Next 16
    qualities: [75],
  },
};

export default nextConfig;
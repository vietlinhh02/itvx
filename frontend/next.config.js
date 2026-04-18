/** @type {import('next').NextConfig} */
const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

const nextConfig = {
  typedRoutes: true,
  experimental: {
    // Match the backend company document upload limit so rewrite proxying does not truncate uploads.
    proxyClientMaxBodySize: 52_428_800,
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
        port: "",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "api.dicebear.com",
        port: "",
        pathname: "/**",
      },
    ],
  },
  async rewrites() {
    if (!backendBaseUrl) {
      return []
    }

    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendBaseUrl}/api/v1/:path*`,
      },
    ]
  },
}

module.exports = nextConfig

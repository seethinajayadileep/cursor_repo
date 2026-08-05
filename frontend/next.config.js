/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output is for Docker/Railway-style Node hosts, not Vercel
  ...(process.env.DOCKER === "1" ? { output: "standalone" } : {}),
};

module.exports = nextConfig;

/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_PUBLIC_BASE_PATH;
const nextConfig = {
  output: "export",
  reactStrictMode: true,
  trailingSlash: true,
  ...(basePath ? { basePath } : {}),
  images: { unoptimized: true },
  distDir: process.env.NEXT_DIST_DIR || ".next"
};

export default nextConfig;

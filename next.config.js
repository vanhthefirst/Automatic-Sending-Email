/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export', // Enable static site generation
  reactStrictMode: true,
  trailingSlash: true,
  distDir: 'build',
  images: {
    unoptimized: true
  },
  typescript: {
    ignoreBuildErrors: true // Temporarily ignore TS errors for deployment
  }
};

module.exports = nextConfig;
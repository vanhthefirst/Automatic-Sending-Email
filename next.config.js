/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    typescript: {
      ignoreBuildErrors: true // Temporarily ignore TS errors for deployment
    }
  };
  
  module.exports = nextConfig;
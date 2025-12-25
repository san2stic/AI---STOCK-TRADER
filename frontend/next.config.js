/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: process.env.API_URL ? `${process.env.API_URL}/api/:path*` : 'http://backend:8000/api/:path*',
            },
        ]
    },
}

module.exports = nextConfig

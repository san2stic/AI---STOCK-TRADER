/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        return [
            {
                source: '/api/health',
                destination: process.env.API_URL ? `${process.env.API_URL}/health` : 'http://backend:8000/health',
            },
            {
                source: '/api/:path*',
                destination: process.env.API_URL ? `${process.env.API_URL}/api/:path*` : 'http://backend:8000/api/:path*',
            },
            {
                source: '/ws',
                destination: process.env.API_URL ? `${process.env.API_URL}/ws` : 'http://backend:8000/ws',
            },
        ]
    },
}

module.exports = nextConfig

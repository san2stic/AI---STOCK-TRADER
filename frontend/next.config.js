/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        return [
            {
                source: '/api/models/:path*',
                destination: process.env.API_URL ? `${process.env.API_URL}/api/models/:path*` : 'http://backend:8000/api/models/:path*',
            },
            {
                source: '/api/learning/:path*',
                destination: process.env.API_URL ? `${process.env.API_URL}/api/learning/:path*` : 'http://backend:8000/api/learning/:path*',
            },
            {
                source: '/api/:path*',
                destination: process.env.API_URL ? `${process.env.API_URL}/:path*` : 'http://backend:8000/:path*',
            },
        ]
    },
}

module.exports = nextConfig

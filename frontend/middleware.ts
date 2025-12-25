import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
    // Only handle /api/ routes
    if (request.nextUrl.pathname.startsWith('/api/')) {
        // Get the API URL from environment variables, fallback to localhost for dev
        const apiUrl = process.env.API_URL || 'http://localhost:8000'

        // Construct the target URL
        // Remove /api/ prefix if the backend doesn't expect it, or keep it if it does.
        // Based on backend routes (api/crew_routes etc), the backend seems to expect /api/ prefix 
        // OR routes are mounted directly. 
        // Looking at main.py: 
        // app.include_router(model_router, tags=["models"]) -> /models/... (likely)
        // Let's check a route definition to be sure.
        // But typically if we proxy /api/foo -> http://backend:8000/foo, we strip /api.

        // Let's inspect the target URL logic.
        // If request is /api/health, we want to hit http://backend:8000/health (based on curl test earlier).
        // So we should replace /api/ with /

        const targetUrl = new URL(
            request.nextUrl.pathname.replace(/^\/api/, ''),
            apiUrl
        )

        // Copy query parameters
        request.nextUrl.searchParams.forEach((value, key) => {
            targetUrl.searchParams.append(key, value)
        })

        // Create headers
        const headers = new Headers(request.headers)
        headers.set('Host', new URL(apiUrl).host)

        return NextResponse.rewrite(targetUrl, {
            request: {
                headers,
            },
        })
    }
}

export const config = {
    matcher: '/api/:path*',
}

/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './app/**/*.{js,ts,jsx,tsx,mdx}',
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // Core
                background: '#0a0e17',
                surface: {
                    DEFAULT: '#111827',
                    elevated: '#1f2937',
                    border: 'rgba(75, 85, 99, 0.4)',
                },
                // Primary - Cyan
                primary: {
                    DEFAULT: '#06b6d4',
                    hover: '#22d3ee',
                    muted: 'rgba(6, 182, 212, 0.2)',
                    glow: 'rgba(6, 182, 212, 0.4)',
                },
                // Secondary - Violet
                secondary: {
                    DEFAULT: '#8b5cf6',
                    hover: '#a78bfa',
                    muted: 'rgba(139, 92, 246, 0.2)',
                },
                // Success - Emerald
                success: {
                    DEFAULT: '#10b981',
                    hover: '#34d399',
                    muted: 'rgba(16, 185, 129, 0.2)',
                },
                // Warning - Amber
                warning: {
                    DEFAULT: '#f59e0b',
                    hover: '#fbbf24',
                    muted: 'rgba(245, 158, 11, 0.2)',
                },
                // Danger - Rose
                danger: {
                    DEFAULT: '#f43f5e',
                    hover: '#fb7185',
                    muted: 'rgba(244, 63, 94, 0.2)',
                },
            },
            fontFamily: {
                sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
                mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
            },
            fontSize: {
                '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
            },
            spacing: {
                '18': '4.5rem',
                '88': '22rem',
                '128': '32rem',
            },
            borderRadius: {
                '4xl': '2rem',
            },
            boxShadow: {
                'glow-primary': '0 0 20px rgba(6, 182, 212, 0.3), 0 0 40px rgba(6, 182, 212, 0.1)',
                'glow-success': '0 0 20px rgba(16, 185, 129, 0.3)',
                'glow-danger': '0 0 20px rgba(244, 63, 94, 0.3)',
                'glow-warning': '0 0 20px rgba(245, 158, 11, 0.3)',
                'inner-glow': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
                'card': '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3)',
                'card-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.4)',
            },
            backgroundImage: {
                'gradient-primary': 'linear-gradient(135deg, #06b6d4 0%, #8b5cf6 100%)',
                'gradient-success': 'linear-gradient(135deg, #10b981 0%, #06b6d4 100%)',
                'gradient-danger': 'linear-gradient(135deg, #f43f5e 0%, #f59e0b 100%)',
                'gradient-surface': 'linear-gradient(180deg, rgba(31, 41, 55, 0.8) 0%, rgba(17, 24, 39, 0.9) 100%)',
                'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
            },
            animation: {
                'fade-in': 'fadeIn 0.4s ease-out forwards',
                'slide-in': 'slideInRight 0.3s ease-out forwards',
                'slide-up': 'slideUp 0.3s ease-out forwards',
                'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
                'shimmer': 'shimmer 1.5s infinite',
                'bounce-subtle': 'bounceSubtle 2s ease-in-out infinite',
                'spin-slow': 'spin 3s linear infinite',
                'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideInRight: {
                    '0%': { opacity: '0', transform: 'translateX(20px)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                pulseGlow: {
                    '0%, 100%': { boxShadow: '0 0 5px rgba(6, 182, 212, 0.2)' },
                    '50%': { boxShadow: '0 0 20px rgba(6, 182, 212, 0.4), 0 0 30px rgba(6, 182, 212, 0.2)' },
                },
                shimmer: {
                    '0%': { backgroundPosition: '-200% 0' },
                    '100%': { backgroundPosition: '200% 0' },
                },
                bounceSubtle: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-5px)' },
                },
            },
            backdropBlur: {
                xs: '2px',
            },
            transitionDuration: {
                '400': '400ms',
            },
            zIndex: {
                '60': '60',
                '70': '70',
                '80': '80',
                '90': '90',
                '100': '100',
            },
        },
    },
    plugins: [],
};

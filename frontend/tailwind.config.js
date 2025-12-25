/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                background: '#05050A', // Deep space black
                surface: {
                    DEFAULT: '#0A0A12', // Slightly lighter for cards
                    hover: '#12121F',
                    active: '#1A1A2E',
                    border: 'rgba(255, 255, 255, 0.08)',
                },
                primary: {
                    DEFAULT: '#00F0FF', // Cyber Cyan
                    dark: '#00B8D4',
                    glow: 'rgba(0, 240, 255, 0.5)',
                },
                secondary: {
                    DEFAULT: '#7000FF', // Cyber Purple
                    hover: '#5E00D6',
                    glow: 'rgba(112, 0, 255, 0.5)',
                },
                accent: {
                    pink: '#FF0099', // Cyber Pink
                    yellow: '#FAFF00', // Cyber Yellow
                    green: '#39FF14', // Neon Green
                },
                status: {
                    success: '#00E676',
                    warning: '#FFEA00',
                    error: '#FF1744',
                    info: '#2979FF',
                },
                gray: {
                    100: '#E0E0E0',
                    200: '#BDBDBD',
                    300: '#9E9E9E',
                    400: '#757575',
                    500: '#616161',
                    600: '#424242',
                    700: '#303030',
                    800: '#212121',
                    900: '#121212',
                }
            },
            fontFamily: {
                sans: ['var(--font-inter)', 'sans-serif'],
                mono: ['var(--font-jetbrains-mono)', 'monospace'],
                display: ['var(--font-outfit)', 'sans-serif'], // Suggested new font for headers
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
                'cyber-grid': 'linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px)',
                'glass-gradient': 'linear-gradient(145deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%)',
                'glow-mesh': 'radial-gradient(circle at 50% 50%, rgba(112, 0, 255, 0.15) 0%, transparent 50%)',
            },
            boxShadow: {
                'neon-blue': '0 0 5px #00F0FF, 0 0 20px rgba(0, 240, 255, 0.3)',
                'neon-purple': '0 0 5px #7000FF, 0 0 20px rgba(112, 0, 255, 0.3)',
                'neon-pink': '0 0 5px #FF0099, 0 0 20px rgba(255, 0, 153, 0.3)',
                'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
            },
            animation: {
                'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'float': 'float 6s ease-in-out infinite',
                'slide-up': 'slideUp 0.5s ease-out forwards',
                'scan': 'scan 2s linear infinite',
            },
            keyframes: {
                float: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-10px)' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' },
                },
                scan: {
                    '0%': { backgroundPosition: '0% 0%' },
                    '100%': { backgroundPosition: '0% 100%' },
                }
            }
        },
    },
    plugins: [],
}

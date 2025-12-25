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
                // Premium Cyberpunk/Fintech Palette
                background: '#0a0a0f',
                surface: {
                    DEFAULT: '#13131f',
                    hover: '#1c1c2e',
                    active: '#242438',
                },
                primary: {
                    DEFAULT: '#00f2fe',
                    hover: '#00c2cb',
                    glow: 'rgba(0, 242, 254, 0.5)',
                },
                secondary: {
                    DEFAULT: '#4facfe',
                    hover: '#3b8ccf',
                },
                accent: {
                    DEFAULT: '#f093fb',
                    pink: '#f5576c',
                    purple: '#a18cd1',
                },
                success: {
                    DEFAULT: '#00e676',
                    glow: 'rgba(0, 230, 118, 0.4)',
                },
                danger: {
                    DEFAULT: '#ff5252',
                    glow: 'rgba(255, 82, 82, 0.4)',
                },
                warning: '#ffd740',
                info: '#40c4ff',
            },
            fontFamily: {
                sans: ['var(--font-inter)', 'sans-serif'],
                mono: ['var(--font-jetbrains-mono)', 'monospace'],
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'premium-gradient': 'linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)',
                'card-gradient': 'linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%)',
                'glass-shine': 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 60%)',
            },
            keyframes: {
                'fade-in-up': {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                'pulse-glow': {
                    '0%, 100%': { boxShadow: '0 0 15px rgba(0, 242, 254, 0.3)' },
                    '50%': { boxShadow: '0 0 30px rgba(0, 242, 254, 0.6)' },
                },
                'market-pulse': {
                    '0%': { transform: 'scale(1)', opacity: '1' },
                    '50%': { transform: 'scale(1.05)', opacity: '0.8' },
                    '100%': { transform: 'scale(1)', opacity: '1' },
                },
                shimmer: {
                    '0%': { backgroundPosition: '-200% 0' },
                    '100%': { backgroundPosition: '200% 0' },
                },
                'scale-up': {
                    '0%': { opacity: '0', transform: 'scale(0.95)' },
                    '100%': { opacity: '1', transform: 'scale(1)' },
                },
                'fade-in': {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                'gradient': {
                    '0%': { backgroundPosition: '0% 50%' },
                    '50%': { backgroundPosition: '100% 50%' },
                    '100%': { backgroundPosition: '0% 50%' },
                },
            },
            animation: {
                'fade-in-up': 'fade-in-up 0.5s ease-out forwards',
                'pulse-glow': 'pulse-glow 2s infinite',
                'market-pulse': 'market-pulse 3s infinite ease-in-out',
                'shimmer': 'shimmer 3s infinite linear',
                'scale-up': 'scale-up 0.3s ease-out forwards',
                'fade-in': 'fade-in 0.2s ease-out forwards',
                'gradient': 'gradient 8s ease infinite',
            },
            boxShadow: {
                'neon': '0 0 10px rgba(0, 242, 254, 0.5), 0 0 20px rgba(0, 242, 254, 0.3)',
                'neon-blue': '0 0 5px #03e9f4, 0 0 25px #03e9f4, 0 0 50px #03e9f4, 0 0 100px #03e9f4',
            },
        },
    },
    plugins: [],
}

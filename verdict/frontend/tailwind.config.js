/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0d0d0d',
          secondary: '#161616',
          surface: '#1a1a1a',
          elevated: '#222222',
          hover: '#2a2a2a',
        },
        gold: { DEFAULT: '#d4a853', light: '#e0be72', dark: '#b08d3e' },
        prosecutor: '#ef4444',
        defense: '#3b82f6',
        judge: '#f59e0b',
        witness: '#a78bfa',
        synthesis: '#10b981',
        research: '#6b7280',
      },
      fontFamily: {
        body: ['Inter', '-apple-system', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}

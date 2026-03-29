/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: '#050508',
        surface: '#0c0c14',
        elevated: '#12121e',
        prosecutor: '#f43f5e',
        defense: '#3b82f6',
        judge: '#f59e0b',
        witness: '#a78bfa',
        synthesis: '#10b981',
        research: '#94a3b8',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '16px',
      },
    },
  },
  plugins: [],
}

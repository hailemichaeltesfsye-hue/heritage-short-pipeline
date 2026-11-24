/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        studio: {
          bg: '#0a0b0e',
          card: '#12141a',
          surface: '#181b22',
          border: '#242833',
          amber: '#d97706',
          gold: '#f59e0b',
          accent: '#b45309',
        }
      },
      fontFamily: {
        cinematic: ['Cinzel', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}

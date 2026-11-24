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
        obsidian: {
          DEFAULT: '#09090b',
          surface: '#111114',
          elevated: '#18181b',
        },
        amberaccent: {
          DEFAULT: '#d97706',
          soft: '#f59e0b',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Noto Sans Ethiopic"', 'system-ui', 'sans-serif'],
        ethiopic: ['"Noto Sans Ethiopic"', '"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
};

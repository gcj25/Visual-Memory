/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ['"IBM Plex Sans"', "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
                    mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"] },
      colors: {
        ink: { 950: "#0a1020", 900: "#0e1627", 800: "#142034", 700: "#1c2b45", 600: "#2a3c5e" },
        mist: { 100: "#e8edf6", 300: "#b4c0d6", 500: "#8393ad", 700: "#566581" },
        accent: { DEFAULT: "#8aa4ff", strong: "#a9bcff" },
        kept: "#4caf50", moved: "#ffa500", fresh: "#1e90ff", gone: "#e63c3c",
      },
    },
  },
  plugins: [],
};

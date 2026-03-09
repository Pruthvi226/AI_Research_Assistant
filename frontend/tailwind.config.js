/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'DM Sans'", "system-ui", "sans-serif"],
        display: ["'Instrument Serif'", "Georgia", "serif"],
      },
      colors: {
        paper: {
          50: "#faf9f7",
          100: "#f0ede8",
          200: "#e5e0d8",
          800: "#2d2a26",
          900: "#1a1816",
        },
        accent: {
          DEFAULT: "#2563eb",
          light: "#3b82f6",
          dark: "#1d4ed8",
        },
      },
    },
  },
  plugins: [],
};

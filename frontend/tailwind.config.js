/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0E1414",
        stock: "#EFF3EC",
        surface: "#FBFBF8",
        park: {
          DEFAULT: "#1F7A5C",
          dark: "#155A44",
        },
        gold: "#C89B3C",
        hairline: "#C9D2C6",
        inktext: "#16211D",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'IBM Plex Sans'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
        comico: ["'Comico-Regular'", "sans-serif"],
      },
    },
  },
  plugins: [],
}
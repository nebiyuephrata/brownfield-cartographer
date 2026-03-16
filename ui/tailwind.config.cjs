/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"] ,
  theme: {
    extend: {
      colors: {
        graphite: {
          50: "#f5f7f8",
          100: "#e8edf0",
          200: "#c9d4dc",
          300: "#a9b9c5",
          400: "#8aa0b1",
          500: "#6d8596",
          600: "#556a7a",
          700: "#3f4f5c",
          800: "#2b353f",
          900: "#1c2229"
        },
        signal: {
          400: "#52e1b2",
          500: "#20c997",
          600: "#0ea972"
        }
      },
      fontFamily: {
        display: ["'Space Grotesk'", "system-ui", "sans-serif"],
        body: ["'Inter'", "system-ui", "sans-serif"]
      },
      boxShadow: {
        soft: "0 20px 50px -30px rgba(15, 23, 42, 0.45)",
        glow: "0 0 0 1px rgba(82, 225, 178, 0.25), 0 15px 45px -25px rgba(82, 225, 178, 0.45)"
      },
      backgroundImage: {
        "grid": "radial-gradient(circle at 1px 1px, rgba(148, 163, 184, 0.15) 1px, transparent 0)",
        "hero": "radial-gradient(circle at top, rgba(82, 225, 178, 0.18), transparent 55%)"
      }
    }
  },
  plugins: []
};

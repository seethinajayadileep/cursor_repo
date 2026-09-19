/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "#0B1220",
        foam: "#E8EEF7",
        mist: "#9AA8BC",
        panel: "#121A2B",
        line: "#243049",
        accent: "#3DDC97",
        accent2: "#4C8DFF",
        warn: "#F0B429",
        danger: "#F07178",
      },
      fontFamily: {
        sans: ['"DM Sans"', "Segoe UI", "sans-serif"],
        display: ['"Instrument Serif"', "Georgia", "serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(61,220,151,0.25)",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
      animation: {
        fadeUp: "fadeUp 0.35s ease-out both",
        pulseSoft: "pulseSoft 1.6s ease-in-out infinite",
        shimmer: "shimmer 2.2s linear infinite",
      },
    },
  },
  plugins: [],
};

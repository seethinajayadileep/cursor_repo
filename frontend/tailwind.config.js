/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f3f6f4",
          100: "#e2ebe6",
          200: "#c5d6cc",
          300: "#9bb5a6",
          400: "#6f917c",
          500: "#4f735e",
          600: "#3c5b4a",
          700: "#31493d",
          800: "#293c33",
          900: "#15241d",
          950: "#0a1410",
        },
        signal: {
          DEFAULT: "#d8ff3e",
          dim: "#a8c92a",
          glow: "#f0ff9a",
        },
        mist: "#e8f1ec",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "hero-grid":
          "linear-gradient(rgba(216,255,62,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(216,255,62,0.06) 1px, transparent 1px)",
        "hero-radial":
          "radial-gradient(ellipse 80% 60% at 70% 20%, rgba(216,255,62,0.18), transparent 55%), radial-gradient(ellipse 50% 40% at 15% 80%, rgba(79,115,94,0.45), transparent 50%)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseBar: {
          "0%, 100%": { transform: "scaleX(0.35)", opacity: "0.55" },
          "50%": { transform: "scaleX(1)", opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        floaty: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
      animation: {
        rise: "rise 0.7s ease-out both",
        "rise-delay": "rise 0.9s ease-out 0.12s both",
        "rise-late": "rise 1s ease-out 0.24s both",
        "pulse-bar": "pulseBar 1.6s ease-in-out infinite",
        shimmer: "shimmer 2.2s linear infinite",
        floaty: "floaty 5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

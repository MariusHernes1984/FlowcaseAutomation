import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Atea primary green (#008A00) — brand-approved accent for CTAs,
        // active states, and highlights. Shades generated around the
        // 600-step so "atea-600" matches the spec value exactly.
        atea: {
          50: "#e8f5e8",
          100: "#c7e6c7",
          200: "#97d197",
          300: "#5fb85f",
          400: "#2ea02e",
          500: "#008f00",
          600: "#008a00", // primary
          700: "#006f00",
          800: "#005400",
          900: "#003d00",
        },
        // Atea neutral grey (#4D575D) — secondary brand grey for chrome,
        // borders, and muted surfaces. Use alongside zinc for depth.
        ateaGrey: {
          50: "#f4f5f5",
          100: "#edeeee", // Atea light grey
          200: "#d5d7d9",
          300: "#abb0b3",
          400: "#7d848a",
          500: "#4d575d", // primary grey
          600: "#3f484e",
          700: "#323a3f",
          800: "#242b2f",
          900: "#171c1f",
        },
        // Atea secondary palette — approved for illustrations, charts,
        // and accent tones. Prefer atea-green for interactive elements;
        // use these for categorical coding only.
        ateaAccent: {
          yellow: "#f6bd18",
          orange: "#ec7a2e",
          red: "#d62429",
          teal: "#097288",
          purple: "#483d7c",
          blue: "#0965b1",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.06)",
        floating: "0 10px 30px -12px rgb(0 0 0 / 0.15)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-500px 0" },
          "100%": { backgroundPosition: "500px 0" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.25s ease-out",
        shimmer: "shimmer 1.5s infinite linear",
      },
    },
  },
  plugins: [],
} satisfies Config;

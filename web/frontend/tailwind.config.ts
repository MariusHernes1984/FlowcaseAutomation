import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Atea brand red used as the accent colour for primary CTAs
        // and highlight states. Everything else is zinc so the accent
        // actually stands out.
        atea: {
          50: "#fff2f3",
          100: "#ffe1e3",
          200: "#ffc7cb",
          300: "#ff9ea6",
          400: "#ff666f",
          500: "#ff2f3a",
          600: "#e30613", // primary
          700: "#c20410",
          800: "#9d0610",
          900: "#810a11",
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

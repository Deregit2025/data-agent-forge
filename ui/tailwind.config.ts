import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        forge: {
          bg:      "#080c10",
          surface: "#0f1419",
          card:    "#141c24",
          border:  "#1e2d3d",
          amber:   "#f59e0b",
          amber2:  "#fbbf24",
          green:   "#10b981",
          red:     "#ef4444",
          blue:    "#3b82f6",
          purple:  "#8b5cf6",
          text:    "#e2e8f0",
          muted:   "#64748b",
          dim:     "#334155",
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "Consolas", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in":    "fadeIn 0.5s ease-in-out",
        "slide-up":   "slideUp 0.4s ease-out",
      },
      keyframes: {
        fadeIn:  { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: { "0%": { transform: "translateY(16px)", opacity: "0" }, "100%": { transform: "translateY(0)", opacity: "1" } },
      },
    },
  },
  plugins: [],
};

export default config;

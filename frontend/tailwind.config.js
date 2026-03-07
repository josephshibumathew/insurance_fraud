/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // ── Charcoal & Sand palette ─────────────────────────────────────
        navy: {
          50:  "#F5F1EA",
          100: "#DFD0B8",
          200: "#CFC0A4",
          300: "#BEAE8E",
          400: "#AD9C7B",
          500: "#948979",
          600: "#6B6358",
          700: "#393E46",
          800: "#2D3239",
          900: "#222831",
          950: "#161B22",
        },
        fraud: {
          low:    "#06A77D",
          medium: "#FFB703",
          high:   "#D64045",
        },
        // ── Backward-compat aliases ──────────────────────────────────────
        brand: {
          navy:    "#222831",
          slate:   "#393E46",
          mist:    "#F5F1EA",
          cyan:    "#948979",
          emerald: "#06A77D",
          amber:   "#FFB703",
          danger:  "#D64045",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        soft:         "0 2px 15px -3px rgba(34,40,49,0.10), 0 10px 20px -2px rgba(34,40,49,0.06)",
        card:         "0 1px 3px rgba(34,40,49,0.08), 0 4px 12px rgba(34,40,49,0.06)",
        "card-hover": "0 4px 16px rgba(34,40,49,0.14), 0 20px 40px rgba(34,40,49,0.10)",
        nav:          "0 1px 0 rgba(34,40,49,0.10), 0 4px 16px rgba(34,40,49,0.08)",
        glow:         "0 0 0 3px rgba(148,137,121,0.35)",
        "glow-amber": "0 0 0 3px rgba(255,183,3,0.30)",
        "inner-top":  "inset 0 1px 0 rgba(255,255,255,0.1)",
      },
      backdropBlur: { xs: "2px" },
      keyframes: {
        fadeIn:    { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp:   { "0%": { opacity: "0", transform: "translateY(14px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        slideDown: { "0%": { opacity: "0", transform: "translateY(-10px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        shimmer:   { "100%": { backgroundPosition: "200% center" } },
        pulseDot:  { "0%, 100%": { opacity: "1" }, "50%": { opacity: "0.35" } },
        spinRing:  { "100%": { transform: "rotate(360deg)" } },
      },
      animation: {
        "fade-in":   "fadeIn 0.25s ease-out",
        "slide-up":  "slideUp 0.25s ease-out",
        "slide-down": "slideDown 0.2s ease-out",
        shimmer:      "shimmer 1.9s linear infinite",
        "pulse-dot":  "pulseDot 1.4s ease-in-out infinite",
        "spin-ring":  "spinRing 0.8s linear infinite",
      },
    },
  },
  plugins: [],
};

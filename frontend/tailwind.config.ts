import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand palette — traditional South Indian aesthetic.
        saffron: "#FF6B00",
        burgundy: "#8B0000",
        ivory: "#FFF8F0",
        gold: "#C9A227",
        ink: "#2A1810", // warm near-black for body text on ivory
      },
      fontFamily: {
        serif: ["var(--font-crimson)", "Crimson Pro", "Georgia", "serif"],
        sans: ["var(--font-jakarta)", "Plus Jakarta Sans", "system-ui", "sans-serif"],
      },
      letterSpacing: {
        eyebrow: "0.2em",
      },
      maxWidth: {
        prose: "65ch",
      },
      transitionTimingFunction: {
        // Spring-like easing used across the site (per high-end-visual-design).
        fluid: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
      keyframes: {
        "rise-in": {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "bar-grow": {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "rise-in": "rise-in 0.7s cubic-bezier(0.32,0.72,0,1) both",
      },
    },
  },
  plugins: [],
};

export default config;

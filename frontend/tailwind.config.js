/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111f",
        navy: "#0b1628",
        panel: "#111c31",
        panel2: "#17253d",
        line: "#2a3b5c",
        muted: "#93a4c3",
        emerald: "#3ddc97",
        signal: "#5b9dff",
        amber: "#f5b942",
        coral: "#ff6b6b",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 10px 30px rgba(2, 8, 20, 0.28)",
      },
    },
  },
  plugins: [],
};

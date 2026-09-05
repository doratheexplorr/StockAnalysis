/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        bull: "#16a34a",
        bear: "#dc2626",
      },
    },
  },
  plugins: [],
};

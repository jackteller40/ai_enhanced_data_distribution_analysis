/** @type {import('tailwindcss').Config} */
export default {
  // This tells Tailwind: "Scan every .js and .jsx file inside the src folder!"
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
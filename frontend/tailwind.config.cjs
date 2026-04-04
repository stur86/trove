/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    // Include flowbite-react component definitions so Tailwind doesn't purge their classes
    "./node_modules/flowbite-react/dist/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("flowbite/plugin"),
  ],
  darkMode: 'class', // Enable dark mode using a CSS class
}

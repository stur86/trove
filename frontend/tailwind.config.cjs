/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    // Include flowbite-react component definitions so Tailwind doesn't purge their classes
    "./node_modules/flowbite-react/dist/**/*.js",
  ],
  theme: {
    extend: {
      // Flowbite React components use `primary-*` shades for default colours
      // (e.g. fill-primary-600 on Spinner). Map to Tailwind blue.
      colors: {
        primary: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [
    require("flowbite/plugin"),
    require("@tailwindcss/typography"),
  ],
  darkMode: 'class',
}

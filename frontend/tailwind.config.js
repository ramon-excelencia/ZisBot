/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'zismed-blue': '#2563eb',
        'zismed-green': '#16a34a',
        'zismed-gray': '#64748b',
        'hospital-primary': '#1e40af',
        'hospital-secondary': '#059669',
        'chat-user': '#3b82f6',
        'chat-bot': '#e5e7eb'
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'medical': ['Source Sans Pro', 'sans-serif']
      }
    },
  },
  plugins: [],
}
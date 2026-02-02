/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#667eea',
        secondary: '#764ba2',
        success: '#10b981',
      },
      boxShadow: {
        'card': '0 10px 30px rgba(102, 126, 234, 0.1)',
      }
    },
  },
  plugins: [],
}

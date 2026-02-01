/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        thryx: {
          primary: '#6366f1',
          secondary: '#8b5cf6',
          dark: '#0f0f1a',
          card: '#1a1a2e',
          border: '#2d2d44',
        },
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#2b72c9',          // Vibrant blue
        secondary: '#2b72c9',        // Same blue for consistency
        accent: '#f15941',           // Coral/orange accent
        'background-light': '#f8fafc',
        'background-dark': '#061636', // Deep navy dark mode
        'surface-light': '#FFFFFF',
        'surface-dark': '#0d2147',   // Slightly lighter navy for surfaces
      },
      fontFamily: {
        display: ['Inter', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};

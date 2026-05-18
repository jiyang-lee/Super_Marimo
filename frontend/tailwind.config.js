/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        pixel: ['"Press Start 2P"', 'monospace'],
        dot: ['"DotGothic16"', '"Press Start 2P"', 'monospace'],
      },
      colors: {
        sky: '#7ec0ee',
        grass: '#2d7a32',
        'grass-dark': '#1b5e20',
        'grass-deeper': '#145216',
        gold: '#fdd835',
        parchment: '#fdf5e6',
        'parchment-dark': '#e8d5b0',
        dirt: '#8b6914',
        'dirt-dark': '#6b4f12',
        bark: '#5d3a1a',
        'bark-dark': '#3d2410',
        'heart-red': '#ff3d3d',
        'water-blue': '#42a5f5',
        'sun-orange': '#ffa726',
      },
    },
  },
  plugins: [],
}
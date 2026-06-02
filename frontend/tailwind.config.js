/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#E8916A',
          light: '#F0C6C0',
          pale: '#FFF3E0',
        },
        surface: {
          bg: '#FFFAF5',
          card: '#FFFFFF',
          glass: 'rgba(255,255,255,0.7)',
          warm: '#FDF2E9',
        },
        text: {
          main: '#3D3D3D',
          secondary: '#8C8C8C',
          muted: '#BFBFBF',
        },
        mood: {
          sad: '#6B7DB3',
          melancholic: '#8B7EC8',
          hopeful: '#F0C060',
          warm: '#E8916A',
          calm: '#7EC8A0',
          healing: '#5DB5A4',
          lonely: '#9B8EC4',
          nostalgic: '#C8A882',
          bittersweet: '#C4828C',
          peaceful: '#82B9C8',
        }
      },
      fontFamily: {
        sans: ['"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
      },
      backdropBlur: {
        glass: '12px',
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'note-fall': 'noteFall 2s ease-in infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.6 },
        },
        noteFall: {
          '0%': { transform: 'translateY(-20px) rotate(0deg)', opacity: 1 },
          '100%': { transform: 'translateY(40px) rotate(20deg)', opacity: 0 },
        },
      },
    },
  },
  plugins: [],
}

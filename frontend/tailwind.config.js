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
          DEFAULT: '#2F7D73',
          light: '#6FB7A8',
          pale: '#DDEFEA',
          dark: '#20564F',
        },
        accent: {
          DEFAULT: '#C95F4F',
          light: '#EF8A5B',
          pale: '#F7DED6',
        },
        surface: {
          bg: '#F7F3EC',
          card: '#FFFFFF',
          glass: 'rgba(255,255,255,0.75)',
          warm: '#EFE6D8',
          dark: '#24323D',
        },
        text: {
          main: '#24323D',
          secondary: '#5D6972',
          muted: '#8A918F',
        },
        mood: {
          sad: '#6B7DB3',
          warm: '#E8916A',
          calm: '#7EC8A0',
          happy: '#F0C060',
          intense: '#C44D4D',
          nostalgic: '#C8A882',
          mysterious: '#8B5CF6',
          energetic: '#06B6D4',
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

module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      spacing: {
        'safe': 'max(1rem, env(safe-area-inset-bottom))',
      },
      screens: {
        'xs': '320px',
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
      },
      colors: {
        'teal': {
          50: '#f0fdfc',
          500: '#14b8a6',
          600: '#0d9488',
        },
      },
      minWidth: {
        touch: '44px',
      },
      minHeight: {
        touch: '44px',
      },
    },
  },
  plugins: [],
}

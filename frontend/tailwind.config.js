/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Core brand
        primary:              '#af101a',
        'primary-dark':       '#8a0c14',
        'primary-container':  '#d32f2f',
        'primary-fixed':      '#ffdad6',
        'primary-fixed-dim':  '#ffb3ac',
        'on-primary':         '#ffffff',
        'on-primary-fixed':   '#ffffff',
        // Secondary
        secondary:            '#005faf',
        'secondary-fixed':    '#d4e3ff',
        'secondary-container':'#54a0fe',
        // Tertiary
        tertiary:             '#715300',
        'tertiary-fixed':     '#ffdfa0',
        'tertiary-fixed-dim': '#f8bd2a',
        'on-tertiary-fixed':  '#261a00',
        // Surfaces
        background:                 '#fcf9f8',
        surface:                    '#fcf9f8',
        'surface-bright':           '#fcf9f8',
        'surface-dim':              '#dcd9d9',
        'surface-container':        '#f0eded',
        'surface-container-low':    '#f6f3f2',
        'surface-container-high':   '#eae7e7',
        'surface-container-highest':'#e5e2e1',
        'surface-container-lowest': '#ffffff',
        'surface-variant':          '#e5e2e1',
        'inverse-surface':          '#303030',
        // On-surface
        'on-surface':         '#1b1b1c',
        'on-surface-variant': '#5b403d',
        // Outline
        outline:              '#8f6f6c',
        'outline-variant':    '#e4beba',
        // Errors
        error:                '#ba1a1a',
        'error-container':    '#ffdad6',
        'on-error-container': '#93000a',
        // Utility aliases
        success: '#16a34a',
        warning: '#d97706',
        danger:  '#dc2626',
        amber:   '#d97706',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],

  theme: {
    extend: {

      colors: {

        /* HR PRODUCTIVITY THEME */

        primary: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4F46E5', // MAIN BRAND
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },

        secondary: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06B6D4', // SECONDARY
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
        },

        /* DASHBOARD SURFACES */

        dashboard: {
          sidebar: '#111827',
          background: '#F9FAFB',
          card: '#FFFFFF',
          border: '#E5E7EB',
          header: '#FFFFFF'
        },

        /* ATTENDANCE STATUS COLORS */

        attendance: {
          present: '#10B981',
          absent: '#EF4444',
          late: '#F59E0B',
          overtime: '#6366F1',
          leave: '#8B5CF6',
          holiday: '#14B8A6',
          weekend: '#F97316',
        },

        /* SUCCESS */

        success: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10B981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },

        /* ERROR */

        danger: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#EF4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },

        /* WARNING */

        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#F59E0B',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },

        /* INFO */

        info: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },

        /* CHART COLORS */

        chart: {
          blue: '#6366F1',
          cyan: '#06B6D4',
          green: '#10B981',
          orange: '#F59E0B',
          red: '#EF4444',
          purple: '#8B5CF6',
          pink: '#EC4899',
        },

        /* NEUTRAL GRAYS */

        gray: {
          50: '#F9FAFB',
          100: '#F3F4F6',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#374151',
          800: '#1F2937',
          900: '#111827',
        }

      },

      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },

      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
        '88': '22rem',
        '128': '32rem',
      },

      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },

      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.05)',
        soft: '0 4px 20px rgba(0,0,0,0.06)',
        hover: '0 10px 25px rgba(0,0,0,0.08)',
      },

      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },

        slideIn: {
          '0%': { transform: 'translateX(-20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },

    },
  },

  plugins: [],
}
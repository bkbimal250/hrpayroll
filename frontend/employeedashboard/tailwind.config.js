/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],

  theme: {
    extend: {

      colors: {

        /* -------------------------------
        PRIMARY BRAND (Corporate Blue)
        --------------------------------*/

        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb', // MAIN BRAND COLOR
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },

        /* -------------------------------
        DASHBOARD UI COLORS
        --------------------------------*/

        dashboard: {
          background: '#f8fafc',  // main page bg
          card: '#ffffff',        // cards
          sidebar: '#1e293b',     // sidebar bg
          header: '#ffffff',
          border: '#e2e8f0',
        },

        /* -------------------------------
        SECONDARY (Slate System)
        --------------------------------*/

        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },

        /* -------------------------------
        ATTENDANCE STATUS COLORS
        --------------------------------*/

        attendance: {
          present: '#22c55e',
          absent: '#ef4444',
          late: '#f59e0b',
          halfday: '#8b5cf6',
          leave: '#6366f1',
        },

        /* -------------------------------
        SEMANTIC COLORS
        --------------------------------*/

        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },

        danger: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },

        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },

        info: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },

        /* -------------------------------
        CHART COLORS
        --------------------------------*/

        chart: {
          blue: '#3b82f6',
          green: '#22c55e',
          purple: '#8b5cf6',
          orange: '#f59e0b',
          red: '#ef4444',
          cyan: '#06b6d4',
        },

        /* -------------------------------
        NEUTRAL SYSTEM
        --------------------------------*/

        neutral: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        }

      },

      /* -------------------------------
      FONTS
      --------------------------------*/

      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'Noto Sans',
          'sans-serif'
        ],
      },

      /* -------------------------------
      SPACING SYSTEM
      --------------------------------*/

      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
        '88': '22rem',
        '128': '32rem',
      },

      /* -------------------------------
      BORDER RADIUS
      --------------------------------*/

      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },

      /* -------------------------------
      SHADOWS
      --------------------------------*/

      boxShadow: {
        card: '0 2px 8px rgba(0,0,0,0.05)',
        soft: '0 2px 15px rgba(0,0,0,0.06)',
        glow: '0 0 20px rgba(37,99,235,0.35)',
        sidebar: '2px 0 8px rgba(0,0,0,0.05)',
      },

    },
  },

  plugins: [],
}
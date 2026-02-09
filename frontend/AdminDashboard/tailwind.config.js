/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary Colors
        primary: {
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
          950: '#172554',
        },
        // Secondary Colors
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
          950: '#020617',
        },
        // Success Colors
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
          950: '#052e16',
        },
        // Warning Colors
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
          950: '#451a03',
        },
        // Danger Colors
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
          950: '#450a0a',
        },
        // Info Colors
        info: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          950: '#083344',
        },
        // Custom Brand Colors
        brand: {
          blue: '#3b82f6',
          indigo: '#6366f1',
          purple: '#8b5cf6',
          pink: '#ec4899',
          rose: '#f43f5e',
        },
        // Background Colors
        background: {
          primary: '#ffffff',
          secondary: '#f8fafc',
          dark: '#0f172a',
          card: '#ffffff',
          cardDark: '#1e293b',
        },
        // Text Colors
        text: {
          primary: '#0f172a',
          secondary: '#475569',
          muted: '#64748b',
          inverse: '#ffffff',
        },
        // Border Colors
        border: {
          light: '#e2e8f0',
          medium: '#cbd5e1',
          dark: '#94a3b8',
        },
        // Attendance Status Colors
        attendance: {
          present: '#22c55e',      // Green for present
          'present-light': '#dcfce7', // Light green background
          absent: '#ef4444',       // Red for absent
          'absent-light': '#fee2e2', // Light red background
          late: '#f59e0b',         // Orange for late
          'late-light': '#fef3c7', // Light orange background
          'half-day': '#8b5cf6',   // Purple for half day
          'half-day-light': '#ede9fe', // Light purple background
        },
        // Priority Colors for notifications and alerts
        priority: {
          high: '#ef4444',         // Red for high priority
          medium: '#f59e0b',       // Orange for medium priority
          low: '#22c55e',         // Green for low priority
          urgent: '#dc2626',      // Dark red for urgent
        },
        // Button Variants
        button: {
          primary: '#3b82f6',      // Blue primary
          'primary-hover': '#2563eb', // Darker blue for hover
          secondary: '#64748b',     // Grey secondary
          'secondary-hover': '#475569', // Darker grey for hover
          success: '#22c55e',      // Green for success actions
          'success-hover': '#16a34a', // Darker green for hover
          danger: '#ef4444',       // Red for danger actions
          'danger-hover': '#dc2626', // Darker red for hover
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'medium': '0 4px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        'large': '0 10px 40px -10px rgba(0, 0, 0, 0.15), 0 2px 10px -2px rgba(0, 0, 0, 0.05)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [
    
  ],
}


// /** @type {import('tailwindcss').Config} */
// module.exports = {
//   content: [
//     "./index.html",
//     "./src/**/*.{js,ts,jsx,tsx}",
//   ],
//   theme: {
//     extend: {
//       colors: {
//         // --- Custom Color Palette based on 5 colors ---
//         // Brand/Primary colors for headers and logos
//         brand: {
//           blue: '#2C3E50',     // Deep Blue / Slate
//           charcoal: '#34495E', // Dark Charcoal
//           teal: '#1ABC9C',     // Accent Teal / Aqua
//         },
//         // Background colors for overall layout and sections
//         background: {
//           primary: '#F2F4F5',  // Clean Light Grey (Main page background)
//           secondary: '#5D6D7E', // Soft Grey-Blue (Secondary panels, sidebars)
//         },
//         // Text colors for readability and hierarchy
//         text: {
//           primary: '#34495E',   // Dark Charcoal (Main text, headings)
//           secondary: '#5D6D7E', // Soft Grey-Blue (Secondary text, captions)
//           inverse: '#FFFFFF'     // White text for dark backgrounds
//         },
//         // Button colors for interactive elements and actions
//         button: {
//           primary: '#1ABC9C',    // Accent Teal (Main button color)
//           // A slightly darker shade of teal for a professional hover effect
//           hover: '#16997C',
//         },
//       },
//       fontFamily: {
//         sans: ['Inter', 'system-ui', 'sans-serif'],
//         mono: ['JetBrains Mono', 'monospace'],
//       },
//       boxShadow: {
//         'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
//         'medium': '0 4px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
//         'large': '0 10px 40px -10px rgba(0, 0, 0, 0.15), 0 2px 10px -2px rgba(0, 0, 0, 0.05)',
//       },
//       animation: {
//         'fade-in': 'fadeIn 0.5s ease-in-out',
//         'slide-up': 'slideUp 0.3s ease-out',
//         'slide-down': 'slideDown 0.3s ease-out',
//         'scale-in': 'scaleIn 0.2s ease-out',
//       },
//       keyframes: {
//         fadeIn: {
//           '0%': { opacity: '0' },
//           '100%': { opacity: '1' },
//         },
//         slideUp: {
//           '0%': { transform: 'translateY(10px)', opacity: '0' },
//           '100%': { transform: 'translateY(0)', opacity: '1' },
//         },
//         slideDown: {
//           '0%': { transform: 'translateY(-10px)', opacity: '0' },
//           '100%': { transform: 'translateY(0)', opacity: '1' },
//         },
//         scaleIn: {
//           '0%': { transform: 'scale(0.95)', opacity: '0' },
//           '100%': { transform: 'scale(1)', opacity: '1' },
//         },
//       },
//     },
//   },
//   plugins: [
//   ],
// }
# Tailwind CSS Setup for Employee Dashboard

## Overview
This document explains how Tailwind CSS is configured and used in the Employee Dashboard project.

## Installation
Tailwind CSS has been installed with the following packages:
- `tailwindcss` - Core Tailwind CSS framework
- `postcss` - CSS processing tool
- `autoprefixer` - Vendor prefix automation

## Configuration Files

### 1. tailwind.config.js
The main Tailwind configuration file that includes:
- Content paths for JIT compilation
- Custom color palette (primary and secondary colors)
- Custom font family (Inter)
- Extended spacing, border radius, and shadow utilities
- Custom component classes

### 2. postcss.config.js
PostCSS configuration for processing Tailwind CSS directives.

### 3. src/index.css
Main CSS file with:
- Tailwind directives (`@tailwind base`, `@tailwind components`, `@tailwind utilities`)
- Google Fonts import (Inter)
- Custom component classes using `@layer components`
- Base styles using `@layer base`

## Custom Component Classes

The following custom classes are available throughout the application:

### Buttons
- `.btn-primary` - Primary button styling
- `.btn-secondary` - Secondary button styling

### Cards
- `.card` - Standard card container with shadow and border

### Form Elements
- `.input-field` - Standard input field styling

### Navigation
- `.sidebar-link` - Sidebar navigation link
- `.sidebar-link.active` - Active sidebar link

## Usage Examples

### Basic Layout
```jsx
<div className="min-h-screen bg-gray-50">
  <header className="bg-white shadow-sm border-b border-gray-200">
    {/* Header content */}
  </header>
  <main className="max-w-7xl mx-auto py-6 px-4">
    {/* Main content */}
  </main>
</div>
```

### Grid Layouts
```jsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {/* Responsive grid items */}
</div>
```

### Cards
```jsx
<div className="card hover:shadow-lg transition-shadow duration-200">
  <h3 className="text-lg font-medium text-gray-900 mb-4">Card Title</h3>
  {/* Card content */}
</div>
```

### Buttons
```jsx
<button className="btn-primary">Primary Action</button>
<button className="btn-secondary">Secondary Action</button>
```

## Custom Colors

### Primary Colors
- `primary-50` to `primary-900` - Blue color palette
- Used for primary actions, links, and highlights

### Secondary Colors
- `secondary-50` to `secondary-900` - Gray color palette
- Used for secondary elements and text

## Responsive Design

The dashboard uses Tailwind's responsive prefixes:
- `sm:` - Small screens (640px+)
- `md:` - Medium screens (768px+)
- `lg:` - Large screens (1024px+)
- `xl:` - Extra large screens (1280px+)

## Custom Utilities

### Shadows
- `.shadow-soft` - Soft shadow for cards
- `.shadow-glow` - Glowing shadow effect

### Spacing
- Custom spacing values: `18`, `88`, `128`

### Border Radius
- Extended border radius: `xl`, `2xl`

## Development Workflow

1. **Adding new styles**: Use Tailwind utility classes directly in JSX
2. **Custom components**: Add to `src/index.css` using `@layer components`
3. **Custom utilities**: Add to `src/index.css` using `@layer utilities`
4. **Theme customization**: Modify `tailwind.config.js`

## Best Practices

1. **Use utility classes first**: Leverage Tailwind's utility-first approach
2. **Component extraction**: Create reusable components for repeated patterns
3. **Responsive design**: Always consider mobile-first responsive design
4. **Consistent spacing**: Use Tailwind's spacing scale consistently
5. **Accessibility**: Ensure proper contrast ratios and focus states

## Troubleshooting

### Styles not applying
- Check if Tailwind is properly imported in `index.css`
- Verify `tailwind.config.js` content paths
- Ensure PostCSS is processing the CSS

### Build issues
- Clear node_modules and reinstall dependencies
- Check PostCSS configuration
- Verify Tailwind version compatibility

## Additional Resources

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Tailwind CSS Components](https://tailwindui.com/)
- [Tailwind CSS Cheat Sheet](https://nerdcave.com/tailwind-cheat-sheet)

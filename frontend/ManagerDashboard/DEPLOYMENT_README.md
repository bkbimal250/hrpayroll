# 🚀 Deployment Guide

Comprehensive deployment guide for the Employee Attendance Manager Dashboard in production environments.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Build Configuration](#build-configuration)
- [Deployment Options](#deployment-options)
- [Production Configuration](#production-configuration)
- [Security Considerations](#security-considerations)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements
- **Node.js**: 16.x or higher
- **npm**: 8.x or higher
- **Web Server**: Nginx, Apache, or similar
- **SSL Certificate**: For HTTPS deployment
- **Domain**: Production domain name

### Backend Requirements
- **Django Backend**: API server running
- **Database**: PostgreSQL, MySQL, or SQLite
- **WebSocket Server**: For real-time features
- **Redis**: For caching and session storage (optional)

### Development Tools
- **Git**: Version control
- **CI/CD**: GitHub Actions, GitLab CI, or similar
- **Container Platform**: Docker (optional)

## 🌍 Environment Setup

### 1. Environment Variables

Create a `.env.production` file:

```env
# API Configuration
VITE_API_BASE_URL=https://api.yourcompany.com/api
VITE_WEBSOCKET_URL=wss://api.yourcompany.com/ws/attendance/

# Authentication
VITE_JWT_SECRET=your-production-jwt-secret
VITE_REFRESH_TOKEN_SECRET=your-refresh-token-secret

# Feature Flags
VITE_ENABLE_WEBSOCKET=true
VITE_ENABLE_NOTIFICATIONS=true
VITE_ENABLE_OFFLINE_MODE=false
VITE_ENABLE_ANALYTICS=true

# Performance
VITE_ENABLE_CACHING=true
VITE_CACHE_DURATION=300000
VITE_REQUEST_TIMEOUT=30000

# Security
VITE_ENABLE_CSP=true
VITE_ENABLE_HSTS=true
VITE_SESSION_TIMEOUT=3600000

# Monitoring
VITE_ENABLE_ERROR_TRACKING=true
VITE_SENTRY_DSN=your-sentry-dsn
VITE_GOOGLE_ANALYTICS_ID=your-ga-id
```

### 2. Build Configuration

Update `vite.config.js` for production:

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          charts: ['chart.js', 'react-chartjs-2'],
          pdf: ['jspdf', 'jspdf-autotable'],
          ui: ['lucide-react']
        }
      }
    },
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  },
  server: {
    port: 5173,
    host: true
  },
  preview: {
    port: 4173,
    host: true
  }
});
```

### 3. Package.json Scripts

Update `package.json` with production scripts:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "build:prod": "NODE_ENV=production vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint . --ext js,jsx --fix",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "analyze": "vite-bundle-analyzer",
    "clean": "rm -rf dist node_modules/.vite"
  }
}
```

## 🏗️ Build Configuration

### 1. Production Build

```bash
# Install dependencies
npm ci --only=production

# Create production build
npm run build:prod

# Verify build
npm run preview
```

### 2. Build Optimization

#### Code Splitting
```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          charts: ['chart.js', 'react-chartjs-2'],
          pdf: ['jspdf', 'jspdf-autotable'],
          ui: ['lucide-react']
        }
      }
    }
  }
});
```

#### Bundle Analysis
```bash
# Install bundle analyzer
npm install --save-dev vite-bundle-analyzer

# Analyze bundle
npm run analyze
```

### 3. Asset Optimization

#### Image Optimization
```javascript
// vite.config.js
import { defineConfig } from 'vite';
import { ViteImageOptimize } from 'vite-plugin-imagemin';

export default defineConfig({
  plugins: [
    ViteImageOptimize({
      gifsicle: { optimizationLevel: 7 },
      mozjpeg: { quality: 80 },
      pngquant: { quality: [0.65, 0.8] },
      svgo: {
        plugins: [
          { name: 'removeViewBox', active: false },
          { name: 'removeEmptyAttrs', active: false }
        ]
      }
    })
  ]
});
```

## 🚀 Deployment Options

### Option 1: Static Hosting (Recommended)

#### Vercel Deployment
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to Vercel
vercel --prod

# Configure environment variables in Vercel dashboard
```

#### Netlify Deployment
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Build and deploy
npm run build
netlify deploy --prod --dir=dist

# Configure environment variables in Netlify dashboard
```

#### GitHub Pages
```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run build
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./dist
```

### Option 2: Docker Deployment

#### Dockerfile
```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: .
    ports:
      - "80:80"
    environment:
      - VITE_API_BASE_URL=https://api.yourcompany.com/api
    depends_on:
      - backend

  backend:
    image: your-backend-image
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/attendance
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=attendance
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### Nginx Configuration
```nginx
# nginx.conf
server {
    listen 80;
    server_name your-domain.com;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Handle client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass https://api.yourcompany.com;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass https://api.yourcompany.com;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option 3: Cloud Platform Deployment

#### AWS S3 + CloudFront
```bash
# Install AWS CLI
npm install -g @aws-cli/cli

# Build and upload to S3
npm run build
aws s3 sync dist/ s3://your-bucket-name --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

#### Google Cloud Storage
```bash
# Install Google Cloud CLI
curl https://sdk.cloud.google.com | bash

# Build and upload
npm run build
gsutil -m rsync -r -d dist/ gs://your-bucket-name
```

#### Azure Static Web Apps
```yaml
# .github/workflows/azure-static-web-apps.yml
name: Azure Static Web Apps CI/CD

on:
  push:
    branches: [ main ]

jobs:
  build_and_deploy_job:
    runs-on: ubuntu-latest
    name: Build and Deploy Job
    steps:
      - uses: actions/checkout@v2
      - name: Build And Deploy
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "/"
          output_location: "dist"
```

## ⚙️ Production Configuration

### 1. Environment-Specific Configuration

#### Development
```javascript
// config/development.js
export const config = {
  apiBaseUrl: 'http://localhost:8000/api',
  websocketUrl: 'ws://localhost:8000/ws/attendance/',
  enableDebug: true,
  enableHotReload: true
};
```

#### Production
```javascript
// config/production.js
export const config = {
  apiBaseUrl: 'https://api.yourcompany.com/api',
  websocketUrl: 'wss://api.yourcompany.com/ws/attendance/',
  enableDebug: false,
  enableHotReload: false,
  enableAnalytics: true
};
```

### 2. Performance Optimization

#### Service Worker
```javascript
// public/sw.js
const CACHE_NAME = 'attendance-dashboard-v1';
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});
```

#### PWA Configuration
```json
// public/manifest.json
{
  "name": "Employee Attendance Dashboard",
  "short_name": "Attendance",
  "description": "Employee attendance management system",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#3b82f6",
  "icons": [
    {
      "src": "/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### 3. Security Configuration

#### Content Security Policy
```html
<!-- index.html -->
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  connect-src 'self' https://api.yourcompany.com wss://api.yourcompany.com;
  font-src 'self' data:;
">
```

#### Security Headers
```javascript
// vite.config.js
export default defineConfig({
  server: {
    headers: {
      'X-Frame-Options': 'SAMEORIGIN',
      'X-Content-Type-Options': 'nosniff',
      'X-XSS-Protection': '1; mode=block',
      'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }
  }
});
```

## 🔒 Security Considerations

### 1. Authentication Security
- Use HTTPS for all communications
- Implement JWT token expiration
- Use secure cookie settings
- Implement CSRF protection

### 2. Data Protection
- Encrypt sensitive data in transit
- Use secure API endpoints
- Implement proper CORS policies
- Validate all user inputs

### 3. Infrastructure Security
- Use WAF (Web Application Firewall)
- Implement DDoS protection
- Regular security updates
- Monitor for vulnerabilities

## 📊 Monitoring & Logging

### 1. Error Tracking

#### Sentry Integration
```javascript
// src/utils/sentry.js
import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';

Sentry.init({
  dsn: process.env.VITE_SENTRY_DSN,
  integrations: [
    new BrowserTracing(),
  ],
  tracesSampleRate: 1.0,
  environment: process.env.NODE_ENV,
});
```

#### Custom Error Handler
```javascript
// src/utils/errorHandler.js
export const errorHandler = (error, errorInfo) => {
  console.error('Application Error:', error);
  
  // Send to monitoring service
  if (window.Sentry) {
    window.Sentry.captureException(error, {
      contexts: {
        react: errorInfo
      }
    });
  }
};
```

### 2. Performance Monitoring

#### Web Vitals
```javascript
// src/utils/analytics.js
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function sendToAnalytics(metric) {
  // Send to your analytics service
  console.log(metric);
}

getCLS(sendToAnalytics);
getFID(sendToAnalytics);
getFCP(sendToAnalytics);
getLCP(sendToAnalytics);
getTTFB(sendToAnalytics);
```

### 3. Logging Configuration

#### Log Levels
```javascript
// src/utils/logger.js
const LOG_LEVELS = {
  ERROR: 0,
  WARN: 1,
  INFO: 2,
  DEBUG: 3
};

class Logger {
  constructor(level = LOG_LEVELS.INFO) {
    this.level = level;
  }

  error(message, ...args) {
    if (this.level >= LOG_LEVELS.ERROR) {
      console.error(`[ERROR] ${message}`, ...args);
    }
  }

  warn(message, ...args) {
    if (this.level >= LOG_LEVELS.WARN) {
      console.warn(`[WARN] ${message}`, ...args);
    }
  }

  info(message, ...args) {
    if (this.level >= LOG_LEVELS.INFO) {
      console.info(`[INFO] ${message}`, ...args);
    }
  }

  debug(message, ...args) {
    if (this.level >= LOG_LEVELS.DEBUG) {
      console.debug(`[DEBUG] ${message}`, ...args);
    }
  }
}

export default new Logger(
  process.env.NODE_ENV === 'development' ? LOG_LEVELS.DEBUG : LOG_LEVELS.INFO
);
```

## 🧪 Testing in Production

### 1. Health Checks
```javascript
// src/utils/healthCheck.js
export const healthCheck = async () => {
  try {
    const response = await fetch('/api/health/');
    return response.ok;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
};

// Run health check every 30 seconds
setInterval(healthCheck, 30000);
```

### 2. Feature Flags
```javascript
// src/utils/featureFlags.js
export const featureFlags = {
  enableWebSocket: process.env.VITE_ENABLE_WEBSOCKET === 'true',
  enableNotifications: process.env.VITE_ENABLE_NOTIFICATIONS === 'true',
  enableAnalytics: process.env.VITE_ENABLE_ANALYTICS === 'true',
  enableOfflineMode: process.env.VITE_ENABLE_OFFLINE_MODE === 'true'
};
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### 2. CORS Issues
```javascript
// Check API configuration
const API_BASE_URL = process.env.VITE_API_BASE_URL;
console.log('API Base URL:', API_BASE_URL);

// Test API connection
fetch(`${API_BASE_URL}/health/`)
  .then(response => console.log('API Status:', response.status))
  .catch(error => console.error('API Error:', error));
```

#### 3. WebSocket Connection Issues
```javascript
// Check WebSocket connection
const ws = new WebSocket(process.env.VITE_WEBSOCKET_URL);
ws.onopen = () => console.log('WebSocket connected');
ws.onerror = (error) => console.error('WebSocket error:', error);
ws.onclose = () => console.log('WebSocket disconnected');
```

#### 4. Performance Issues
```bash
# Analyze bundle size
npm run analyze

# Check for memory leaks
# Use Chrome DevTools Memory tab
# Monitor heap usage over time
```

### Debug Commands
```bash
# Check environment variables
npm run build -- --mode production

# Test production build locally
npm run preview

# Check bundle size
npm run analyze

# Run linting
npm run lint

# Run tests
npm test
```

## 📚 Additional Resources

### Documentation Links
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)
- [React Production Build](https://react.dev/learn/start-a-new-react-project)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### Monitoring Tools
- [Sentry](https://sentry.io/) - Error tracking
- [Google Analytics](https://analytics.google.com/) - User analytics
- [New Relic](https://newrelic.com/) - Performance monitoring
- [DataDog](https://www.datadoghq.com/) - Infrastructure monitoring

---

**🎉 Your Employee Attendance Manager Dashboard is now ready for production!**

For additional support, refer to the [Main README](./README.md) or contact the development team.

# API Troubleshooting Guide

## 🚨 Current Issues Identified

Based on your console errors, you're experiencing:

1. **CORS Policy Errors**: Server sending multiple `Access-Control-Allow-Origin` headers (`http://localhost:5173, *`)
2. **Redirect Loops**: `/dashboard/stats/` endpoint causing `ERR_TOO_MANY_REDIRECTS`
3. **Network Failures**: Even successful responses (200 OK) marked as failed due to CORS blocking

## 🔧 Solutions Implemented

### 1. Enhanced API Configuration (`src/services/api.js`)

- Added `maxRedirects: 0` to prevent redirect loops
- Added `withCredentials: false` for CORS compatibility
- Enhanced error logging with specific error type detection
- Added `testConnection()` method for debugging

### 2. Debug Tools Added

- **API Debug Panel** on Dashboard with 5 test buttons
- **Comprehensive error logging** with specific error types
- **CORS testing utilities** to identify server configuration issues

### 3. Enhanced Error Handling

- Better network error detection
- Redirect loop detection
- Detailed error information and suggestions

## 🧪 How to Use Debug Tools

### Step 1: Open Dashboard
Navigate to your Dashboard page where you'll see a yellow debug panel.

### Step 2: Run Tests (in order)
1. **Test API** - Basic connection test
2. **Test CORS** - CORS preflight test
3. **Compare** - Fetch vs Axios comparison
4. **Test URLs** - Test different API URL configurations
5. **CORS Config** - Detailed CORS configuration test

### Step 3: Check Console
Open browser console (F12) to see detailed test results and error information.

## 🎯 Root Cause & Server-Side Fix

The main issue is **server-side CORS configuration**. Your Django backend is sending:

```
Access-Control-Allow-Origin: http://localhost:5173, *
```

This is **invalid** - only one origin value is allowed per header.

### Django Backend Fix Required:

```python
# In your Django settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    # Add other allowed origins
]

# Remove any duplicate CORS middleware
# Ensure only ONE CORS middleware is active

# If using django-cors-headers, make sure it's configured correctly
CORS_ALLOW_CREDENTIALS = False  # Set to False for your use case
CORS_ALLOW_ALL_ORIGINS = False  # Don't use this with CORS_ALLOWED_ORIGINS
```

## 🔍 Immediate Testing Steps

### 1. Test Current Setup
```javascript
// In browser console
import { debugApiConnection } from './src/utils/apiDebug.js';
await debugApiConnection();
```

### 2. Test CORS Headers
```javascript
// In browser console
import { testCorsPreflight } from './src/utils/apiUrlTest.js';
await testCorsPreflight();
```

### 3. Check Network Tab
- Open DevTools → Network tab
- Look for failed requests
- Check response headers for CORS issues

## 🚀 Quick Fixes to Try

### Option 1: Environment Variable Override
Create `.env.local` file:
```env
VITE_API_BASE_URL=https://company.d0s369.co.in/api
```

### Option 2: Use HTTP instead of HTTPS
```javascript
// In api.js, temporarily change to:
const API_BASE_URL = 'http://company.d0s369.co.in/api';
```

### Option 3: Proxy Configuration (Vite)
Add to `vite.config.js`:
```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'https://company.d0s369.co.in',
        changeOrigin: true,
        secure: false
      }
    }
  }
});
```

## 📋 Debug Checklist

- [ ] Run all 5 debug tests
- [ ] Check console for specific error types
- [ ] Verify server CORS configuration
- [ ] Test with different API URLs
- [ ] Check network tab for failed requests
- [ ] Verify authentication tokens are valid

## 🆘 If Issues Persist

1. **Check server logs** for CORS-related errors
2. **Verify Django CORS middleware** configuration
3. **Test API endpoints** directly with Postman/curl
4. **Check server firewall/proxy** settings
5. **Verify SSL certificate** if using HTTPS

## 📞 Next Steps

1. **Immediate**: Use debug tools to gather detailed error information
2. **Short-term**: Apply client-side fixes (proxy, HTTP, etc.)
3. **Long-term**: Fix server-side CORS configuration
4. **Testing**: Verify all endpoints work after fixes

## 🔗 Useful Resources

- [MDN CORS Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Django CORS Headers](https://github.com/adamchainz/django-cors-headers)
- [Axios CORS Configuration](https://axios-http.com/docs/req_config)

---

**Note**: The debug tools will help identify the exact nature of your CORS issues. Run them first to get detailed information before applying fixes.

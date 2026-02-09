# Hostinger Deployment Guide

##  Quick Deployment Steps for Hostinger

### **1. Upload Files to Hostinger**

#### **Manager Dashboard:**
1. Upload all files from `frontend/ManagerDashboard/dist/` to your domain root
2. The `.htaccess` file is already included and configured

#### **Employee Dashboard:**
1. Upload all files from `frontend/employeedashboard/dist/` to your subdomain
2. The `.htaccess` file is already included and configured

#### **Admin Dashboard:**
1. Upload all files from `frontend/AdminDashboard/dist/` to your subdomain
2. The `.htaccess` file is already included and configured

### **2. File Structure on Hostinger**

```
public_html/
├── index.html (Manager Dashboard)
├── .htaccess
├── assets/
│   ├── index-BbWYAjxf.js
│   └── index-CBwUF6F2.css
├── companylogo.png
└── vite.svg
```

### **3. What the .htaccess File Does**

 **Fixes MIME Type Issues:**
- Sets correct MIME types for CSS (`text/css`) and JS (`application/javascript`)
- Prevents the "text/html" MIME type error

 **Handles Static Assets:**
- Serves CSS and JS files with proper headers
- Enables compression for faster loading
- Sets cache headers for better performance

 **API Proxy:**
- Routes `/api/` requests to `https://company.d0s369.co.in/api/`
- Handles CORS properly

 **SPA Routing:**
- Redirects all non-asset requests to `index.html`
- Enables client-side routing for React Router

### **4. Common Hostinger Issues & Solutions**

#### **Issue: 403 Forbidden Error**
**Solution:** Check file permissions in Hostinger File Manager
- Right-click on files → Properties → Set permissions to 644
- Set folder permissions to 755

#### **Issue: MIME Type Errors**
**Solution:** The `.htaccess` file fixes this automatically
- If still having issues, contact Hostinger support to enable mod_mime

#### **Issue: API Requests Not Working**
**Solution:** Ensure mod_rewrite is enabled
- Contact Hostinger support to enable mod_rewrite module

### **5. Testing Your Deployment**

1. **Check CSS Loading:**
   ```
   https://dosmanagers.dishaonlinesolution.in/assets/index-CBwUF6F2.css
   ```
   Should return CSS content with `Content-Type: text/css`

2. **Check JS Loading:**
   ```
   https://dosmanagers.dishaonlinesolution.in/assets/index-BbWYAjxf.js
   ```
   Should return JavaScript content with `Content-Type: application/javascript`

3. **Test API Proxy:**
   ```
   https://dosmanagers.dishaonlinesolution.in/api/auth/login/
   ```
   Should proxy to the backend API

### **6. Performance Optimizations**

The `.htaccess` file includes:
-  Gzip compression
-  Browser caching (1 year for static assets)
-  Security headers
-  Proper MIME types

### **7. Troubleshooting**

#### **If CSS/JS still not loading:**
1. Check Hostinger error logs
2. Verify file permissions (644 for files, 755 for folders)
3. Ensure mod_rewrite is enabled
4. Contact Hostinger support if needed

#### **If API calls fail:**
1. Check if mod_proxy is enabled
2. Verify the backend API is accessible
3. Check CORS settings

### **8. Support**

If you encounter issues:
1. Check Hostinger error logs
2. Verify all files are uploaded correctly
3. Contact Hostinger support for server configuration issues

##  Ready for Deployment!

Your applications are now ready to be deployed on Hostinger with proper configuration!

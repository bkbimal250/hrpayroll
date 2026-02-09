# Hostinger Upload Guide - Complete File List

##  Ready-to-Upload Packages

### **1. Manager Dashboard** 
**Upload to:** `dosmanagers.dishaonlinesolution.in` (domain root)

**Files to upload from:** `frontend/ManagerDashboard/dist/`

```
📁 Upload ALL these files to your domain root:
├── 📄 index.html
├── 📄 .htaccess
├── 📄 web.config (backup)
├── 📁 assets/
│   ├── 📄 index-BbWYAjxf.js
│   └── 📄 index-CBwUF6F2.css
├── 🖼️ companylogo.png
└── 🖼️ vite.svg
```

### **2. Employee Dashboard**
**Upload to:** Your employee subdomain

**Files to upload from:** `frontend/employeedashboard/dist/`

```
📁 Upload ALL these files to your subdomain root:
├── 📄 index.html
├── 📄 .htaccess
├── 📁 assets/
│   ├── 📄 Attendance-DQnTPiB-.js
│   ├── 📄 Dashboard-CY7prRRP.js
│   ├── 📄 DashboardLayout-3t9D2c0T.js
│   ├── 📄 Documents-DSyssaIS.js
│   ├── 📄 index-B1gzG4CJ.css
│   ├── 📄 index-CXn7hWRx.js
│   ├── 📄 Leaves-BWbT4oHR.js
│   ├── 📄 Login-C_CCy6CL.js
│   ├── 📄 PageHeader-DhkNqo1d.js
│   ├── 📄 Profile-MtOVbNsi.js
│   ├── 📄 Resignations-A9gdj-1F.js
│   ├── 📄 StatsCard-D68SSIen.js
│   ├── 📄 ToastProvider-Ce0Vfum4.js
│   ├── 📄 ui--leQwODY.js
│   ├── 📄 usePagination-C9eFtMJH.js
│   ├── 📄 utils-DZIQhO2a.js
│   └── 📄 vendor-CtPCxZU4.js
├── 🖼️ companylogo.png
└── 🖼️ vite.svg
```

### **3. Admin Dashboard**
**Upload to:** Your admin subdomain

**Files to upload from:** `frontend/AdminDashboard/dist/`

```
📁 Upload ALL these files to your subdomain root:
├── 📄 index.html
├── 📄 .htaccess
├── 📁 assets/
│   ├── 📄 html2canvas.esm-B0tyYwQk.js
│   ├── 📄 index-BlYg7USM.css
│   ├── 📄 index-Dm9mx8l3.js
│   ├── 📄 index.es-DTynRzde.js
│   ├── 📄 jspdf.es.min-DYBo2wVU.js
│   ├── 📄 jspdf.plugin.autotable-DZlIrCiz.js
│   └── 📄 purify.es-CQJ0hv7W.js
├── 🖼️ companylogo.png
└── 🖼️ vite.svg
```

## 📋 Upload Instructions

### **Step 1: Access Hostinger File Manager**
1. Login to your Hostinger control panel
2. Go to "File Manager"
3. Navigate to your domain's `public_html` folder

### **Step 2: Upload Files**
1. **For Manager Dashboard:**
   - Upload ALL files from `frontend/ManagerDashboard/dist/` to `public_html/`
   - Make sure `.htaccess` file is uploaded (not `.htaccess.txt`)

2. **For Employee Dashboard:**
   - Create a subdomain folder (e.g., `employee/`)
   - Upload ALL files from `frontend/employeedashboard/dist/` to that folder

3. **For Admin Dashboard:**
   - Create a subdomain folder (e.g., `admin/`)
   - Upload ALL files from `frontend/AdminDashboard/dist/` to that folder

### **Step 3: Set File Permissions**
1. Right-click on `.htaccess` → Properties → Set to **644**
2. Right-click on `index.html` → Properties → Set to **644**
3. Right-click on `assets/` folder → Properties → Set to **755**
4. Right-click on CSS/JS files → Properties → Set to **644**

##  What Each File Does

### **Essential Files:**
- **`index.html`** - Main application entry point
- **`.htaccess`** - Fixes MIME type errors and handles routing
- **`assets/`** - Contains CSS and JavaScript files
- **`companylogo.png`** - Company logo
- **`vite.svg`** - Vite icon

### **Backup Files:**
- **`web.config`** - Alternative configuration for IIS servers

## 🔧 Troubleshooting

### **If you still get MIME type errors:**
1. Verify `.htaccess` file is uploaded correctly
2. Check file permissions (644 for files, 755 for folders)
3. Contact Hostinger support to enable `mod_rewrite`

### **If you get 403 errors:**
1. Check file permissions
2. Ensure all files are uploaded
3. Verify folder structure matches exactly

##  Expected Result

After uploading, your applications should:
-  Load without console errors
-  CSS files load with correct MIME type
-  JavaScript files load without 403 errors
-  API calls work properly
-  React Router navigation works

## 📞 Support

If you encounter issues:
1. Check the troubleshooting guide
2. Verify all files are uploaded
3. Contact Hostinger support if needed

**All files are ready for upload!** 

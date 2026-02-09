# API Debugging Guide

## ✅ Backend API Status
The backend API is working perfectly:
- ✅ Django server running on port 8000
- ✅ Login endpoint working
- ✅ Dashboard stats endpoint working
- ✅ Users endpoint working
- ✅ Offices endpoint working

## 🔍 Frontend Issues to Check

### 1. React Development Server
Make sure the React dev server is running:
```bash
cd frontend/accountdashboard
npm run dev
```

### 2. API Base URL
Check if the API base URL is correct in `src/services/api.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000/api';
```

### 3. CORS Configuration
The Django CORS settings should allow all origins in development mode.

### 4. Browser Console
Open browser developer tools and check:
- Network tab for failed requests
- Console for error messages
- Application tab for localStorage

### 5. Test Files Created
- `test-api-endpoints.html` - Direct API testing
- `debug-frontend-api.html` - Frontend API debugging
- `test-api-direct.py` - Python API testing

## 🚀 Quick Test Steps

1. **Test Backend API**:
   ```bash
   python test-api-direct.py
   ```

2. **Test Frontend API**:
   - Open `debug-frontend-api.html` in browser
   - Click "Test Login" with credentials: `sejalmisal` / `Dos@2026`
   - Click "Test Dashboard Stats"

3. **Test React App**:
   - Open React app in browser (usually http://localhost:5173)
   - Open browser console
   - Try to login
   - Check console for API call logs

## 🔧 Common Issues

### Issue 1: CORS Errors
**Solution**: Check Django CORS settings in `attendance_system/settings.py`

### Issue 2: Network Errors
**Solution**: Ensure both Django (port 8000) and React (port 5173) servers are running

### Issue 3: Authentication Issues
**Solution**: Check localStorage for tokens and user data

### Issue 4: API Endpoint Errors
**Solution**: Verify endpoint URLs and request format

## 📊 Expected API Response Format

### Login Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "585e81ef-f333-4511-b523-da7a668dc1eb",
    "username": "sejalmisal",
    "role": "accountant",
    "full_name": "Sejal Misal"
  }
}
```

### Dashboard Stats Response (for Accountant):
```json
{
  "total_employees": 1,
  "total_managers": 0,
  "total_offices": 1,
  "total_devices": 0,
  "active_devices": 0,
  "today_attendance": 0,
  "total_today_records": 0,
  "attendance_rate": 0,
  "pending_leaves": 0,
  "approved_leaves": 0,
  "total_leaves": 0,
  "leave_approval_rate": 0,
  "active_users": 1
}
```

## 🎯 Next Steps

1. Run the test files to identify the exact issue
2. Check browser console for error messages
3. Verify server configurations
4. Test API endpoints individually

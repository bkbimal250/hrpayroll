# Data Loading Troubleshooting Guide

## 🚨 **Issue: Login Works but Data Not Showing**

### **Step 1: Check Browser Console**
1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Look for API request/response logs
4. Check for any error messages

### **Step 2: Use Debug Tools**
1. Login to the dashboard
2. If you see errors, debug tools will appear automatically
3. Use the "Data Structure Debugger" to analyze API responses
4. Check the "Token Tester" for authentication issues

### **Step 3: Manual API Testing**
1. Open `test-auth.html` in your browser
2. Click "Test Login" to verify authentication
3. Use individual test buttons for each API endpoint
4. Check the console for detailed response information

## 🔍 **Common Issues and Solutions**

### **Issue 1: Empty Data Arrays**
**Symptoms**: API calls succeed but return empty arrays
**Solution**: 
- Check if there's actual data in the database
- Verify user permissions for accountant role
- Check if the user has access to the data

### **Issue 2: 401 Unauthorized Errors**
**Symptoms**: API calls fail with 401 status
**Solution**:
- Token might be expired - check Token Tester
- Clear browser storage and login again
- Verify credentials are correct

### **Issue 3: 403 Forbidden Errors**
**Symptoms**: API calls fail with 403 status
**Solution**:
- Accountant role might not have proper permissions
- Check backend role permissions
- Verify user is assigned to correct role

### **Issue 4: Network Errors**
**Symptoms**: API calls fail with network errors
**Solution**:
- Check internet connection
- Verify server is accessible: `https://dosapi.attendance.dishaonliesolution.workspa.in`
- Check if server is running

### **Issue 5: Data Structure Mismatch**
**Symptoms**: Data loads but doesn't display correctly
**Solution**:
- Check console logs for data structure
- Use Data Structure Debugger to analyze responses
- Verify data format matches expected structure

## 🧪 **Testing Steps**

### **1. Authentication Test**
```javascript
// Test in browser console
const token = localStorage.getItem('authToken');
console.log('Token:', token ? 'Present' : 'Missing');

// Test token validity
fetch('https://dosapi.attendance.dishaonliesolution.workspa.in/api/auth/profile/', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(console.log);
```

### **2. API Endpoint Test**
```javascript
// Test users endpoint
fetch('https://dosapi.attendance.dishaonliesolution.workspa.in/api/users/', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` }
})
.then(r => r.json())
.then(console.log);
```

### **3. Data Structure Analysis**
Look for these patterns in console logs:
- `👥 Users data structure:` - Shows raw API response
- `👥 Users data type:` - Shows if it's object/array
- `👥 Users data keys:` - Shows object keys
- `✅ Users data:` - Shows processed data

## 📊 **Expected Data Structures**

### **Users API Response**
```json
{
  "results": [
    {
      "id": "uuid",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "role": "employee",
      "office": { "id": "uuid", "name": "Main Office" }
    }
  ]
}
```

### **Attendance API Response**
```json
{
  "results": [
    {
      "id": "uuid",
      "user": { "id": "uuid", "first_name": "John", "last_name": "Doe" },
      "date": "2024-01-15",
      "status": "present",
      "check_in_time": "2024-01-15T09:00:00Z"
    }
  ]
}
```

## 🛠️ **Debug Commands**

### **Clear All Data and Retry**
```javascript
// Clear all stored data
localStorage.clear();
// Reload page
window.location.reload();
```

### **Check Current User**
```javascript
// Check current user data
const user = JSON.parse(localStorage.getItem('user') || 'null');
console.log('Current user:', user);
```

### **Test API Connectivity**
```javascript
// Test basic connectivity
fetch('https://dosapi.attendance.dishaonliesolution.workspa.in/api/auth/profile/')
.then(r => console.log('Status:', r.status))
.catch(e => console.error('Error:', e));
```

## 📞 **Next Steps**

1. **Check Console Logs**: Look for detailed API request/response information
2. **Use Debug Tools**: The dashboard will show debug tools if there are errors
3. **Test Individual APIs**: Use the test page to verify each endpoint
4. **Verify Permissions**: Ensure accountant role has proper access
5. **Check Server Status**: Verify the backend server is running and accessible

## 🔧 **Quick Fixes**

### **If Nothing Works**
1. Clear browser storage completely
2. Restart the development server
3. Check if the backend server is running
4. Verify your credentials are correct
5. Check network connectivity

### **If Data Structure is Wrong**
1. Use the Data Structure Debugger
2. Check console logs for actual API responses
3. Update the data handling code if needed
4. Verify the backend API is returning expected format

The debug tools will help identify exactly what's happening with your API calls and data structure.

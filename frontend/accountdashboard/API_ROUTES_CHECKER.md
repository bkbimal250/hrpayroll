# Accountant Dashboard API Routes Checker

## 🔍 **API Base URL**
```
https://dosapi.attendance.dishaonliesolution.workspa.in/api
```

## 🔐 **Test Credentials**
- **Username:** `sejalmisal`
- **Password:** `Dos@2026`
- **Dashboard Type:** `accountant`

## 📋 **API Endpoints to Test**

### **Authentication Endpoints**
| Endpoint | Method | Description | Status |
|----------|--------|-------------|---------|
| `/auth/login/` | POST | User login | ✅ |
| `/auth/profile/` | GET | Get user profile | ✅ |
| `/auth/change-password/` | POST | Change password | ✅ |
| `/token/refresh/` | POST | Refresh access token | ✅ |

### **User Management Endpoints**
| Endpoint | Method | Description | Status |
|----------|--------|-------------|---------|
| `/users/` | GET | Get all users | ✅ |
| `/users/{id}/` | GET | Get specific user | ✅ |
| `/users/{id}/` | PATCH | Update user | ✅ |

### **Office Management Endpoints**
| Endpoint | Method | Description | Status |
|----------|--------|-------------|---------|
| `/offices/` | GET | Get all offices | ✅ |
| `/offices/{id}/` | GET | Get specific office | ✅ |

### **Department Management Endpoints**
| Endpoint | Method | Description | Status |
|----------|--------|-------------|---------|
| `/departments/` | GET | Get all departments | ✅ |
| `/departments/{id}/` | GET | Get specific department | ✅ |

### **Designation Management Endpoints**
| Endpoint | Method | Description | Status |
|----------|--------|-------------|---------|
| `/designations/` | GET | Get all designations | ✅ |
| `/designations/{id}/` | GET | Get specific designation | ✅ |

### **Attendance Management Endpoints**
| Endpoint | Method | Description | Status |
|----------|--------|-------------|---------|
| `/attendance/` | GET | Get attendance records | ✅ |
| `/attendance/today/` | GET | Get today's attendance | ✅ |
| `/attendance/date/{date}/` | GET | Get attendance by date | ✅ |
| `/attendance/employee/{id}/` | GET | Get employee attendance | ✅ |

### **Reports Endpoints**
| Endpoint | Method | Description | Status |
|----------|--------|-------------|---------|
| `/reports/attendance/` | GET | Generate attendance report | ✅ |
| `/reports/user/` | GET | Generate user report | ✅ |

## 🧪 **Testing Instructions**

### **Step 1: Open Test Page**
1. Open `test-accountant-api.html` in your browser
2. The credentials are pre-filled: `sejalmisal` / `Dos@2026`

### **Step 2: Test Authentication**
1. Click "Test Login" button
2. Verify login is successful
3. Check token information is displayed

### **Step 3: Test Individual Endpoints**
1. Click individual test buttons for each endpoint
2. Verify each endpoint returns data successfully
3. Check the response structure and data

### **Step 4: Test All Endpoints**
1. Click "Test All" button to run comprehensive tests
2. Review all results for any failures
3. Check console for detailed logs

## 📊 **Expected Response Formats**

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
      "office": {
        "id": "uuid",
        "name": "Main Office"
      }
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
      "user": {
        "id": "uuid",
        "first_name": "John",
        "last_name": "Doe"
      },
      "date": "2024-01-15",
      "status": "present",
      "check_in_time": "2024-01-15T09:00:00Z"
    }
  ]
}
```

### **Offices API Response**
```json
{
  "results": [
    {
      "id": "uuid",
      "name": "Main Office",
      "address": "123 Main St",
      "phone": "+1234567890"
    }
  ]
}
```

## 🔧 **Troubleshooting**

### **Common Issues**

1. **401 Unauthorized**
   - Check if token is expired
   - Verify credentials are correct
   - Try refreshing the token

2. **403 Forbidden**
   - Check user permissions
   - Verify accountant role access

3. **404 Not Found**
   - Check endpoint URL
   - Verify server is running

4. **500 Server Error**
   - Check server logs
   - Verify database connection

### **Debug Steps**

1. **Check Browser Console**
   - Look for detailed API logs
   - Check for error messages

2. **Verify Token Status**
   - Use "Analyze Current Tokens" button
   - Check token expiration

3. **Test Individual Endpoints**
   - Test each endpoint separately
   - Identify which ones are failing

4. **Check Network Tab**
   - Verify requests are being sent
   - Check response status codes

## 📈 **Success Criteria**

- ✅ Login successful with provided credentials
- ✅ All API endpoints return 200 status
- ✅ Data is properly structured and accessible
- ✅ Token refresh works correctly
- ✅ No authentication errors

## 🚀 **Next Steps**

1. Run the test page
2. Verify all endpoints are working
3. Check data structure matches expectations
4. Report any issues found
5. Implement fixes if needed

The test page will provide detailed information about each API call, including response data, error messages, and token status.

# 🔐 Accountant Dashboard API Testing Guide

This guide provides comprehensive testing tools and instructions for testing all APIs related to the accountant dashboard functionality.

## 📋 Test Credentials
- **Username**: `manishayadav`
- **Password**: `Dos@2026`
- **Base URL**: `http://127.0.0.1:8000`

## 🛠️ Testing Tools Available

### 1. **HTML/JavaScript Testing Tool** (`test_accountant_apis.html`)
- **Best for**: Interactive testing with visual interface
- **Features**: 
  - Click-to-test buttons for each API
  - Real-time results display
  - Color-coded success/error indicators
  - No installation required

**How to use:**
1. Open `test_accountant_apis.html` in your web browser
2. Click "Test Login" to authenticate
3. Use individual test buttons for each API endpoint
4. View results in real-time

### 2. **Python Testing Script** (`test_accountant_apis.py`)
- **Best for**: Comprehensive automated testing
- **Features**:
  - Detailed logging with timestamps
  - JSON response formatting
  - Exception handling
  - Exit codes for CI/CD integration

**How to use:**
```bash
# Install required dependencies
pip install requests

# Run the test script
python test_accountant_apis.py
```

### 3. **PowerShell Script** (`test_accountant_apis.ps1`)
- **Best for**: Windows users with PowerShell
- **Features**:
  - Colored output
  - JSON formatting
  - Windows-native execution

**How to use:**
```powershell
# Run in PowerShell
.\test_accountant_apis.ps1
```

### 4. **Bash Script** (`test_accountant_apis.sh`)
- **Best for**: Linux/macOS users
- **Features**:
  - Colored output
  - JSON formatting with jq (optional)
  - Unix-native execution

**How to use:**
```bash
# Make executable (Linux/macOS)
chmod +x test_accountant_apis.sh

# Run the script
./test_accountant_apis.sh
```

## 🧪 API Endpoints Being Tested

### **Authentication**
- `POST /api/auth/login/` - Login and get JWT token

### **User Profile**
- `GET /api/auth/profile/` - Get current user profile

### **Leaves Management**
- `GET /api/leaves/my/` - Get current user's leaves
- `POST /api/leaves/` - Create new leave request

### **Documents Management**
- `GET /api/documents/my/` - Get current user's documents
- `GET /api/generated-documents/my_documents/` - Get generated documents

### **Resignations Management**
- `GET /api/resignations/my_resignations/` - Get current user's resignations
- `POST /api/resignations/` - Create new resignation request

### **Attendance Management**
- `GET /api/attendance/my/` - Get current user's attendance
- `GET /api/attendance/summary/` - Get attendance summary

##  Expected Test Results

### **Successful Login Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "uuid",
    "username": "manishayadav",
    "email": "manishayadav@example.com",
    "role": "accountant",
    "first_name": "Manisha",
    "last_name": "Yadav"
  }
}
```

### **Leave Request Creation:**
```json
{
  "id": "uuid",
  "leave_type": "sick",
  "start_date": "2024-02-01",
  "end_date": "2024-02-02",
  "reason": "Medical appointment - API test",
  "status": "pending",
  "created_at": "2024-01-20T10:00:00Z"
}
```

### **Resignation Request Creation:**
```json
{
  "id": "uuid",
  "resignation_date": "2024-03-15",
  "notice_period_days": 30,
  "reason": "Career growth opportunity - API test",
  "status": "pending",
  "created_at": "2024-01-20T10:00:00Z"
}
```

## Troubleshooting

### **Common Issues:**

1. **Connection Refused**
   - Ensure Django server is running on `http://127.0.0.1:8000`
   - Check if the server is accessible

2. **Authentication Failed**
   - Verify credentials are correct
   - Check if the user account exists and is active
   - Ensure the user has 'accountant' role

3. **Permission Denied**
   - Verify the user has appropriate permissions
   - Check if the user role is correctly set

4. **CORS Issues (HTML tool)**
   - Ensure Django CORS settings allow requests from file:// protocol
   - Consider running a local web server for the HTML file

### **Debug Steps:**

1. **Check Server Status:**
   ```bash
   curl http://127.0.0.1:8000/api/
   ```

2. **Test Login Manually:**
   ```bash
   curl -X POST http://127.0.0.1:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username":"manishayadav","password":"Dos@2026"}'
   ```

3. **Check Django Logs:**
   - Look at Django console output for error messages
   - Check database connectivity

##  Performance Testing

For load testing, you can modify the Python script to:
- Run multiple concurrent requests
- Measure response times
- Test rate limiting

## 🔒 Security Testing

The scripts also help verify:
- JWT token expiration handling
- Proper authentication headers
- Role-based access control
- Input validation

##  Test Results Interpretation

### **Success Indicators:**
-  HTTP 200/201 status codes
-  Valid JSON responses
-  Expected data structure
-  Proper authentication

### **Failure Indicators:**
-  HTTP 4xx/5xx status codes
-  Authentication errors
-  Permission denied errors
-  Invalid JSON responses

##  Next Steps

After successful API testing:

1. **Update Frontend**: Replace mock data with real API calls
2. **Error Handling**: Implement proper error handling in frontend
3. **Loading States**: Add loading indicators for API calls
4. **Validation**: Implement client-side validation
5. **Testing**: Add unit tests for API integration

## 📞 Support

If you encounter issues:
1. Check Django server logs
2. Verify database connectivity
3. Ensure all required packages are installed
4. Check network connectivity
5. Verify user permissions and roles

---

**Happy Testing! 🎉**

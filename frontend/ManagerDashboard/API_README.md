# 🔌 API Documentation

Complete API reference for the Employee Attendance Manager Dashboard backend integration.

## 📋 Table of Contents

- [Authentication](#authentication)
- [Base Configuration](#base-configuration)
- [Endpoints](#endpoints)
- [WebSocket API](#websocket-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## 🔐 Authentication

### JWT Token Authentication
All API requests require a valid JWT token in the Authorization header.

```javascript
// Request header format
Authorization: Bearer <jwt_token>
```

### Token Management
```javascript
// Storing token after login
localStorage.setItem('authToken', response.data.token);

// Using token in requests
const token = localStorage.getItem('authToken');
axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
```

### Token Refresh
```javascript
// Automatic token refresh on 401 errors
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Attempt token refresh
      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        try {
          const response = await axios.post('/api/auth/refresh/', {
            refresh: refreshToken
          });
          localStorage.setItem('authToken', response.data.access);
          // Retry original request
          return axios.request(error.config);
        } catch (refreshError) {
          // Redirect to login
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
```

## ⚙️ Base Configuration

### API Base URL
```javascript
// Development
const API_BASE_URL = 'http://localhost:8000/api';

// Production
const API_BASE_URL = 'https://your-api-server.com/api';
```

### Request Configuration
```javascript
// Default axios configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false, // CORS compatibility
  maxRedirects: 0, // Prevent redirect loops
});
```

## 🛠️ Endpoints

### Authentication Endpoints

#### Login
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "manager@company.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "manager@company.com",
    "email": "manager@company.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "manager",
    "office": {
      "id": 1,
      "name": "Main Office",
      "location": "New York"
    }
  }
}
```

#### Logout
```http
POST /api/auth/logout/
Authorization: Bearer <token>
```

#### Token Refresh
```http
POST /api/auth/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Employee Endpoints

#### Get All Employees
```http
GET /api/employees/
Authorization: Bearer <token>
```

**Query Parameters:**
- `office_id`: Filter by office ID
- `search`: Search by name or employee ID
- `page`: Page number for pagination
- `page_size`: Number of items per page
- `ordering`: Sort order (e.g., `name`, `-created_at`)

**Response:**
```json
{
  "count": 150,
  "next": "http://api.example.com/employees/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "employee_id": "EMP001",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@company.com",
      "phone": "+1234567890",
      "department": "Engineering",
      "designation": "Senior Developer",
      "office": {
        "id": 1,
        "name": "Main Office"
      },
      "hire_date": "2023-01-15",
      "status": "active",
      "profile_picture": "https://api.example.com/media/profiles/john_doe.jpg"
    }
  ]
}
```

#### Get Employee Details
```http
GET /api/employees/{id}/
Authorization: Bearer <token>
```

#### Create Employee
```http
POST /api/employees/
Authorization: Bearer <token>
Content-Type: application/json

{
  "employee_id": "EMP002",
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@company.com",
  "phone": "+1234567891",
  "department": "Marketing",
  "designation": "Marketing Manager",
  "office": 1,
  "hire_date": "2024-01-15"
}
```

#### Update Employee
```http
PUT /api/employees/{id}/
Authorization: Bearer <token>
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@company.com",
  "phone": "+1234567891",
  "department": "Marketing",
  "designation": "Senior Marketing Manager"
}
```

#### Delete Employee
```http
DELETE /api/employees/{id}/
Authorization: Bearer <token>
```

### Attendance Endpoints

#### Get Attendance Records
```http
GET /api/attendance/
Authorization: Bearer <token>
```

**Query Parameters:**
- `employee_id`: Filter by employee ID
- `date_from`: Start date (YYYY-MM-DD)
- `date_to`: End date (YYYY-MM-DD)
- `status`: Filter by status (present, absent, late)
- `office_id`: Filter by office ID

**Response:**
```json
{
  "count": 500,
  "next": "http://api.example.com/attendance/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "employee": {
        "id": 1,
        "employee_id": "EMP001",
        "first_name": "John",
        "last_name": "Doe"
      },
      "date": "2024-01-15",
      "check_in": "09:00:00",
      "check_out": "17:30:00",
      "status": "present",
      "is_late": false,
      "hours_worked": 8.5,
      "device": "Device-001",
      "office": {
        "id": 1,
        "name": "Main Office"
      }
    }
  ]
}
```

#### Create Attendance Record
```http
POST /api/attendance/
Authorization: Bearer <token>
Content-Type: application/json

{
  "employee": 1,
  "date": "2024-01-15",
  "check_in": "09:00:00",
  "check_out": "17:30:00",
  "device": "Device-001"
}
```

#### Update Attendance Record
```http
PUT /api/attendance/{id}/
Authorization: Bearer <token>
Content-Type: application/json

{
  "check_in": "09:15:00",
  "check_out": "17:45:00",
  "status": "late"
}
```

### Leave Management Endpoints

#### Get Leave Requests
```http
GET /api/leaves/
Authorization: Bearer <token>
```

**Query Parameters:**
- `employee_id`: Filter by employee ID
- `status`: Filter by status (pending, approved, rejected)
- `leave_type`: Filter by leave type (sick, vacation, personal)
- `date_from`: Start date filter
- `date_to`: End date filter

**Response:**
```json
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "employee": {
        "id": 1,
        "employee_id": "EMP001",
        "first_name": "John",
        "last_name": "Doe"
      },
      "leave_type": "vacation",
      "start_date": "2024-02-01",
      "end_date": "2024-02-05",
      "days": 5,
      "reason": "Family vacation",
      "status": "pending",
      "applied_date": "2024-01-15T10:30:00Z",
      "approved_by": null,
      "approved_date": null,
      "rejection_reason": null
    }
  ]
}
```

#### Create Leave Request
```http
POST /api/leaves/
Authorization: Bearer <token>
Content-Type: application/json

{
  "leave_type": "sick",
  "start_date": "2024-02-01",
  "end_date": "2024-02-02",
  "reason": "Medical appointment"
}
```

#### Approve Leave Request
```http
POST /api/leaves/{id}/approve/
Authorization: Bearer <token>
Content-Type: application/json

{
  "comments": "Approved for medical reasons"
}
```

#### Reject Leave Request
```http
POST /api/leaves/{id}/reject/
Authorization: Bearer <token>
Content-Type: application/json

{
  "rejection_reason": "Insufficient notice period"
}
```

### Reports Endpoints

#### Get Attendance Reports
```http
GET /api/reports/attendance/
Authorization: Bearer <token>
```

**Query Parameters:**
- `date_from`: Start date (YYYY-MM-DD)
- `date_to`: End date (YYYY-MM-DD)
- `office_id`: Filter by office ID
- `employee_id`: Filter by employee ID
- `format`: Response format (json, csv, pdf)

**Response:**
```json
{
  "summary": {
    "total_employees": 50,
    "present_count": 45,
    "absent_count": 5,
    "attendance_rate": 90.0,
    "average_hours": 8.2
  },
  "daily_stats": [
    {
      "date": "2024-01-15",
      "present": 45,
      "absent": 5,
      "late": 3,
      "attendance_rate": 90.0
    }
  ],
  "data": [
    {
      "employee": "John Doe",
      "employee_id": "EMP001",
      "date": "2024-01-15",
      "status": "present",
      "check_in": "09:00:00",
      "check_out": "17:30:00",
      "hours_worked": 8.5
    }
  ]
}
```

#### Get Leave Reports
```http
GET /api/reports/leaves/
Authorization: Bearer <token>
```

#### Get Employee Reports
```http
GET /api/reports/employees/
Authorization: Bearer <token>
```

#### Export Reports
```http
GET /api/reports/{type}/export/
Authorization: Bearer <token>
```

**Query Parameters:**
- `format`: Export format (csv, pdf, excel)
- `date_from`: Start date
- `date_to`: End date
- `office_id`: Office filter

### Resignation Endpoints

#### Get Resignation Requests
```http
GET /api/resignations/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "employee": {
        "id": 1,
        "employee_id": "EMP001",
        "first_name": "John",
        "last_name": "Doe"
      },
      "resignation_date": "2024-03-01",
      "last_working_date": "2024-03-15",
      "reason": "Career advancement opportunity",
      "status": "pending",
      "submitted_date": "2024-01-15T10:30:00Z",
      "approved_by": null,
      "approved_date": null,
      "rejection_reason": null
    }
  ]
}
```

#### Approve Resignation
```http
POST /api/resignations/{id}/approve/
Authorization: Bearer <token>
Content-Type: application/json

{
  "comments": "Approved resignation"
}
```

#### Reject Resignation
```http
POST /api/resignations/{id}/reject/
Authorization: Bearer <token>
Content-Type: application/json

{
  "rejection_reason": "Critical project dependency"
}
```

### Dashboard Statistics

#### Get Dashboard Stats
```http
GET /api/dashboard/stats/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "attendance": {
    "today_present": 45,
    "today_absent": 5,
    "attendance_rate": 90.0,
    "late_arrivals": 3
  },
  "leaves": {
    "pending_requests": 8,
    "approved_this_month": 15,
    "rejected_this_month": 2
  },
  "employees": {
    "total_employees": 50,
    "active_employees": 48,
    "new_this_month": 2
  },
  "resignations": {
    "pending": 3,
    "approved_this_month": 1,
    "rejected_this_month": 0
  }
}
```

## 🔌 WebSocket API

### Connection
```javascript
const ws = new WebSocket('wss://your-websocket-server.com/ws/attendance/');
```

### Authentication
```javascript
ws.onopen = function() {
  // Send authentication
  ws.send(JSON.stringify({
    'type': 'auth',
    'token': localStorage.getItem('authToken')
  }));
};
```

### Event Types

#### Join Attendance Room
```javascript
ws.send(JSON.stringify({
  'type': 'join_attendance_room',
  'employee_id': 123
}));
```

#### Leave Attendance Room
```javascript
ws.send(JSON.stringify({
  'type': 'leave_attendance_room',
  'employee_id': 123
}));
```

#### Join General Attendance
```javascript
ws.send(JSON.stringify({
  'type': 'join_general_attendance'
}));
```

### Received Events

#### Attendance Update
```json
{
  "type": "attendance_update",
  "data": {
    "employee_id": 123,
    "employee_name": "John Doe",
    "status": "present",
    "date": "2024-01-15",
    "timestamp": "2024-01-15T09:00:00Z",
    "device": "Device-001",
    "isLate": false
  }
}
```

#### General Attendance Update
```json
{
  "type": "general_attendance_update",
  "data": {
    "office_id": 1,
    "total_present": 45,
    "total_absent": 5,
    "attendance_rate": 90.0,
    "timestamp": "2024-01-15T09:00:00Z"
  }
}
```

## ❌ Error Handling

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

### Error Response Format
```json
{
  "error": "Validation failed",
  "message": "Invalid input data",
  "details": {
    "email": ["This field is required."],
    "phone": ["Enter a valid phone number."]
  },
  "code": "VALIDATION_ERROR"
}
```

### Common Error Scenarios

#### Authentication Errors
```json
{
  "error": "Authentication failed",
  "message": "Invalid or expired token",
  "code": "AUTH_ERROR"
}
```

#### Permission Errors
```json
{
  "error": "Permission denied",
  "message": "You don't have permission to perform this action",
  "code": "PERMISSION_ERROR"
}
```

#### Validation Errors
```json
{
  "error": "Validation failed",
  "message": "Invalid input data",
  "details": {
    "email": ["Enter a valid email address."],
    "date": ["Date cannot be in the past."]
  },
  "code": "VALIDATION_ERROR"
}
```

## 🚦 Rate Limiting

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### Rate Limit Exceeded
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

## 📝 Examples

### Complete API Integration Example
```javascript
// API service configuration
import axios from 'axios';

const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh or redirect to login
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API methods
export const authAPI = {
  login: (credentials) => api.post('/auth/login/', credentials),
  logout: () => api.post('/auth/logout/'),
  refresh: (refreshToken) => api.post('/auth/refresh/', { refresh: refreshToken }),
};

export const employeeAPI = {
  getEmployees: (params) => api.get('/employees/', { params }),
  getEmployee: (id) => api.get(`/employees/${id}/`),
  createEmployee: (data) => api.post('/employees/', data),
  updateEmployee: (id, data) => api.put(`/employees/${id}/`, data),
  deleteEmployee: (id) => api.delete(`/employees/${id}/`),
};

export const attendanceAPI = {
  getAttendance: (params) => api.get('/attendance/', { params }),
  createAttendance: (data) => api.post('/attendance/', data),
  updateAttendance: (id, data) => api.put(`/attendance/${id}/`, data),
};

export const leaveAPI = {
  getLeaves: (params) => api.get('/leaves/', { params }),
  createLeave: (data) => api.post('/leaves/', data),
  approveLeave: (id, data) => api.post(`/leaves/${id}/approve/`, data),
  rejectLeave: (id, data) => api.post(`/leaves/${id}/reject/`, data),
};

export const reportAPI = {
  getAttendanceReport: (params) => api.get('/reports/attendance/', { params }),
  getLeaveReport: (params) => api.get('/reports/leaves/', { params }),
  exportReport: (type, format, params) => 
    api.get(`/reports/${type}/export/`, { 
      params: { ...params, format },
      responseType: 'blob'
    }),
};

export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats/'),
};
```

### WebSocket Integration Example
```javascript
// WebSocket service
class WebSocketService {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  connect() {
    const wsUrl = process.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws/attendance/';
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.authenticate();
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  authenticate() {
    const token = localStorage.getItem('authToken');
    if (token) {
      this.send({
        type: 'auth',
        token: token
      });
    }
  }

  subscribeToEmployee(employeeId) {
    this.send({
      type: 'join_attendance_room',
      employee_id: employeeId
    });
  }

  unsubscribeFromEmployee(employeeId) {
    this.send({
      type: 'leave_attendance_room',
      employee_id: employeeId
    });
  }

  subscribeToGeneral() {
    this.send({
      type: 'join_general_attendance'
    });
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  handleMessage(data) {
    switch (data.type) {
      case 'attendance_update':
        this.onAttendanceUpdate(data.data);
        break;
      case 'general_attendance_update':
        this.onGeneralUpdate(data.data);
        break;
      case 'auth_success':
        console.log('WebSocket authenticated');
        break;
      case 'auth_error':
        console.error('WebSocket authentication failed');
        break;
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export default new WebSocketService();
```

## 🔧 Configuration

### Environment Variables
```env
# API Configuration
VITE_API_BASE_URL=https://your-api-server.com/api
VITE_WEBSOCKET_URL=wss://your-websocket-server.com/ws/attendance/

# Authentication
VITE_JWT_SECRET=your-jwt-secret

# Feature Flags
VITE_ENABLE_WEBSOCKET=true
VITE_ENABLE_NOTIFICATIONS=true
VITE_ENABLE_OFFLINE_MODE=false
```

### CORS Configuration
Ensure your backend server is configured with proper CORS headers:

```python
# Django CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://your-frontend-domain.com",
]

CORS_ALLOW_CREDENTIALS = False
CORS_ALLOW_ALL_ORIGINS = False
```

## 🧪 Testing

### API Testing with curl
```bash
# Test authentication
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "manager@company.com", "password": "password"}'

# Test employee endpoint
curl -X GET http://localhost:8000/api/employees/ \
  -H "Authorization: Bearer <your-token>"

# Test attendance endpoint
curl -X GET "http://localhost:8000/api/attendance/?date_from=2024-01-01&date_to=2024-01-31" \
  -H "Authorization: Bearer <your-token>"
```

### Postman Collection
Import the provided Postman collection for comprehensive API testing:
- Authentication endpoints
- CRUD operations for all resources
- Report generation
- WebSocket testing

## 📞 Support

For API-related issues:
1. Check the error response format
2. Verify authentication tokens
3. Test endpoints with curl or Postman
4. Review server logs for detailed error information
5. Contact the backend development team

---

**🔗 Related Documentation:**
- [Main README](./README.md)
- [Deployment Guide](./DEPLOYMENT_README.md)
- [WebSocket Implementation](./WEBSOCKET_IMPLEMENTATION.md)
- [API Troubleshooting](./API_TROUBLESHOOTING_GUIDE.md)

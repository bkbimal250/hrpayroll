# Employee Dashboard

A clean and structured employee dashboard built with React and Tailwind CSS that integrates with the Django backend API.

## Features

### 📊 Dashboard Overview
- **Welcome section** with employee information
- **Statistics cards** showing attendance, leaves, and documents summary
- **Quick actions** for common tasks
- **Real-time data** from backend API

### ⏰ Attendance Management
- **Monthly attendance view** with calendar navigation
- **Attendance statistics** (Present, Absent, Late, Total Days)
- **Detailed attendance table** with check-in/out times
- **Status indicators** with color coding

### 🗓️ Leave Management
- **Leave request form** with validation
- **Leave history** with status tracking
- **Statistics overview** (Total, Approved, Pending, Rejected)
- **Date range selection** with automatic day calculation

### 📄 Document Management
- **Document upload** with file type selection
- **Document library** with download functionality
- **File type categorization** (Resume, Certificate, ID Proof, Other)
- **Upload statistics** and file size display

## API Integration

The dashboard uses the following backend endpoints:

### Authentication
- `GET /api/auth/profile/` - Get employee profile
- `PUT /api/auth/profile/update/` - Update profile

### Attendance
- `GET /api/attendance/monthly/?year={year}&month={month}` - Monthly attendance
- `GET /api/attendance/today/` - Today's attendance

### Leaves
- `GET /api/leaves/my/` - Employee's leave requests
- `POST /api/leaves/` - Create new leave request

### Documents
- `GET /api/documents/my/` - Employee's documents
- `POST /api/documents/` - Upload new document
- `GET /api/documents/{id}/download/` - Download document

## Components Structure

```
src/
├── components/
│   └── AuthGuard.jsx          # Authentication wrapper
├── Layout/
│   └── DashboardLayout.jsx    # Main layout with sidebar
├── pages/
│   ├── Dashboard.jsx          # Main dashboard overview
│   ├── Attendance.jsx         # Attendance management
│   ├── Leaves.jsx            # Leave management
│   └── Documents.jsx         # Document management
├── services/
│   └── api.js                # API service utilities
└── App.jsx                   # Main app component
```

## Usage

1. **Authentication**: The app automatically checks for valid JWT tokens
2. **Navigation**: Use the sidebar to switch between different sections
3. **Data Loading**: All data is fetched from the backend API in real-time
4. **Responsive Design**: Works on desktop and mobile devices

## Key Features

- ✅ **Clean UI** - Minimal design without extra styling
- ✅ **Structured Layout** - Organized dashboard with clear sections
- ✅ **API Integration** - Full backend integration
- ✅ **Responsive** - Mobile-friendly design
- ✅ **Authentication** - Secure token-based auth
- ✅ **Real-time Data** - Live data from backend
- ✅ **Error Handling** - Proper error states and loading indicators

## Getting Started

1. Ensure the Django backend is running on `http://localhost:8000`
2. Install dependencies: `npm install`
3. Start the development server: `npm run dev`
4. Access the dashboard at `http://localhost:3000`

## Authentication

The dashboard requires a valid JWT token stored in localStorage:
- `access_token` - For API requests
- `refresh_token` - For token renewal

If no valid token is found, users are redirected to the login page.

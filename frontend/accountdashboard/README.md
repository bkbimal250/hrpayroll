# Accountant Dashboard

This is the frontend application for the accountant role in the Employee Attendance System.

## Features

### Accountant Role Access
- **Read-only access** to all user data across all offices
- **Profile management** with ability to update personal information
- **Password change** functionality
- **Reports generation** for attendance data
- **No create, edit, or delete** permissions for user management

### Pages Available
1. **Dashboard** - Overview of system data
2. **Users** - View all employees across all offices (read-only)
3. **Attendance** - View attendance records (read-only)
4. **Reports** - Generate and export attendance reports
5. **Profile** - Manage personal information and change password

## Setup Instructions

### 1. Install Dependencies
```bash
npm install
```

### 2. Environment Configuration
The application is configured to use the production API at `https://company.d0s369.co.in/api`.

If you need to use a different API URL, you can create a `.env` file in the root directory:
```env
VITE_API_URL=https://your-api-url.com/api
```

**Note**: This project uses Vite, so environment variables must be prefixed with `VITE_` to be accessible in the browser.

### 3. Start Development Server
```bash
npm run dev
```

The application will be available at `http://localhost:5173` (Vite default port)

## API Integration

The frontend integrates with the Django backend API with the following endpoints:

- `POST /api/users/login/` - User authentication
- `GET /api/users/` - Get all users (accountant can see all offices)
- `GET /api/users/me/` - Get current user profile
- `PATCH /api/users/{id}/` - Update user profile
- `POST /api/users/change-password/` - Change password
- `GET /api/offices/` - Get all offices
- `GET /api/reports/attendance/` - Generate attendance reports

## Accountant Permissions

Based on the backend implementation:

- **Can view**: All users from all offices
- **Cannot**: Create, edit, or delete users
- **Can**: Update own profile information
- **Can**: Change own password
- **Can**: Generate and export reports

## Authentication

The application uses JWT tokens for authentication. The login process:

1. User enters username and password
2. Frontend sends login request to backend with `dashboard_type: 'accountant'`
3. Backend validates credentials and role
4. Returns JWT token and user data
5. Token is stored in localStorage for subsequent requests

**Login Credentials**: The system uses username-based authentication instead of email.

## Role-Based Access Control

The sidebar navigation shows "View Only" indicators for pages where the accountant has read-only access. The UI clearly indicates the limited permissions available to the accountant role.

## Error Handling

The application includes comprehensive error handling for:
- API connection failures
- Authentication errors
- Permission denied errors
- Network timeouts
- Invalid data responses

## Responsive Design

The dashboard is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile phones

The sidebar collapses on mobile devices for better usability.
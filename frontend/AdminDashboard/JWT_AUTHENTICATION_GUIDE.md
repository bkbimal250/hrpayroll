# JWT Authentication Guide

## Overview

This application now uses JWT (JSON Web Tokens) for secure authentication. JWT provides:

- **Access Tokens**: Short-lived tokens (60 minutes) for API access
- **Refresh Tokens**: Long-lived tokens (7 days) for token renewal
- **Automatic Token Refresh**: Seamless token renewal without user intervention
- **Secure Storage**: Tokens stored in localStorage with automatic cleanup

## API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description | Request Body |
|----------|--------|-------------|--------------|
| `/api/token/` | POST | Login and get tokens | `{"username": "admin", "password": "admin123"}` |
| `/api/token/refresh/` | POST | Refresh access token | `{"refresh": "refresh_token_here"}` |
| `/api/token/verify/` | POST | Verify token validity | `{"token": "access_token_here"}` |

### Response Format

**Login Response:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Refresh Response:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Frontend Usage

### 1. Import JWT Service

```javascript
import jwtAuthService from '../services/jwtAuth';
// or import specific functions
import { login, logout, isAuthenticated, getAccessToken } from '../services/jwtAuth';
```

### 2. Login

```javascript
const handleLogin = async (credentials) => {
  const result = await jwtAuthService.login(credentials);
  
  if (result.success) {
    console.log('Login successful:', result.user);
    // Navigate to dashboard
  } else {
    console.error('Login failed:', result.error);
  }
};
```

### 3. Check Authentication Status

```javascript
// Check if user is authenticated
if (jwtAuthService.isAuthenticated()) {
  const user = jwtAuthService.getUser();
  console.log('Current user:', user);
}

// Check if token is expired
const token = jwtAuthService.getAccessToken();
if (jwtAuthService.isTokenExpired(token)) {
  // Token is expired, refresh or logout
}
```

### 4. Make Authenticated API Calls

```javascript
// Using the JWT service API instance
const api = jwtAuthService.getApi();
const response = await api.get('/users/profile/');

// Or using the generic request method
const result = await jwtAuthService.request({
  method: 'GET',
  url: '/users/profile/'
});
```

### 5. Refresh Token

```javascript
// Manual token refresh
const refreshed = await jwtAuthService.refreshToken();
if (refreshed) {
  console.log('Token refreshed successfully');
} else {
  console.log('Token refresh failed, user logged out');
}
```

### 6. Logout

```javascript
jwtAuthService.logout();
// This clears all tokens and redirects to login page
```

## React Context Usage

### Using AuthContext

```javascript
import { useAuth } from '../contexts/AuthContext';

function MyComponent() {
  const { 
    user, 
    loading, 
    error, 
    authenticated,
    login, 
    logout, 
    isAdmin, 
    isManager,
    getAccessToken,
    getApi 
  } = useAuth();

  const handleLogin = async () => {
    const result = await login({ username: 'admin', password: 'admin123' });
    if (result.success) {
      console.log('Login successful');
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!authenticated) return <div>Please login</div>;

  return (
    <div>
      <h1>Welcome, {user?.username}!</h1>
      {isAdmin() && <div>Admin Dashboard</div>}
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

## Automatic Features

### 1. Automatic Token Refresh

The JWT service automatically refreshes tokens when:
- A 401 error is received from the API
- The access token is expired
- The refresh token is still valid

### 2. Request Interceptors

All API requests automatically include the JWT token in the Authorization header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Response Interceptors

The service automatically handles:
- 401 errors by attempting token refresh
- Failed refresh attempts by logging out the user
- Token expiration detection

## Token Storage

### localStorage Keys

- `access_token`: The JWT access token
- `refresh_token`: The JWT refresh token  
- `user_data`: Decoded user information from the token

### Security Considerations

- Tokens are stored in localStorage (for development)
- In production, consider using httpOnly cookies
- Tokens are automatically cleared on logout
- Expired tokens are automatically refreshed

## Error Handling

### Common Error Responses

```javascript
// Invalid credentials
{
  "detail": "No active account found with the given credentials"
}

// Token expired
{
  "detail": "Token is invalid or expired"
}

// Invalid refresh token
{
  "detail": "Token is invalid or expired"
}
```

### Error Handling Example

```javascript
try {
  const result = await jwtAuthService.login(credentials);
  if (result.success) {
    // Handle success
  } else {
    // Handle specific errors
    if (result.error?.detail) {
      console.error('Login error:', result.error.detail);
    }
  }
} catch (error) {
  console.error('Unexpected error:', error);
}
```

## Testing JWT Endpoints

### Using curl

```bash
# Login
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Use access token
curl -X GET http://localhost:8000/api/users/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Refresh token
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"YOUR_REFRESH_TOKEN"}'
```

### Using PowerShell

```powershell
# Login
Invoke-WebRequest -Uri "http://localhost:8000/api/token/" -Method POST -ContentType "application/json" -Body '{"username":"admin","password":"admin123"}'

# Use access token
Invoke-WebRequest -Uri "http://localhost:8000/api/users/profile/" -Method GET -Headers @{"Authorization"="Bearer YOUR_ACCESS_TOKEN"}
```

## Configuration

### JWT Settings (Django)

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### Frontend Configuration

```javascript
// In jwtAuth.js
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

## Best Practices

1. **Always use the JWT service** for authentication operations
2. **Check authentication status** before making API calls
3. **Handle errors gracefully** with proper user feedback
4. **Use the AuthContext** for global authentication state
5. **Implement proper loading states** during authentication
6. **Test token refresh** scenarios thoroughly
7. **Monitor token expiration** in production

## Troubleshooting

### Common Issues

1. **Token not being sent**: Check if `jwtAuthService.isAuthenticated()` returns true
2. **401 errors**: Verify token expiration and refresh mechanism
3. **CORS issues**: Ensure Django CORS settings are correct
4. **Token decode errors**: Check token format and expiration

### Debug Mode

Enable debug logging in the JWT service:

```javascript
// Add to jwtAuth.js
console.log('JWT Debug:', {
  hasToken: !!jwtAuthService.getAccessToken(),
  isAuthenticated: jwtAuthService.isAuthenticated(),
  user: jwtAuthService.getUser()
});
```

This JWT authentication system provides a robust, secure, and user-friendly authentication experience that can be used throughout your application!

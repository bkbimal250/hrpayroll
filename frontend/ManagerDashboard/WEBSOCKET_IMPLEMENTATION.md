# WebSocket Implementation for Real-time Attendance

## Overview
This document describes the WebSocket implementation that provides real-time attendance updates in the Manager Dashboard.

## Features
- **Real-time Connection**: Live WebSocket connection to Django backend
- **Attendance Updates**: Instant notifications when attendance records change
- **Employee-specific Updates**: Subscribe to updates for specific employees
- **General Updates**: Subscribe to all attendance updates
- **Auto-reconnection**: Automatic reconnection on connection loss
- **Status Indicators**: Visual connection status and real-time indicators

## Architecture

### 1. WebSocket Service (`src/services/websocket.js`)
- Manages WebSocket connection lifecycle
- Handles authentication with JWT tokens
- Provides methods for subscribing/unsubscribing to updates
- Implements auto-reconnection logic

### 2. WebSocket Context (`src/contexts/WebSocketContext.jsx`)
- Global WebSocket state management
- Provides WebSocket methods to all components
- Handles connection status monitoring
- Manages authentication tokens

### 3. Real-time Attendance Hook (`src/hooks/useRealTimeAttendance.js`)
- Custom hook for easy WebSocket integration
- Manages subscription lifecycle
- Provides real-time data and connection status
- Handles cleanup on component unmount

### 4. UI Components
- **WebSocketStatus**: Shows connection status with visual indicators
- **RealTimeNotification**: Displays live attendance updates as notifications
- **RealTimeAttendance**: Dashboard showing live attendance statistics

## Usage

### Basic WebSocket Connection
```jsx
import { useWebSocket } from '../contexts/WebSocketContext';

const MyComponent = () => {
  const { isConnected, subscribeToAttendanceUpdates } = useWebSocket();
  
  useEffect(() => {
    if (isConnected) {
      subscribeToAttendanceUpdates(employeeId, (data) => {
        console.log('Attendance update:', data);
      });
    }
  }, [isConnected, employeeId]);
};
```

### Using Real-time Attendance Hook
```jsx
import { useRealTimeAttendance } from '../hooks/useRealTimeAttendance';

const MyComponent = () => {
  const { realTimeData, isConnected, getConnectionStatus } = useRealTimeAttendance(employeeId);
  
  return (
    <div>
      <p>Status: {getConnectionStatus()}</p>
      {realTimeData && <p>Latest update: {realTimeData.status}</p>}
    </div>
  );
};
```

### Displaying Connection Status
```jsx
import WebSocketStatus from '../Components/WebSocketStatus/WebSocketStatus';

const Header = () => {
  return (
    <header>
      <WebSocketStatus showDetails={true} />
    </header>
  );
};
```

## Backend Integration

### WebSocket Endpoints
- **Connection**: `ws://localhost:8000`
- **Authentication**: JWT token in connection auth
- **Events**:
  - `join_attendance_room`: Subscribe to specific employee updates
  - `leave_attendance_room`: Unsubscribe from employee updates
  - `join_general_attendance`: Subscribe to all updates
  - `leave_general_attendance`: Unsubscribe from general updates
  - `attendance_update`: Employee-specific update event
  - `general_attendance_update`: General update event

### Expected Data Format
```json
{
  "employee_id": "123",
  "employee_name": "John Doe",
  "status": "present",
  "date": "2024-01-15",
  "timestamp": "2024-01-15T09:00:00Z",
  "device": "Device-001",
  "isLate": false
}
```

## Configuration

### Environment Variables
- **WebSocket URL**: Configure in `websocket.js` service
- **Reconnection Settings**: Adjustable in WebSocket service
- **Authentication**: Uses existing JWT token system

### Connection Settings
- **Transport**: WebSocket only (no fallback)
- **Reconnection**: Enabled with 5 attempts
- **Reconnection Delay**: 1 second between attempts
- **Authentication**: JWT token from localStorage

## Error Handling

### Connection Errors
- Automatic reconnection attempts
- Visual error indicators
- Console logging for debugging
- Graceful degradation to HTTP API

### Data Validation
- Checks for required fields
- Handles malformed data gracefully
- Logs validation errors

## Performance Considerations

### Memory Management
- Automatic cleanup of event listeners
- Subscription management
- Component unmount cleanup

### Network Optimization
- Single WebSocket connection
- Efficient event handling
- Minimal data transfer

## Security

### Authentication
- JWT token validation
- Secure WebSocket connection
- User-specific subscriptions

### Data Privacy
- Employee-specific data isolation
- Secure communication channel
- Access control through backend

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check backend WebSocket server
   - Verify authentication token
   - Check network connectivity

2. **No Real-time Updates**
   - Verify WebSocket connection status
   - Check subscription to correct events
   - Verify backend event emission

3. **Authentication Errors**
   - Check JWT token validity
   - Verify token in localStorage
   - Check backend authentication

### Debug Mode
Enable console logging by checking browser console for:
- 🔌 WebSocket connection messages
- 🔄 Real-time update messages
- ⚠️ Warning and error messages

## Future Enhancements

### Planned Features
- **Offline Support**: Cache updates when disconnected
- **Push Notifications**: Browser notifications for updates
- **Data Synchronization**: Sync missed updates on reconnection
- **Performance Metrics**: Connection quality monitoring
- **Custom Events**: User-defined notification types

### Scalability
- **Connection Pooling**: Multiple WebSocket connections
- **Load Balancing**: Distribute connections across servers
- **Message Queuing**: Handle high-volume updates
- **Compression**: Reduce data transfer size

## Support

For technical support or questions about the WebSocket implementation:
1. Check console logs for error messages
2. Verify backend WebSocket server status
3. Test authentication token validity
4. Review network connectivity

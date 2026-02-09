import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Attendance, CustomUser


class AttendanceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time attendance updates.
    Broadcasts attendance changes to all connected clients.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Accept the connection
        await self.accept()
        
        # Join the attendance group (all clients receive updates)
        await self.channel_layer.group_add(
            "attendance_updates",
            self.channel_name
        )
        
        print(f"WebSocket connected: {self.channel_name}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to attendance updates'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave the attendance group
        await self.channel_layer.group_discard(
            "attendance_updates",
            self.channel_name
        )
        print(f"WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
            elif message_type == 'get_latest':
                # Send latest attendance data
                latest_attendance = await self.get_latest_attendance()
                await self.send(text_data=json.dumps({
                    'type': 'latest_attendance',
                    'data': latest_attendance
                }))
                
        except json.JSONDecodeError:
            print("Invalid JSON received")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    async def attendance_update(self, event):
        """Send attendance update to WebSocket"""
        # Send the attendance update to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'attendance_update',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_latest_attendance(self):
        """Get latest attendance records from database"""
        try:
            # Get the latest 10 attendance records
            latest_records = Attendance.objects.select_related(
                'user', 'user__office', 'device'
            ).order_by('-created_at')[:10]
            
            # Serialize the data
            attendance_data = []
            for record in latest_records:
                attendance_data.append({
                    'id': str(record.id),
                    'user_name': record.user.get_full_name(),
                    'employee_id': record.user.employee_id,
                    'office': record.user.office.name if record.user.office else None,
                    'date': record.date.isoformat(),
                    'check_in_time': record.check_in_time.isoformat() if record.check_in_time else None,
                    'check_out_time': record.check_out_time.isoformat() if record.check_out_time else None,
                    'status': record.status,
                    'device': record.device.name if record.device else None,
                    'created_at': record.created_at.isoformat(),
                    'updated_at': record.updated_at.isoformat(),
                })
            
            return attendance_data
        except Exception as e:
            print(f"Error fetching latest attendance: {e}")
            return []


# Utility function to broadcast attendance updates
async def broadcast_attendance_update(attendance_data):
    """
    Broadcast attendance update to all connected WebSocket clients.
    This function should be called from views or signals when attendance changes.
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    
    await channel_layer.group_send(
        "attendance_updates",
        {
            "type": "attendance_update",
            "data": attendance_data
        }
    )


# Synchronous version for use in Django views/signals
def broadcast_attendance_update_sync(attendance_data):
    """
    Synchronous version of broadcast_attendance_update for use in Django views/signals.
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        "attendance_updates",
        {
            "type": "attendance_update",
            "data": attendance_data
        }
    )


class ResignationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time resignation status updates.
    Broadcasts resignation status changes to all connected clients.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Accept the connection
        await self.accept()
        
        # Join the resignation group (all clients receive updates)
        await self.channel_layer.group_add(
            "resignation_updates",
            self.channel_name
        )
        
        print(f"Resignation WebSocket connected: {self.channel_name}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to resignation updates'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave the resignation group
        await self.channel_layer.group_discard(
            "resignation_updates",
            self.channel_name
        )
        print(f"Resignation WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
            elif message_type == 'get_latest':
                # Send latest resignation data
                latest_resignations = await self.get_latest_resignations()
                await self.send(text_data=json.dumps({
                    'type': 'latest_resignations',
                    'data': latest_resignations
                }))
                
        except json.JSONDecodeError:
            print("Invalid JSON received in resignation consumer")
        except Exception as e:
            print(f"Error processing resignation message: {e}")
    
    async def resignation_update(self, event):
        """Send resignation update to WebSocket"""
        # Send the resignation update to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'resignation_update',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_latest_resignations(self):
        """Get latest resignation records from database"""
        try:
            from .models import Resignation
            
            # Get the latest 10 resignation records
            latest_records = Resignation.objects.select_related(
                'user', 'approved_by'
            ).order_by('-updated_at')[:10]
            
            # Serialize the data
            resignation_data = []
            for record in latest_records:
                resignation_data.append({
                    'id': str(record.id),
                    'user_name': record.user.get_full_name(),
                    'employee_id': record.user.employee_id,
                    'office': record.user.office.name if record.user.office else None,
                    'resignation_date': record.resignation_date.isoformat(),
                    'last_working_date': record.last_working_date.isoformat() if record.last_working_date else None,
                    'reason': record.reason,
                    'status': record.status,
                    'approved_by_name': record.approved_by.get_full_name() if record.approved_by else None,
                    'approved_at': record.approved_at.isoformat() if record.approved_at else None,
                    'status_reason': record.status_reason,
                    'created_at': record.created_at.isoformat(),
                    'updated_at': record.updated_at.isoformat(),
                })
            
            return resignation_data
        except Exception as e:
            print(f"Error fetching latest resignations: {e}")
            return []


# Utility function to broadcast resignation updates
async def broadcast_resignation_update(resignation_data):
    """
    Broadcast resignation update to all connected WebSocket clients.
    This function should be called from views or signals when resignation status changes.
    """
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    
    await channel_layer.group_send(
        "resignation_updates",
        {
            "type": "resignation_update",
            "data": resignation_data
        }
    )


# Synchronous version for use in Django views/signals
def broadcast_resignation_update_sync(resignation_data):
    """
    Synchronous version of broadcast_resignation_update for use in Django views/signals.
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        "resignation_updates",
        {
            "type": "resignation_update",
            "data": resignation_data
        }
    )
from channels.generic.websocket import AsyncWebsocketConsumer
import json
class RobotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "robot_group"


        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        await self.send(text_data="You are now connected to robot")


    async def disconnect(self, close_code):
        pass
   
    async def navigation_created(self, event):
        await self.send(text_data=json.dumps({
            "event": "navigation_created",
            "data": event["data"]
        }))
       
       
    # 🔹 This is the consumer function that receives events from channel layer
    async def entertainment_updated(self, event):
        """
        This function is triggered when a message is sent to the group
        from Django REST API (via channel_layer.group_send)
        """
        await self.send(text_data=json.dumps({
            "event": "entertainment_updated",
            "action": event["action"],   # "created" or "updated"
            "data": event["data"]        # The serialized object
        }))


    async def robot_power_status(self, event):
        # Send message + status to WebSocket clients
        await self.send(text_data=json.dumps({
            "event":"robot_power_status",
            "data":event["data"]
            }))
       
     # 🔹 Video playback update
    async def video_playback_status(self, event):
        await self.send(text_data=json.dumps({
            "event": "video_playback_status",
            "data": {"state":event["state"],
            "text": event["text"]}
        }))
       
    async def robot_battery_updates(self, event):
        await self.send(text_data=json.dumps({
            "event":"robot_battery_updates",
            "data":event["data"]}))
       
    async def robot_charge_updates(self, event):
        await self.send(text_data=json.dumps({
            "event":"robot_charge_updates",
            "data":event["data"]}))

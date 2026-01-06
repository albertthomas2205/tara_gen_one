from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import get_poweron_object
from .models import Navigation
from .serializers import *
from rest_framework import status
from django.core.cache import cache
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
import os
import requests
from rest_framework import status as drf_status
from django.http import FileResponse, Http404
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@api_view(['POST'])
def turn_on(request):
    poweron = get_poweron_object()

    if not poweron.status:  # Only turn on if currently off
        poweron.status = True
        poweron.save()

        # Send WebSocket event to all connected clients
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "robot_group",           # must match consumer group_name
            {
                "type": "robot_power_status",   # matches consumer function
                "data": {"status": poweron.status}
            }
        )

        return Response({
            "message": "Robot turned ON",
            "status": poweron.status
        })

    return Response({
        "message": "Robot was already ON",
        "status": poweron.status
    })



@api_view(['POST'])
def turn_off(request):
    poweron = get_poweron_object()

    if poweron.status:  # Only turn off if currently on
        poweron.status = False
        poweron.save()

        # Send WebSocket event
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "robot_group",           # must match consumer group_name
            {
                "type": "robot_power_status",   # matches consumer function
                "data": {"status": poweron.status}
            }
        )

        return Response({
            "message": "Robot turned OFF",
            "status": poweron.status
        })

    return Response({
        "message": "Robot was already OFF",
        "status": poweron.status
    })

@api_view(['GET'])
def check_status(request):
    poweron = get_poweron_object()
    return Response({"status": "ON" if poweron.status else "OFF"})


@api_view(['POST'])
def create_navigation(request):
    serializer = NavigationSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "ok", "message": "Navigation created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def edit_navigation(request, navigation_id):
    """
    Allows authenticated users to update an existing navigation entry.
    """
    try:
        navigation = Navigation.objects.get(id=navigation_id)
    except Navigation.DoesNotExist:
        return Response({"error": "Navigation not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = NavigationSerializer(navigation, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({"status": "ok", "message": "Navigation updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_all_navigation(request):
    """
    Delete all navigation records.
    """
    Navigation.objects.all().delete()  # Deletes all records
    return Response({"status": "ok", "message": "All navigation records deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def list_navigation(request):
    navigations = Navigation.objects.all()
    serializer = NavigationSerializer(navigations, many=True, context={'request': request})  # 👈 this is the key
    return Response({"status": "ok", "message": "Navigation list", "data": serializer.data}, status=status.HTTP_200_OK)


LAST_CLICKED_NAVIGATION_KEY = "last_clicked_navigation"

@api_view(['GET'])
def get_navigation_by_id(request, nav_id):
    """Retrieve a specific navigation item's ID and name when clicked and store it as last clicked"""
    try:
        navigation = Navigation.objects.get(id=nav_id)
        cache.set(LAST_CLICKED_NAVIGATION_KEY, {"id": navigation.id, "name": navigation.name}, timeout=2)
    except Navigation.DoesNotExist:
        return Response({"error": "Navigation not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "status": "ok",
        "message": "Navigation retrieved successfully",
        "data": {
            "id": navigation.id,
            "name": navigation.name
           
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_last_clicked_navigation(request):
    """Retrieve the last clicked navigation from memory, expire after 10 seconds"""
    last_clicked = cache.get(LAST_CLICKED_NAVIGATION_KEY)

    if not last_clicked:
        return Response({"error": "No navigation has been clicked yet or it has expired."}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "status": "ok",
        "message": "Last clicked navigation retrieved successfully",
        "data": last_clicked
    }, status=status.HTTP_200_OK)



global_status = {
    "status": False,
    "last_updated": None
}
@api_view(['POST'])
def update_base_status(request):
    """
    Update the global status.
    Accepts 'status': true/false in the request body.
    """
    new_status = request.data.get('status', None)

    if new_status is None:
        return Response({"message": "Status is required"}, status=status.HTTP_400_BAD_REQUEST)

    global_status["status"] = new_status
    global_status["last_updated"] = datetime.now() if new_status else None  

    return Response({"message": "Status updated successfully"}, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_base_status(request):
    """
    Get the current status.
    If status has been True for more than 15 seconds, reset it to False.
    """
    if global_status["status"] and global_status["last_updated"]:
        elapsed_time = (datetime.now() - global_status["last_updated"]).total_seconds()
        if elapsed_time > 15:
            global_status["status"] = False 
            global_status["last_updated"] = None

    return Response({"status": bool(global_status["status"])}, status=status.HTTP_200_OK)

robo_volumes = {}

def set_volume(request, robo_id, volume):
    """
    Set the volume for a specific robot.
    Only the last updated volume is stored.
    """
    try:
        volume = int(volume)  # Ensure volume is an integer

        if 0 <= volume <= 150:
            robo_volumes[robo_id] = volume  # Store only the latest volume
            return JsonResponse({"message": "Volume updated", "robo_id": robo_id, "current_volume": volume})
        else:
            return JsonResponse({"error": "Volume must be between 0 and 150"}, status=400)

    except ValueError:
        return JsonResponse({"error": "Invalid volume input. Volume must be an integer."}, status=400)

def get_volume(request, robo_id):
    """
    Get the last updated volume of the robot.
    If no volume was set, return a default of 50.
    """
    volume = robo_volumes.get(robo_id, 50)  # Return default volume if not set
    return JsonResponse({"robo_id": robo_id, "current_volume": volume})



# video playing updation
# Global state and text
state = {
    "listening": False,
    "waiting": False,
    "speaking": False,
}
text = ""  # 👈 Added text field

# Command to state mapping
COMMAND_MAPPING = {
    "SPEAKING_VIDEO": "speaking",
    "LISTENING_VIDEO": "listening",
    "WAITING_VIDEO": "waiting",
}

@api_view(["POST"])
def update_status(request):
    """
    API to update the status based on command input.
    Only one state key can be True at a time.
    Also updates the optional text field.
    """
    global text

    data = request.data
    command = data.get("command")
    input_text = data.get("text")  # 👈 Get optional text field

    if input_text is not None:
        text = input_text  # Update global text

    if not command:
        return Response({
            "message": "No command provided",
            "command": None,
            "data": state,
            "text": text  # 👈 Include text in response
        }, status=status.HTTP_200_OK)

    if command not in COMMAND_MAPPING:
        return Response({
            "error": "Invalid command provided",
            "command": command,
            "text": text
        }, status=status.HTTP_400_BAD_REQUEST)

    # Reset all state values, set only the relevant one to True
    key_to_update = COMMAND_MAPPING[command]
    for key in state:
        state[key] = False
    state[key_to_update] = True
    
    
    # 🔥 WebSocket trigger (EVERY update)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "robot_group",
        {
            "type": "video_playback_status",
            "state": state,
            "text": text
        }
    )

    return Response({
        "status": "OK",
        "command": command,
        "text": text,  # 👈 Include updated text
        key_to_update: True
    }, status=status.HTTP_200_OK)

@api_view(["GET"])
def list_status(request):
    """
    API to return the current state of all statuses and the current text.
    """
    return Response({
        "status": "OK",
        "data": state,
        "text": text  # 👈 Include text here too
    }, status=status.HTTP_200_OK)



@api_view(['POST'])
def create_full_tour(request):
    navigations = request.data.get('navigations', [])

    if not isinstance(navigations, list):
        return Response({"error": "Invalid data format. Navigations must be a list of IDs."}, status=status.HTTP_400_BAD_REQUEST)

    FullTour.objects.all().delete()  # Keep only one FullTour at a time
    full_tour = FullTour.objects.create(navigations=navigations)

    serializer = FullTourSerializer(full_tour)
    return Response({"status": "ok", "message": "Full tour created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def full_tour_list(request):
    full_tour = FullTour.objects.last()  # Get the latest FullTour instance

    if not full_tour:
        return Response({"status": "ok", "data": None}, status=status.HTTP_200_OK)

    serializer = FullTourSerializer(full_tour)
    return Response({"status": "ok", "data": serializer.data}, status=status.HTTP_200_OK)



local_store = {"status": False}  # Default status is False

@api_view(['POST'])
def delete_status(request):
    """Update the status (only one status is stored at a time)."""
    new_status = request.data.get('status', False)  # Expecting {"status": true/false}
    
    local_store["status"] = new_status  # Overwrite the stored status

    return Response({"message": "Status updated", "status": local_store["status"]}, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_delete_status(request):
    """Retrieve the current status."""
    return Response({"status": local_store["status"]}, status=status.HTTP_200_OK)

MESSAGE_CACHE_KEY = "latest_message_{}"
BUTTON_STATUS_KEY = "button_status_{}"

@api_view(['POST'])
def post_message(request, robot_id: str):
    """API to post a message and store it in cache for 5 minutes for a specific robot"""
    message = request.data.get("message")
    if not message:
        return Response({"error": "Message is required."}, status=status.HTTP_400_BAD_REQUEST)

    cache.set(MESSAGE_CACHE_KEY.format(robot_id), message, timeout=15) 
    return Response({"status": "ok", "message": "Message posted successfully"}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_message(request, robot_id: str):
    """API to get the latest message for a specific robot, or return 'no message' if expired"""
    message = cache.get(MESSAGE_CACHE_KEY.format(robot_id))
    if not message:
        return Response({"status": "ok","message": "no message"}, status=status.HTTP_200_OK)

    return Response({"status": "ok", "message": message}, status=status.HTTP_200_OK)


@api_view(['POST'])
def button_click(request, robot_id: str):
    """API to set button status and clear the message when clicked"""
    status_value = request.data.get("status")

    if status_value not in ["true", "false"]:
        return Response({"error": "Invalid status. Use 'true' or 'false'."}, status=status.HTTP_400_BAD_REQUEST)

    # Set button status in cache
    cache.set(BUTTON_STATUS_KEY.format(robot_id), status_value, timeout=15)  

    # Clear the message cache when the button is clicked
    cache.delete(MESSAGE_CACHE_KEY.format(robot_id))

    return Response({"status": "ok", "message": f"Button clicked, status set to {status_value}, message cleared"}, status=status.HTTP_200_OK)

@api_view(['GET'])
def button_status(request, robot_id: str):
    """API to get button status for a specific robot - 'true', 'false', or 'no message' after expiry"""
    status_value = cache.get(BUTTON_STATUS_KEY.format(robot_id), "no message")  # Default is "no message"
    return Response({"status": status_value}, status=status.HTTP_200_OK)


@api_view(['POST'])
def upload_api_key(request):
    """Upload a new API key and remove the old key automatically."""
    # Delete all old API keys
    APIKey.objects.all().delete()

    # Create a new API key
    serializer = APIKeySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status":"ok","message":"upload key successfully","data":serializer.data}, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_api_key(request):
    """Retrieve the latest API key."""
    api_key = APIKey.objects.order_by('-created_at').first()  # Get the latest API key
    if api_key:
        serializer = APIKeySerializer(api_key)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response({"error": "No API key found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def update_tour_status(request):
    """
    Updates the tour status.
    - If `status` is provided, sets it to True/False.
    - If `toggle` is provided, flips the current status.
    """
    new_status = request.data.get("status")  # Expecting True/False
    toggle = request.data.get("status", False)  # Expecting True

    if toggle:
        current_status = cache.get("tour_status", False)
        new_status = not current_status  # Flip status

    if new_status is None or not isinstance(new_status, bool):
        return Response({"error": "Invalid input. Use {'status': true/false} or {'status': true}."}, status=status.HTTP_400_BAD_REQUEST)

    cache.set("tour_status", new_status, timeout=None)
    return Response({"status": "ok", "message": "Tour status updated."}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_tour_status(request):
    """Fetches the current tour status (True/False)."""
    tour_status = cache.get("tour_status", False)  # Default: False
    return Response({"status": tour_status}, status=status.HTTP_200_OK)


# Store reboot status (default is False)
reboot_status_store = {"status": False}

@api_view(['POST'])
def update_reboot_status(request):
    """Update the reboot status (True/False)."""
    new_status = request.data.get("status", False)  # Get status from request

    if not isinstance(new_status, bool):  # Ensure it's a boolean
        return Response({"error": "Invalid status value. Must be true or false."}, status=status.HTTP_400_BAD_REQUEST)

    reboot_status_store["status"] = new_status  # Update status globally
    return Response({"message": "Reboot status updated", "status": reboot_status_store["status"]}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_reboot_status(request):
    """Retrieve the current reboot status."""
    return Response({"status": reboot_status_store["status"]}, status=status.HTTP_200_OK)



# robot_store.py
robot_data_store = {}
@api_view(['POST'])
def update_robot_status(request):
    try:
        robot_id = list(request.data.keys())[0]
        robot_info = request.data[robot_id]
        
        # Add timestamp to data
        robot_info['updated_at'] = datetime.now().isoformat()
        
        # Update or insert into in-memory store
        robot_data_store[robot_id] = robot_info
        
        return Response({
            "message": "Data updated",
            "robot_id": robot_id,
            "data": robot_info
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    


offline= {"status": False}

@api_view(['POST'])
def update_offline_status(request):
    """Update the reboot status (True/False)."""
    new_status = request.data.get("status", False)  # Get status from request

    if not isinstance(new_status, bool):  # Ensure it's a boolean
        return Response({"error": "Invalid status value. Must be true or false."}, status=status.HTTP_400_BAD_REQUEST)

    offline["status"] = new_status  # Update status globally
    return Response({"message": "Reboot status updated", "status": offline["status"]}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_offline_status(request):
    """Retrieve the current reboot status."""
    return Response({"status": offline["status"]}, status=status.HTTP_200_OK)



@api_view(['POST'])
def robot_battery_view(request):
    """
    Accepts JSON like:
    {
      "RB3": {
        "battery_status": 85
      }
    }
    """
    try:
        robot_id = list(request.data.keys())[0]  # e.g., "RB3"
        battery_status = request.data[robot_id].get("battery_status")

        if battery_status is None:
            return Response({"error": "battery_status is required."}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = RobotBattery.objects.update_or_create(
            robo_id=robot_id,
            defaults={'battery_status': battery_status}
        )

        serializer = RobotBatterySerializer(obj)
        
         # 🔥 WebSocket Broadcast
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
           "robot_group",
            {
                "type": "robot_battery_updates",
                "data": {
                    "event": "created" if created else "updated",
                    "robot_id": robot_id,
                    "battery_status": battery_status,
                }
            }
        )
        
        return Response({
            "message": "Created" if created else "Updated",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    


@api_view(['GET'])
def robot_battery_list(request):
    robots = RobotBattery.objects.all()
    serializer = RobotBatterySerializer(robots, many=True)

    # Convert the list to a dictionary with robot IDs as keys
    robot_dict = {
        "battery_status": robot["battery_status"]
        for robot in serializer.data
    }

    # Wrap the response with a status field
    return Response({
        "status": "ok",
        "data": robot_dict
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_or_replace_url(request):
    try:
        url_obj = URL.objects.first()  # Get the first (and only) object
        serializer = URLSerializer(url_obj, data=request.data)
    except URL.DoesNotExist:
        serializer = URLSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response({"status":"ok","message":"url added successfully","data":serializer.data}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def url_list(request):
    url_obj = URL.objects.first()  # Get the only object
    if url_obj:
        serializer = URLSerializer(url_obj)
        return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data}, status=status.HTTP_200_OK)
    else:
        return Response({"detail": "No URL found."}, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['POST'])
def create_or_update_charge(request):
    charge_obj, created = Charge.objects.get_or_create(id=1)

    serializer = ChargeSerializer(charge_obj, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
                # 🔥 WebSocket broadcast
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "robot_group",
            {
                "type": "charge_event",
                "data": {
                    "event": "created" if created else "updated",
                    "charge_id": charge_obj.id,
                    "payload": serializer.data,
                }
            }
        )
        return Response({
            "status": "ok",
            "message": "Charge updated successfully" if not created else "Charge created successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response({
        "status": "error",
        "message": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_current_charge(request):
    try:
        charge = Charge.objects.last()  # Get the latest one
        if not charge:
            return Response({"message": "No charge data found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChargeSerializer(charge )
        return Response({
            "status": "ok",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST', 'GET'])
def add_wishing_commands(request):
    try:
        if request.method == 'POST':
            serializer = DescriptionModelSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "status": "ok",
                    "message": "Description added successfully",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                "status": "error",
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'GET':
            descriptions = DescriptionModel.objects.filter(is_active=True)
            serializer = DescriptionModelSerializer(descriptions, many=True)
            return Response({
                "status": "ok",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def deactivate_description(request):
    pk = request.data.get('pk')
    try:
        # Fetch the DescriptionModel instance by its primary key (pk)
        description = DescriptionModel.objects.get(pk=pk)
        
        # Update the 'is_active' field to False
        description.is_active = False
        description.save()

        # Optionally, return the updated object in the response
        serializer = DescriptionModelSerializer(description)
        return Response({
            "status": "ok",
            "message": "Description deactivated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    except DescriptionModel.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Description not found"
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
def edit_description(request):
    pk = request.data.get('description_id')
    try:
        # Fetch the DescriptionModel instance by its primary key (pk)
        description = DescriptionModel.objects.get(pk=pk)

        # Update fields if they are provided in the request
        description.description = request.data.get('description' , description.description)
        # Add more fields here as needed

        description.save()

        # Return the updated object in the response
        serializer = DescriptionModelSerializer(description)
        return Response({
            "status": "ok",
            "message": "Description updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    except DescriptionModel.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Description not found"
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
  

    

@api_view(['PUT'])
def update_wishing_command(request, pk):
    try:
        try:
            instance = DescriptionModel.objects.get(pk=pk)
        except DescriptionModel.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Description not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = DescriptionModelSerializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "ok",
                "message": "Description updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            "status": "error",
            "message": "Invalid data.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def change_refresh_status(request):
    try:
        # Extract the 'status' value from the request data
        status_value = request.data.get('status')

        if status_value is None:
            return Response({
                "status": "error",
                "message": "Missing 'status' value in request."
            }, status=status.HTTP_400_BAD_REQUEST)

        # If only one RefreshButton instance is expected
        obj, created = RefreshButton.objects.get_or_create(id=1)  # or use a different condition
        obj.status = status_value
        obj.save()

        # Serialize and return the updated object
        serializer = RefreshButtonSerializer(obj)
        return Response({
            "status": "ok",
            "updated_data": serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def fetch_refresh_status(request):
    try:
        obj = RefreshButton.objects.filter(id=1).first()  # or use get() if you're sure it exists

        if obj is None:
            return Response({
                "status": "error",
                "message": "RefreshButton not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = RefreshButtonSerializer(obj)
        return Response({
            "status": "ok",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
def update_or_create_speed(request):
    sound, created = Speed.objects.get_or_create(id=1)  # Keep one record only

    serializer = SpeedSerializer(instance=sound, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "status": "ok",
            "message": "Speed value updated" if not created else "Speed created",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    return Response({
        "status": "error",
        "message": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_current_speed_value(request):
    try:
        sound = Speed.objects.first()  # Get the only sound object
        if sound:
            serializer = SpeedSerializer(sound)
            return Response({
                "status": "ok",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "error",
                "message": "No speed value found."
            }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    






def get_robot_upload_dir(stock_id):
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'stm_files', stock_id)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

@api_view(['POST'])
def upload_stcm_file(request, stock_id):
    """Upload or replace .stcm file for a robot_id"""
    serializer = STCMFileSerializer(data=request.data)
    
    if serializer.is_valid():
        file = serializer.validated_data['file']
        
        if not file.name.endswith('.stcm'):
            return Response({"error": "Only .stcm files are allowed"}, status=status.HTTP_400_BAD_REQUEST)

        # Construct path for this robot
        robot_dir = os.path.join(settings.MEDIA_ROOT, 'stm_files', stock_id)

        # If folder exists, delete existing .stcm files (replace case)
        if os.path.exists(robot_dir):
            for existing_file in os.listdir(robot_dir):
                if existing_file.endswith('.stcm'):
                    os.remove(os.path.join(robot_dir, existing_file))
        else:
            # If folder does not exist, create it (new file for new robot_id)
            os.makedirs(robot_dir, exist_ok=True)

        # Save the new file
        file_path = os.path.join(robot_dir, file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return Response({
            "message": "File uploaded successfully",
            "robot_id": stock_id,
            "file_name": file.name
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_latest_stcm_file(request, stock_id):
    """Get the latest uploaded .stcm file for a robot_id"""
    try:
        upload_dir = get_robot_upload_dir(stock_id)
        files = [f for f in os.listdir(upload_dir) if f.endswith('.stcm')]

        if not files:
            return Response({"message": "No .stcm files found"}, status=status.HTTP_404_NOT_FOUND)

        latest_file = files[0]
        file_url = request.build_absolute_uri(f"/stm_files/{stock_id}/{latest_file}")

        return Response({
            "latest_file": latest_file,
            "robot_id": stock_id,
            "file_url": file_url
        })

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_stcm_file(request, stock_id):
    """Delete uploaded .stcm file for a robot_id"""
    try:
        upload_dir = get_robot_upload_dir(stock_id)
        files = [f for f in os.listdir(upload_dir) if f.endswith('.stcm')]

        if not files:
            return Response({"message": "No .stcm files to delete"}, status=status.HTTP_404_NOT_FOUND)

        file_to_delete = os.path.join(upload_dir, files[0])
        os.remove(file_to_delete)

        return Response({"message": "File deleted", "robot_id": stock_id}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


@api_view(['GET'])
def get_charging_status(request):
    charging = Charging.objects.first()
    if charging:
        serializer = ChargingSerializer(charging)
        return Response(serializer.data)
    return Response({'status': None}, status=drf_status.HTTP_200_OK)

@api_view(['POST'])
def set_charging_status(request):
    status_value = request.data.get('status')

    if not isinstance(status_value, bool):
        return Response({'error': 'status must be true or false'}, status=drf_status.HTTP_400_BAD_REQUEST)

    Charging.objects.all().delete()  # ensure only one object
    serializer = ChargingSerializer(data={'status': status_value})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=drf_status.HTTP_201_CREATED)
    return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)








@api_view(['POST'])
def create_stcm_files(request):
    if request.method == 'POST':
        serializer = STCMFilesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_stcm_files(request, robot_id):
    try:
        ai_summary = STCMFiles.objects.get(robot_id=robot_id)
        serializer = STCMFilesSerializer(ai_summary)
        return Response(serializer.data)
    except STCMFiles.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['DELETE'])
def delete_stcm_files(request, robot_id):
    try:
        stcm_file = STCMFiles.objects.get(robot_id=robot_id)

        # Delete the file from the filesystem
        if stcm_file.stcm_file_path:
            stcm_file.stcm_file_path.delete(save=False)

        # Delete the database entry
        stcm_file.delete()
        local_store["status"] = True
        return Response(
            {"status":"ok",
            'detail': f'STCMFiles with robot_id {robot_id} has been deleted.'},
            status=status.HTTP_204_NO_CONTENT
        )

    except STCMFiles.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({'detail': f'Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
@api_view(['GET'])
def has_stcm_files(request, robot_id):
    try:
        # exists = STCMFiles.objects.filter(robot_id=robot_id).exists()
        # if exists:
        #     status_bool = False
        # else:
        #     status_bool = True
        return Response({'status': local_store["status"]}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'detail': f'Error: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
def set_home(request):
    status_value = request.data.get('status')

    if not isinstance(status_value, bool):
        return Response({'error': 'status must be true or false'}, status=drf_status.HTTP_400_BAD_REQUEST)

    Home.objects.all().delete()  # ensure only one object
    serializer = HomeSerializer(data={'status': status_value})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=drf_status.HTTP_201_CREATED)
    return Response(serializer.errors, status=drf_status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
def get_home_status(request):
    charging = Home.objects.first()
    if charging:
        serializer = HomeSerializer(charging)
        return Response(serializer.data)
    return Response({'status': None}, status=drf_status.HTTP_200_OK)


@api_view(['POST'])
def create_prompt(request):
    # Allow only one prompt — delete existing
    Prompt.objects.all().delete()
    
    serializer = PromptSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "ok", "message": "Prompt created.", "data": serializer.data}, status=status.HTTP_201_CREATED)
    return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_prompt(request):
    prompt = Prompt.objects.first()
    if prompt:
        serializer = PromptSerializer(prompt)
        return Response({"status": "ok", "data": serializer.data}, status=status.HTTP_200_OK)
    return Response({"status": "ok", "data": None, "message": "No prompt found."}, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_prompt(request, pk):
    try:
        prompt = Prompt.objects.get(pk=pk)
    except Prompt.DoesNotExist:
        return Response({"status": "error", "message": "Prompt not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = PromptSerializer(prompt, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "ok", "message": "Prompt updated.", "data": serializer.data}, status=status.HTTP_200_OK)
    return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_prompt(request, pk):
    try:
        prompt = Prompt.objects.get(pk=pk)
    except Prompt.DoesNotExist:
        return Response({"status": "error", "message": "Prompt not found."}, status=status.HTTP_404_NOT_FOUND)

    prompt.delete()
    return Response({"status": "ok", "message": "Prompt deleted."}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def create_prompt_qa(request):
    serializer = PromptQASerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "ok", "message": "QA added", "data": serializer.data}, status=status.HTTP_201_CREATED)
    return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def list_prompt_qas_by_prompt(request, prompt_id):
    try:
        prompt = Prompt.objects.get(pk=prompt_id)
    except Prompt.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Prompt not found"
        }, status=status.HTTP_404_NOT_FOUND)

    qas = PromptQA.objects.filter(prompt=prompt)
    serializer = PromptQASerializer(qas, many=True)
    return Response({
        "status": "ok",
        "prompt": prompt.command_prompt,
        "data": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_prompt_qa(request, pk):
    try:
        qa = PromptQA.objects.get(pk=pk)
    except PromptQA.DoesNotExist:
        return Response({"status": "error", "message": "QA not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = PromptQASerializer(qa, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({"status": "ok", "message": "QA updated", "data": serializer.data})
    return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_prompt_qa(request, pk):
    try:
        qa = PromptQA.objects.get(pk=pk)
    except PromptQA.DoesNotExist:
        return Response({"status": "error", "message": "QA not found"}, status=status.HTTP_404_NOT_FOUND)

    qa.delete()
    return Response({"status": "ok", "message": "QA deleted"}, status=status.HTTP_204_NO_CONTENT)



@api_view(['GET'])
def list_prompt_with_qas(request):
    prompts = Prompt.objects.prefetch_related('qas').all()
    data = []

    for prompt in prompts:
        command_text = f"Role:{prompt.command_prompt}"
        for qa in prompt.qas.all():
            command_text += f"\n {qa.question}\n {qa.answer}"
        
        data.append({
            "id": prompt.id,
            "command_prompt": command_text
        })

    return Response({
        "status": "ok",
        "data": data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def teaching_status_update(request):
    # Ensure only one object exists
    teaching_obj, created = Teaching.objects.get_or_create(id=1)

    # Toggle status if requested
    new_status = request.data.get('status')
    if new_status is not None:
        teaching_obj.status = bool(new_status)
        teaching_obj.save()

    serializer = TeachingSerializer(teaching_obj)
    return Response({
        'status': 'ok',
        'status_code': 200,
        'message': 'Teaching status updated successfully.',
        'data': serializer.data
    }, status=200)

@api_view(['GET'])
def get_teaching_status(request):
    try:
        teaching_obj = Teaching.objects.get(id=1)
        serializer = TeachingSerializer(teaching_obj)
        response_data = {
            'status': 'ok',
            'status_code': 200,
            'message': 'Current teaching status retrieved successfully.',
            'data': serializer.data
        }
    except Teaching.DoesNotExist:
        response_data = {
            'status': 'error',
            'status_code': 200,
            'message': 'Teaching status not initialized.',
            'data': None
        }

    return Response(response_data, status=200)


@api_view(['POST'])
def set_teaching_started(request):
    """
    Set teaching_started to True or False.
    Payload: {"status": true} or {"status": false}
    """
    try:
        status_value = request.data.get('status')

        if not isinstance(status_value, bool):
            return Response({"error": "status must be true or false"}, status=status.HTTP_400_BAD_REQUEST)

        obj, _ = Teaching.objects.get_or_create(id=1)
        obj.teaching_started = status_value
        obj.save()

        return Response({
            "status": obj.teaching_started,
            "message": f"Teaching started set to {obj.teaching_started}"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def is_teaching_started(request):
    """
    Get the current value of teaching_started
    """
    try:
        obj = Teaching.objects.get(id=1)
        return Response({"status": obj.teaching_started}, status=status.HTTP_200_OK)
    except Teaching.DoesNotExist:
        return Response({"status": False}, status=status.HTTP_200_OK)



@api_view(['POST'])
def create_subject(request):
    serializer = SubjectSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status":"ok","message":"subject created successfully","data":serializer.data}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def upload_pdf_document(request):
    serializer = PDFDocumentSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            "status": "ok",
            "message": "PDF uploaded successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({
        "status": "error",
        "message": "Invalid PDF upload.",
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def list_pdfs_by_subject(request, subject_id):
    # Check if the subject exists
    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all PDFs for this subject
    pdfs = PDFDocument.objects.filter(subject=subject).order_by('-uploaded_at')
    serializer = PDFDocumentSerializer(pdfs, many=True, context={'request': request})
    
    return Response({
        "subject": subject.name,
        "count": pdfs.count(),
        "pdfs": serializer.data
    })

@api_view(['PUT', 'PATCH'])
def edit_pdf_document(request, pdf_id):
    try:
        pdf = PDFDocument.objects.get(pk=pdf_id)
    except PDFDocument.DoesNotExist:
        return Response({"error": "PDF not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # If a new file is uploaded, remove the old one
    if 'file' in request.FILES and pdf.file:
        if os.path.exists(pdf.file.path):
            os.remove(pdf.file.path)

    # Allow partial updates (PATCH)
    serializer = PDFDocumentSerializer(pdf, data=request.data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            "status": "ok",
            "message": "PDF updated successfully",
            "data": serializer.data
        })
    
    return Response({
        "status": "error",
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_pdf_document(request, pdf_id):
    try:
        pdf = PDFDocument.objects.get(pk=pdf_id)
    except PDFDocument.DoesNotExist:
        return Response({"error": "PDF not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Delete the actual file from storage if it exists
    if pdf.file and os.path.exists(pdf.file.path):
        os.remove(pdf.file.path)
    
    # Delete the database record
    pdf.delete()
    
    return Response({
        "status": "ok",
        "message": f"PDF with id={pdf_id} deleted successfully"
    }, status=status.HTTP_200_OK)
    
@api_view(['GET'])
def subject_list(request):
    subjects = Subject.objects.all()
    serializer = SubjectSerializer(subjects, many=True)
    return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data})


@api_view(['PUT', 'PATCH'])
def subject_edit(request, pk):
    try:
        subject = Subject.objects.get(pk=pk)
    except Subject.DoesNotExist:
        return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)

    # PUT = full update, PATCH = partial update
    serializer = SubjectSerializer(subject, data=request.data, partial=(request.method == 'PATCH'))
    if serializer.is_valid():
        serializer.save()
        return Response({"status":"ok","message":"data updated successfully","data":serializer.data})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def subject_detail(request, pk):
    try:
        subject = Subject.objects.get(pk=pk)
    except Subject.DoesNotExist:
        return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = SubjectSerializer(subject)
    return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data})

@api_view(['DELETE'])
def subject_delete(request, pk):
    try:
        subject = Subject.objects.get(pk=pk)
    except Subject.DoesNotExist:
        return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)

    subject.delete()
    return Response({"message": "Subject deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
def lastmodule_replace_view(request):
    lastmodule = Lastmodule.objects.first()

    if lastmodule:
        serializer = LastmoduleSerializer(lastmodule, data=request.data, context={'request': request})
    else:
        serializer = LastmoduleSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        instance = serializer.save()
        return Response(LastmoduleSerializer(instance, context={'request': request}).data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def lastmodule_list_view(request):
    lastmodule = Lastmodule.objects.first()
    if not lastmodule:
        return Response({"detail": "No Lastmodule found"}, status=404)

    # Expiry logic (optional)
    
    if (timezone.now() - lastmodule.updated_at) > timedelta(seconds=30):
        return Response({"detail": "Expired"}, status=410)

    serializer = LastmoduleSerializer(lastmodule, context={'request': request})  # ✅ pass request
    return Response(serializer.data)

@api_view(['GET', 'POST'])
def camera_toggle_view(request):
    # There should only be one toggle object, create if not exists
    toggle_obj, _ = CameraToggle.objects.get_or_create(id=1)

    if request.method == 'GET':
        serializer = ToggleHandlerSerializer(toggle_obj)
        return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data}, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        toggle = request.data.get('toggle')
        # Flip the boolean
        toggle_obj.tog_bool = toggle
        toggle_obj.save()
        serializer = ToggleHandlerSerializer(toggle_obj)
        return Response({"status":"ok","message":"data toggled successfully","data":serializer.data}, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
def person_data_view(request):
    if request.method == 'GET':
        person_data = FaceDetData.objects.order_by('-updated_at').first()

        if person_data is None:
            return Response({
                "status": "error",
                "message": "No data found",
                "data": None
            }, status=status.HTTP_200_OK)

        serializer = FaceDetDataSerializer(person_data)

        if person_data.is_failed:
            return Response({
                "status": "error",
                "message": "An uncompleted person found. Delete the previous one?",
                "data": serializer.data
            }, status=status.HTTP_409_CONFLICT)

        if person_data.is_completed:
            return Response({
                "status": "info",
                "message": "No new names added",
                "data": None
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "ok",
            "message": "Uncompleted person data fetched.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        name = request.data.get('name')
        if not name:
            return Response({
                "status": "error",
                "message": "Name is required.",
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for duplicate
        existing = FaceDetData.objects.filter(name=name).first()
        if existing:
            if not existing.is_completed:
                serializer = FaceDetDataSerializer(existing)
                return Response({
                    "status": "error",
                    "message": "Uncompleted person with this name exists. Delete the previous one?.",
                    "data": serializer.data
                }, status=status.HTTP_409_CONFLICT)
            else:
                return Response({
                    "status": "error",
                    "message": "This name already exists.",
                    "data": None
                }, status=status.HTTP_409_CONFLICT)

        # Check for latest record
        latest = FaceDetData.objects.order_by('-updated_at').first()
        if latest and not latest.is_completed:
            serializer = FaceDetDataSerializer(latest)
            return Response({
                "status": "error",
                "message": "Previous person data is not completed. Delete the previous one?.",
                "data": serializer.data
            }, status=status.HTTP_409_CONFLICT)

        # Create new
        serializer = FaceDetDataSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "message": "Data created",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "error",
                "message": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def update_person_data_view(request):
    name = request.data.get('name')
    if not name:
        return Response({
            "status": "error",
            "message": "Name is required.",
            "data": None
        }, status=status.HTTP_400_BAD_REQUEST)
    is_failed = request.data.get('is_failed',False)
    if is_failed is None:
        return Response({
            "status": "error",
            "message": "Failed bool is required.",
            "data": None
        }, status=status.HTTP_400_BAD_REQUEST)
    is_completed = request.data.get('is_completed')
    if is_completed is None:
        return Response({
            "status": "error",
            "message": "Completed bool is required.",
            "data": None
        }, status=status.HTTP_400_BAD_REQUEST)
    try:
        obj = FaceDetData.objects.get(name=name)
        obj.is_failed = is_failed
        obj.is_completed = is_completed
        obj.save()
        return Response({
            "status": "success",
            "message": "Data updated successfully",
            "data": FaceDetDataSerializer(obj).data
        }, status=status.HTTP_200_OK)
    except FaceDetData.DoesNotExist:
        return Response({
            "status": "error",
            "message": f"No record found for name '{name}'",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def delete_person_data_view(request):
    name = request.data.get('name')
    if not name:
        return Response({
            "status": "error",
            "message": "Name is required.",
            "data": None
        }, status=status.HTTP_400_BAD_REQUEST)

    deleted, _ = FaceDetData.objects.filter(name=name).delete()
    if deleted == 0:
        return Response({
            "status": "error",
            "message": "No such name found to delete.",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "status": "success",
        "message": "Data deleted",
        "data": None
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def joystick_view(request):
    if request.method == 'POST':
        joystick = Joystick.objects.first()  # Get the first and only object if exists

        if joystick:
            serializer = JoystickSerializer(joystick, data=request.data, partial=True)
            action_message = "Joystick updated successfully"
        else:
            serializer = JoystickSerializer(data=request.data)
            action_message = "Joystick created successfully"

        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "ok",
                "message": action_message,
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            "status": "error",
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        joystick = Joystick.objects.first()
        if joystick:
            serializer = JoystickSerializer(joystick)
            return Response({
                "status": "ok",
                "message": "Joystick data fetched successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            "status": "error",
            "message": "No joystick data available",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)
    


@api_view(['POST'])
def appointment_create_or_update(request):
    data = request.data

    # Only allow one record
    obj, created = Appointment.objects.update_or_create(
        id=1,  # always overwrite object with id=1
        defaults={'status': data.get('status', False)}
    )

    serializer = AppointmentSerializer(obj)
    return Response({
        "status": "ok",
        "message": "Created successfully" if created else "Updated successfully",
        "data": serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def appointment_get(request):
    obj = Appointment.objects.first()
    if obj:
        serializer = AppointmentSerializer(obj)
        return Response({
            "status": "ok",
            "message": "Data retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "status": "ok",
            "message": "No data found",
            "data": None
        }, status=status.HTTP_200_OK)
    
@api_view(['POST'])
def create_mode(request):
    serializer = ModeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status":"ok","message":"data created successfully","data":serializer.data}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_modes(request):
    modes = Mode.objects.all()
    serializer = ModeSerializer(modes, many=True)
    return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data})

@api_view(['PUT'])
def update_mode(request, pk):
    try:
        mode = Mode.objects.get(pk=pk)
    except Mode.DoesNotExist:
        return Response({'error': 'Mode not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ModeSerializer(mode, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status":"ok","message":"data updated successfully","data":serializer.data})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_mode(request, pk):
    try:
        mode = Mode.objects.get(pk=pk)
    except Mode.DoesNotExist:
        return Response({'error': 'Mode not found'}, status=status.HTTP_404_NOT_FOUND)

    mode.delete()
    return Response({'message': 'Mode deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def detail_mode(request, pk):
    try:
        mode = Mode.objects.get(pk=pk)
    except Mode.DoesNotExist:
        return Response({'error': 'Mode not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ModeSerializer(mode)
    return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data})


@api_view(['POST'])
def create_gesture(request):
    serializer = GesturesSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status":"ok","message":"data created successfully","data":serializer.data}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def list_gestures(request):
    gestures = Gestuers.objects.all()
    serializer = GesturesSerializer(gestures, many=True)
    return Response({"status":"ok","message":"data created successfully","data":serializer.data})


@api_view(['PUT'])
def edit_gesture(request, pk):
    gesture = get_object_or_404(Gestuers, pk=pk)
    serializer = GesturesSerializer(gesture, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"status":"ok","message":"data updated succesfully","data":serializer.data})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def gesture_detail(request, pk):
    gesture = get_object_or_404(Gestuers, pk=pk)
    serializer = GesturesSerializer(gesture)
    return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data})

@api_view(['DELETE'])
def delete_gesture(request, pk):
    gesture = get_object_or_404(Gestuers, pk=pk)
    gesture.delete()
    return Response({"status":"ok","message": "Gesture deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def assign_gesture_to_mode(request):
    serializer = GestureAssignmentSerializer(data=request.data)
    if serializer.is_valid():
        mode = serializer.validated_data['mode']
        gesture = serializer.validated_data['gesture']

        # Check if this mode already has an assignment
        assignment, created = GestureAssignment.objects.update_or_create(
            mode=mode,
            defaults={'gesture': gesture}
        )

        # Return the updated/created assignment
        output_serializer = GestureAssignmentSerializer(assignment)
        return Response({"status":"ok","message":"data created successfully","data":output_serializer.data}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
def list_gesture_assignments(request):
    assignments = GestureAssignment.objects.all()
    serializer = GestureAssignmentSerializer(assignments, many=True)
    return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data})

@api_view(['DELETE'])
def delete_gesture_assignment(request, pk):
    assignment = get_object_or_404(GestureAssignment, pk=pk)
    assignment.delete()
    return Response({"message": "Gesture assignment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def set_last_clicked_mode(request):
    """
    Set a mode as last clicked.
    Only one mode can have is_last_clicked=True at a time.
    """
    mode_id = request.data.get('mode_id')
    if not mode_id:
        return Response({"error": "mode_id is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    mode = get_object_or_404(Mode, pk=mode_id)
    
    # Set all modes to is_last_clicked=False
    Mode.objects.update(is_last_clicked=False)
    
    # Set this mode as last clicked
    mode.is_last_clicked = True
    mode.save()
    
    serializer = ModeSerializer(mode)
    return Response({"status":"ok","message":"data created successfully","data":serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
def last_clicked_mode_detail(request):
    """
    Get the Mode marked as last clicked with its related GestureAssignments.
    """
    mode = Mode.objects.filter(is_last_clicked=True).first()
    if not mode:
        return Response({"message": "No last clicked mode found"}, status=404)
    
    serializer = LastClickedModeSerializer(mode)
    return Response({"status":"ok","message":"data retrieved successfully","data":serializer.data})



@api_view(['POST'])
def entertainment_view(request):
    # Try to get the object (id=1) or create it
    obj, created = Entertainment.objects.get_or_create(id=1)

    serializer = EntertainmentSerializer(obj, data=request.data)
    if serializer.is_valid():
        serializer.save()

        # Determine status
        action = "created" if created else "updated"

        # 🔥 Send WebSocket event
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "robot_group",       # must match group_name in consumer
            {
                "type": "entertainment_updated",  # matches consumer function
                "action": action,
                "data": serializer.data
            }
        )

        # Return REST response
        return Response(
            {
                "status": "ok",
                "message": f"Entertainment {action} successfully",
                "data": serializer.data,
                "action": action
            },
            status=200
        )

    return Response(serializer.errors, status=400)


@api_view(['GET'])
def entertainment_status(request):
    try:
        obj = Entertainment.objects.get(id=1)
        serializer = EntertainmentSerializer(obj)
        return Response({
            "status": "OK",
            "message": "Data retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Entertainment.DoesNotExist:
        return Response({
            "status": "Error",
            "message": "No Entertainment object found",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['POST'])
def upload_song(request):
    serializer = SongSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        song = serializer.save()
        return Response({
            "status": "OK",
            "message": "Song uploaded successfully",
            "data": SongSerializer(song, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def list_songs(request):
    songs = Song.objects.all()
    serializer = SongSerializer(songs, many=True, context={'request': request})
    return Response({
        "status": "OK",
        "message": "Songs retrieved successfully",
        "data": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
def edit_song(request, song_id):
    """
    Edit an existing song by ID
    """
    try:
        song = Song.objects.get(id=song_id)
    except Song.DoesNotExist:
        return Response({
            "status": "Error",
            "message": "Song not found",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)

    serializer = SongSerializer(song, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({
            "status": "OK",
            "message": "Song updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def song_detail(request, song_id):
    """
    Retrieve details of a single song by ID
    """
    try:
        song = Song.objects.get(id=song_id)
        serializer = SongSerializer(song, context={'request': request})
        return Response({
            "status": "OK",
            "message": "Song retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Song.DoesNotExist:
        return Response({
            "status": "Error",
            "message": "Song not found",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
def delete_song(request, song_id):
    """
    Delete a song by ID
    """
    try:
        song = Song.objects.get(id=song_id)
        song.delete()
        return Response({
            "status": "OK",
            "message": "Song deleted successfully",
            "data": None
        }, status=status.HTTP_200_OK)
    except Song.DoesNotExist:
        return Response({
            "status": "Error",
            "message": "Song not found",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def set_last_clicked_song(request):
    """
    Set a song as last clicked.
    """
    song_id = request.data.get('song_id')
    if not song_id:
        return Response({"status": "Error", "message": "song_id is required", "data": None}, status=status.HTTP_400_BAD_REQUEST)

    try:
        song = Song.objects.get(id=song_id)
    except Song.DoesNotExist:
        return Response({"status": "Error", "message": "Song not found", "data": None}, status=status.HTTP_404_NOT_FOUND)

    # Reset last_clicked for all songs
    Song.objects.update(last_clicked=False)

    # Set this song as last clicked
    song.last_clicked = True
    song.save()

    serializer = SongSerializer(song, context={'request': request})
    return Response({"status": "OK", "message": "Last clicked song updated", "data": serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_last_clicked_song(request):
    """
    Retrieve the last clicked song.
    """
    try:
        song = Song.objects.get(last_clicked=True)
        serializer = SongSerializer(song, context={'request': request})
        return Response({"status": "OK", "message": "Last clicked song retrieved", "data": serializer.data}, status=status.HTTP_200_OK)
    except Song.DoesNotExist:
        return Response({"status": "Error", "message": "No last clicked song found", "data": None}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def set_calibration_status(request):
    """
    Create or update a single Calibration object.
    """
    # Always use the first object, or create one
    obj, created = Calibration.objects.get_or_create(id=1)
    
    serializer = CalibrationSerializer(obj, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "status": "OK",
            "message": "Calibration status updated",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_calibration_status(request):
    """
    Retrieve the current calibration status.
    """
    try:
        obj = Calibration.objects.get(id=1)
        serializer = CalibrationSerializer(obj)
        return Response({
            "status": "OK",
            "message": "Calibration status retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Calibration.DoesNotExist:
        return Response({
            "status": "Error",
            "message": "No calibration record found",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)
    


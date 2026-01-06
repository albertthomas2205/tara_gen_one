from .models import PowerOn

def get_poweron_object():
    poweron, created = PowerOn.objects.get_or_create(id=1)  # Ensure only one instance exists
    return poweron
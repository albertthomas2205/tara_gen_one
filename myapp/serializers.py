from rest_framework import serializers
from .models import *

class NavigationSerializer(serializers.ModelSerializer):
    video = serializers.SerializerMethodField()

    class Meta:
        model = Navigation
        fields = ['id', 'name', 'description', 'video','name1']

    def get_video(self, obj):
        request = self.context.get('request')
        if obj.video and hasattr(obj.video, 'url'):
            return request.build_absolute_uri(obj.video.url) if request else obj.video.url
        return None


class STCMFileSerializer(serializers.Serializer):
    file = serializers.FileField()


class FullTourSerializer(serializers.ModelSerializer):
    navigations = serializers.SerializerMethodField()

    class Meta:
        model = FullTour
        fields = ['id', 'navigations']

    def get_navigations(self, obj):
        # Retrieve navigations in the order stored in JSONField
        navigations = {nav.id: nav for nav in Navigation.objects.filter(id__in=obj.navigations)}
        ordered_navigations = [navigations[nav_id] for nav_id in obj.navigations if nav_id in navigations]
        return NavigationSerializer(ordered_navigations, many=True).data
class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ['id', 'key', 'created_at']
        read_only_fields = ['id', 'created_at']


class RobotBatterySerializer(serializers.ModelSerializer):
    class Meta:
        model = RobotBattery
        fields = ['robo_id', 'battery_status']


class URLSerializer(serializers.ModelSerializer):
    class Meta:
        model = URL
        fields = ['id', 'name', 'url']


class ChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charge
        fields = ['id', 'low_battery_entry', 'back_to_home_entry']

class DescriptionModelSerializer(serializers.ModelSerializer):
    time_of_day_display = serializers.CharField(source='get_time_of_day_display', read_only=True)

    class Meta:
        model = DescriptionModel
        fields = ['id', 'time_of_day', 'time_of_day_display', 'description']



class RefreshButtonSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefreshButton
        fields = ['id' , 'status']

class SpeedSerializer(serializers.ModelSerializer):
    value = serializers.FloatField(min_value=0.1, max_value=0.7)

    class Meta:
        model = Speed
        fields = ['id', 'value']

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        # Convert float to string before saving
        data['value'] = str(data['value'])
        return data
    
class STCMFileSerializer(serializers.Serializer):
    file = serializers.FileField()

class ChargingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charging
        fields = ['status']

class STCMFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = STCMFiles
        fields = ['robot_id', 'stcm_file_path', 'created_at']

    # Custom validation to ensure only one STCMFiles for each robot_id
    def validate_robot_id(self, value):
        if STCMFiles.objects.filter(robot_id=value).exists():
            raise serializers.ValidationError(f"An STCMFiles for robot_id {value} already exists.")
        return value
    

class HomeSerializer(serializers.ModelSerializer):
    class Meta:
        model=Home
        fields=['status']


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = ['id', 'command_prompt']


class PromptQASerializer(serializers.ModelSerializer):
    command_prompt = serializers.CharField(source='prompt.command_prompt', read_only=True)

    class Meta:
        model = PromptQA
        fields = ['id', 'prompt', 'command_prompt', 'question', 'answer']


class TeachingSerializer(serializers.ModelSerializer):
    class Meta:
        model=Teaching
        fields=['id','status']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name'] 

class PDFDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField()
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())  
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = PDFDocument
        fields = [
            'id',
            'subject',       # Foreign key (writeable)
            'subject_name',  # Read-only subject name
            'module_name',
            'file',
            'uploaded_at',
            'ppt_file'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.file:
            data['file'] = request.build_absolute_uri(instance.file.url)
        return data

    def validate_file(self, value):
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value


class LastmoduleSerializer(serializers.ModelSerializer):
    pdf = serializers.PrimaryKeyRelatedField(queryset=PDFDocument.objects.all())

    class Meta:
        model = Lastmodule
        fields = ['id', 'pdf']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Replace the PDF ID with full serialized data
        rep['pdf'] = PDFDocumentSerializer(instance.pdf, context=self.context).data
        return rep

class ToggleHandlerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraToggle
        fields = ['id','tog_bool','updated_at']

class FaceDetDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaceDetData
        fields = ['id','name','is_completed','is_failed']

class JoystickSerializer(serializers.ModelSerializer):
    class Meta:
        model = Joystick
        fields = ['id', 'direction', 'distance']

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['id', 'status']


class ModeSerializer(serializers.ModelSerializer):
    class Meta:
        model=Mode
        fields=['id','name']

class GesturesSerializer(serializers.ModelSerializer):
    class Meta:
        model=Gestuers
        fields=['id','name']

class GestureAssignmentSerializer(serializers.ModelSerializer):
    mode = ModeSerializer(read_only=True)
    gesture = GesturesSerializer(read_only=True)

    mode_id = serializers.PrimaryKeyRelatedField(
        queryset=Mode.objects.all(), source='mode', write_only=True
    )
    gesture_id = serializers.PrimaryKeyRelatedField(
        queryset=Gestuers.objects.all(), source='gesture', write_only=True
    )

    class Meta:
        model = GestureAssignment
        fields = ['id', 'mode', 'gesture', 'mode_id', 'gesture_id']

class LastClickedModeSerializer(serializers.ModelSerializer):
    assignments = GestureAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Mode
        fields = ['id', 'name', 'is_last_clicked', 'assignments']

class EntertainmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entertainment
        fields = '__all__' 

class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = '__all__'

class CalibrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calibration
        fields = '__all__'


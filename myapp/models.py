from django.db import models

class PowerOn(models.Model):
    status = models.BooleanField(default=True) 

    def __str__(self):
        return f"PowerOn status: {self.status}"

class Navigation(models.Model):
    name=models.CharField(max_length=100,null=True,blank=True,unique=True)
    name1=models.CharField(max_length=300,null=True,blank=True)
    description=models.TextField(null=True,blank=True)
    video = models.FileField(upload_to='videos/', null=True, blank=True) 
    
    def __str__(self):
        return self.name
    

class FullTour(models.Model):
    navigations = models.JSONField(default=list)  # Store ordered navigation IDs


class APIKey(models.Model):
    key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"API Key ({self.created_at})"
    

class RobotBattery(models.Model):
    robo_id = models.CharField(max_length=50, unique=True)
    battery_status = models.CharField(max_length=100,null=True,blank=True)


class URL(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField()

    def __str__(self):
        return self.name


class Charge(models.Model):
    low_battery_entry = models.IntegerField(default=10)
    back_to_home_entry = models.IntegerField(default=80)

    def __str__(self):
        return f"Low Battery: {self.low_battery_entry}, Back to Home: {self.back_to_home_entry}"
    
class DescriptionModel(models.Model):
    TIME_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ('night', 'Night'),
    ]
    
    time_of_day = models.CharField(max_length=10, choices=TIME_CHOICES)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_time_of_day_display()} - {self.description[:30]}"



    
class RefreshButton(models.Model):

    status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.status}"
    


class Speed(models.Model):
    value = models.CharField(
        max_length=10,
        default="0.1"
    )

    def __str__(self):
        return f"Speed Value: {self.value}"
    


class Charging(models.Model):
    status = models.BooleanField(default=False)

    def __str__(self):
        return "Charging" if self.status else "Not Charging"


class STCMFiles(models.Model):
    robot_id = models.TextField(unique=True)
    stcm_file_path = models.FileField(upload_to='RB2/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.robot_id} - {self.created_at}"
    

class Home(models.Model):
    status=models.BooleanField(default=False)
    def __str__(self):
        return self.status
    
class Prompt(models.Model):
    command_prompt=models.TextField(null=True,blank=True)
    def __str__(self):
        return self.command_prompt


class PromptQA(models.Model):
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE, related_name='qas')
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return f"Q: {self.question} → A: {self.answer[:30]}..."
    

class Teaching(models.Model):
    status=models.BooleanField(default=False,null=True,blank=True)
    teaching_started=models.BooleanField(default=False,null=True,blank=True)
    def __str__(self):
        return self.status
class Subject(models.Model):
    name=models.CharField(max_length=500,null=True,blank=True,unique=True)
    def __str__(self):
        return self.name
    

class PDFDocument(models.Model):
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE,   
        related_name='pdfs'  ,null=True,blank=True      
    )
    module_name = models.CharField(max_length=255,null=True,blank=True)  # module name for the PDF
    file = models.FileField(upload_to='Teaching/pdfs/') 
    uploaded_at = models.DateTimeField(auto_now_add=True)
    ppt_file = models.FileField(upload_to='Teaching/ppt/',null=True,blank=True) 

    def __str__(self):
        return f"{self.module_name} ({self.subject})"
    
class Lastmodule(models.Model):
    pdf = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='lastpdf', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)  # auto-update timestamp

    def __str__(self):
        return f"Lastmodule → {self.pdf.module_name if self.pdf else 'None'}"
    
class CameraToggle(models.Model):
    tog_bool = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"camera toggle is toggled {self.tog_bool}"
    
class FaceDetData(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_completed = models.BooleanField(default=False)
    is_failed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} completion is {self.is_completed} , failed = {self.is_failed}"
    
class Joystick(models.Model):
    direction=models.CharField(max_length=300,null=True,blank=True)
    distance=models.CharField(max_length=300,null=True,blank=True)
    def __str__(self):
        return self.direction
    

class Appointment(models.Model):
    status = models.BooleanField(default=False) 

    def __str__(self):
        return self.status
    
class Mode(models.Model):
    name=models.CharField(max_length=400,null=True,blank=True)
    is_last_clicked = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
class Gestuers(models.Model):
    name=models.CharField(max_length=400,null=True,blank=True)
    
    def __str__(self):
        return self.name
    
class GestureAssignment(models.Model):
    mode = models.ForeignKey(Mode, on_delete=models.CASCADE, related_name="assignments")
    gesture = models.ForeignKey(Gestuers, on_delete=models.CASCADE, related_name="assignments")

    def __str__(self):
        return f"{self.gesture.name} → {self.mode.name}"
    

class Entertainment(models.Model):
    status = models.BooleanField(default=False) 

    def __str__(self):
        return self.status
    
class Song(models.Model):
    name = models.CharField(max_length=500,null=True,blank=True)
    file = models.FileField(upload_to='songs/',null=True,blank=True) 
    last_clicked = models.BooleanField(default=False)
    def __str__(self):
        return self.name
    
class Calibration(models.Model):
    status = models.BooleanField(default=False)

    def __str__(self):
        return str(self.status)

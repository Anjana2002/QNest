from django.db import models
from django.contrib.auth.models import User


class Template(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    template_name = models.CharField(max_length=255)  
    exam_title = models.CharField(max_length=255)  # Exam Title
    course_code = models.CharField(max_length=50)  # Course Code
    course_name = models.CharField(max_length=255)  # Course Name
    time_duration = models.CharField(max_length=50)  # Example: "3 Hours"
    max_marks = models.IntegerField()  # Example: 40 Marks
    sections = models.JSONField()  # Store section details like {"A": {"questions": 6, "marks": 1}}
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.template_name} - {self.course_name}"

class GeneratedPDF(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    template = models.ForeignKey('Template', on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to='generated_pdfs/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PDF by {self.user.username} for {self.template.template_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
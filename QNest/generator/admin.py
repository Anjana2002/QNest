from django.contrib import admin
from .models import StudyMaterial, PreviousQuestionPaper, Template

# Register the models
admin.site.register(StudyMaterial)
admin.site.register(PreviousQuestionPaper)
admin.site.register(Template)
from django.contrib import admin
from .models import  Template,  GeneratedPDF

# Register the models

admin.site.register(Template)
admin.site.register(GeneratedPDF)
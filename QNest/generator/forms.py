from django import forms
from .models import StudyMaterial, PreviousQuestionPaper

class StudyMaterialForm(forms.ModelForm):
    class Meta:
        model = StudyMaterial
        fields = ['title']

class PreviousQuestionPaperForm(forms.ModelForm):
    class Meta:
        model = PreviousQuestionPaper
        fields = ['title']

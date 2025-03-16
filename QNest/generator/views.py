from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from .models import StudyMaterial, PreviousQuestionPaper, Template
from PyPDF2 import PdfReader
import ollama
import json
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit

def home(request):
    """Login Page"""
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("upload_files") 
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "home.html")

def register(request):
    """User Registration"""
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect("register")

        # Create user
        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Account created successfully! Please log in.")
        return redirect("home")

    return render(request, "register.html")

def user_logout(request):
    """Logout User"""
    logout(request)
    return redirect("home")

def extract_text_from_pdf(pdf):
    """Extract text from an uploaded PDF file"""
    reader = PdfReader(pdf)
    text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return text



@login_required
def upload_files(request):
    """Handle question paper generation"""
    if request.method == "POST":
        template_id = request.POST.get("template_id")

        # Validate template
        try:
            template = Template.objects.get(id=template_id, user=request.user)
        except Template.DoesNotExist:
            return JsonResponse({"error": "Invalid template selected."}, status=400)

        # Extract study material (Mandatory)
        study_materials = request.FILES.getlist("study_material")
        if not study_materials:
            return JsonResponse({"error": "Study material is required."}, status=400)

        study_texts = [extract_text_from_pdf(pdf) for pdf in study_materials]
        study_text = "\n\n".join(study_texts)

        # Extract previous question paper (Optional)
        prev_texts = [extract_text_from_pdf(pdf) for pdf in request.FILES.getlist("previous_question", [])]
        prev_text = "\n\n".join(prev_texts) if prev_texts else ""

        # Format sections
        sections_formatted = "\n".join([
            f"**{section}**\n- Questions: {details['questions']}\n- Marks per Question: {details['marks_per_question']}\n- Instructions: {details['instructions']}"
            for section, details in template.sections.items()
        ])

        # Construct prompt for Ollama
        prev_qstn_text = f"### **Previous Exam Paper (Use for Reference, But Do NOT Repeat Questions):**\n{prev_text[:4000]}" if prev_text else ""
        prompt = f"""
        You are an expert in university-level question paper creation.
        **Strictly follow the given template** to structure the question paper.

        ### **Generated Question Paper Format (Follow This Exactly):**
        **Name:** ________________  
        **Reg No:** ________________  
        **{template.exam_title}**  
        **Course Code:** {template.course_code}  
        **Course Name:** {template.course_name}  
        **Time Duration:** {template.time_duration}  
        **Max Marks:** {template.max_marks}  

        ### **Sections (Use These Exactly):**
        {sections_formatted}

        {prev_qstn_text}

        ### **Study Material (Use to Generate Questions):**  
        {study_text[:4000]}

        🔹 **Rules:**  
        1. Follow the exact template structure.  
        2. Use the previous exam paper as a reference (if provided), but don't repeat questions.  
        3. Ensure university-level difficulty.  
        4. Maintain proper formatting.

        **Generate Question Paper:**  
        """

        # Call the AI model
        response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
        questions = response["message"]["content"]

        if not questions.strip():
            return JsonResponse({"error": "Question generation failed. No response from the model."}, status=500)

        return JsonResponse({"question_paper": questions})

    templates = Template.objects.filter(user=request.user)
    return render(request, "upload.html", {"templates": templates})
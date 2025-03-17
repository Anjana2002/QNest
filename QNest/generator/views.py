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
@csrf_protect
def create_template(request):
    """Handles template creation and saves it to the database."""
    
    if request.method =="GET":
        return render(request, "create_template.html")

    if request.method == "POST":
        try:
            template_name = request.POST.get("template_name", "").strip()
            exam_title = request.POST.get("exam_title", "").strip()
            course_code = request.POST.get("course_code", "").strip()
            course_name = request.POST.get("course_name", "").strip()
            time_duration = request.POST.get("time_duration", "").strip()
            max_marks = request.POST.get("max_marks", "0").strip()

            # Ensure required fields are present
            if not template_name or not exam_title or not course_code or not course_name or not time_duration:
                return JsonResponse({"error": "All fields are required"}, status=400)

            # Convert max_marks safely
            try:
                max_marks = int(max_marks)
            except ValueError:
                return JsonResponse({"error": "Invalid max marks value"}, status=400)

            # Extract sections
            sections = []
            section_names = request.POST.getlist("section_name[]")
            num_questions = request.POST.getlist("num_questions[]")
            marks_per_question = request.POST.getlist("marks_per_question[]")
            instructions = request.POST.getlist("instructions[]")

            for i in range(len(section_names)):
                sections.append({
                    "section_name": section_names[i].strip(),
                    "questions": int(num_questions[i]),
                    "marks_per_question": int(marks_per_question[i]),
                    "instructions": instructions[i].strip()
                })

            # Save template to DB
            template = Template.objects.create(
                user=request.user,
                template_name=template_name,
                exam_title=exam_title,
                course_code=course_code,
                course_name=course_name,
                time_duration=time_duration,
                max_marks=max_marks,
                sections=sections
            )

            messages.success(request, "Template saved successfully!")
            return redirect("upload_files")  

        except Exception as e:
            return JsonResponse({"error": f"Error saving template: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)


@login_required
@csrf_protect
def upload_files(request):
    if request.method == "POST":
        print("Received POST request:", request.POST)  

        if "create_template" in request.POST:
            return create_template(request)

        # ✅ Handle Question Paper Generation
        elif "generate_question_paper" in request.POST:
            print("Generating question paper...")  # Debugging

            template_id = request.POST.get("template_id")

            # Validate template selection
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

            if not study_text.strip():
                return JsonResponse({"error": "Study material text extraction failed."}, status=400)

            # Extract previous question paper (Optional)
            prev_texts = [extract_text_from_pdf(pdf) for pdf in request.FILES.getlist("previous_question", [])]
            prev_text = "\n\n".join(prev_texts) if prev_texts else ""

            # ✅ Construct the prompt
            prev_qstn_text = f"### **Previous Exam Paper (Use as Reference, Do NOT Repeat Questions):**\n{prev_text[:4000]}" if prev_text else ""

            # **Format template sections strictly**
            sections_formatted = "\n".join([
                f"**{section['section_name']}**\n- Questions: {section['questions']}\n- Marks per Question: {section['marks_per_question']}\n- Instructions: {section['instructions']}\n"
                for section in template.sections 
            ])


            # 🔹 **Final Prompt**
            prompt = f"""
            You are an expert in university-level question paper creation.
            **Strictly follow the provided template** to structure the question paper.
            Do **NOT** create any new structure. Do **NOT** modify the number of sections, numbering, or total marks.

            ### **Question Paper Format (Follow This Exactly):**
            **Name:** ________________  
            **Reg No:** ________________  

            **{template.exam_title}**  
            **Course Code:** {template.course_code}  
            **Course Name:** {template.course_name}  
            **Time Duration:** {template.time_duration}  
            **Max Marks:** {template.max_marks}  

            ### **Sections (Follow These Exactly)**  
            {sections_formatted}

            {prev_qstn_text}

            ### **Study Material (Use to Generate New Questions, No Copy-Pasting):**  
            {study_text[:4000]}

            🔹 **Rules for Generation:**  
            1. **Follow the exact structure of the template.** Keep the same **number of sections, questions, and marks per question.**  
            2. **Use the previous exam paper as a reference (if provided), but DO NOT repeat questions.**  
            3. **Do NOT modify the question numbering, section names, or formatting.**  
            4. **Ensure difficulty is appropriate for university-level exams.**

            **Generate the Final Question Paper Below (Follow Formatting Exactly):**
            """

            print("Sending prompt to Ollama...")  # Debugging

            try:
                response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
                print("Ollama Response:", response)  # Debugging

                if "message" not in response or "content" not in response["message"]:
                    return JsonResponse({"error": "Invalid response from the model."}, status=500)

                questions = response["message"]["content"].strip()
                if not questions:
                    return JsonResponse({"error": "Question generation failed. No response from the model."}, status=500)

                print("Generated questions:", questions)  # Debugging
                return JsonResponse({"question_paper": questions})

            except Exception as e:
                print("Error calling Ollama:", str(e))  # Debugging
                return JsonResponse({"error": f"Ollama request failed: {str(e)}"}, status=500)

  
    templates = Template.objects.filter(user=request.user).order_by("id") 
    print("Templates in DB:", list(Template.objects.filter(user=request.user)))  
    print("Templates Passed to Template:", list(templates)) 
    return render(request, "upload.html", {"templates": templates})
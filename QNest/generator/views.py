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
from django.contrib import messages
import re


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
    if request.method == "GET":
        return render(request, "create_template.html")

    if request.method == "POST":
        try:
            # Get basic template info
            template_name = request.POST.get("template_name", "").strip()
            exam_title = request.POST.get("exam_title", "").strip()
            course_code = request.POST.get("course_code", "").strip()
            course_name = request.POST.get("course_name", "").strip()
            time_duration = request.POST.get("time_duration", "").strip()
            max_marks = request.POST.get("max_marks", "0").strip()

            # Validate required fields
            if not all([template_name, exam_title, course_code, course_name, time_duration]):
                messages.error(request, "All fields are required")
                return redirect("create_template")

            try:
                max_marks = int(max_marks)
                if max_marks <= 0:
                    messages.error(request, "Max marks must be positive")
                    return redirect("create_template")
            except ValueError:
                messages.error(request, "Invalid max marks value")
                return redirect("create_template")

            # Process sections
            section_names = request.POST.getlist("section_name[]")
            num_questions = request.POST.getlist("num_questions[]")
            marks_per_question = request.POST.getlist("marks_per_question[]")
            instructions = request.POST.getlist("instructions[]")

            if not section_names:
                messages.error(request, "At least one section is required")
                return redirect("create_template")

            total_marks = 0
            sections = []
            has_errors = False

            for i in range(len(section_names)):
                try:
                    # Get section data
                    section_name = section_names[i].strip()
                    questions = int(num_questions[i])
                    marks = int(marks_per_question[i])
                    instruction = instructions[i].strip().lower()

                    # Validate basic fields
                    if not section_name or questions <= 0 or marks <= 0:
                        has_errors = True
                        break

                    # Validate instruction and calculate counted questions
                    if instruction.startswith("answer only"):
                        try:
                            answer_only = int(instruction.split(" ")[2])
                            if answer_only > questions:
                                has_errors = True
                                break
                            counted_questions = answer_only
                        except (IndexError, ValueError):
                            has_errors = True
                            break
                    elif instruction.startswith("answer all"):
                        counted_questions = questions
                    else:
                        has_errors = True
                        break

                    # Calculate section marks
                    section_marks = counted_questions * marks
                    total_marks += section_marks

                    sections.append({
                        "section_name": section_name,
                        "total_questions": questions,
                        "marks_per_question": marks,
                        "instructions": instruction,
                        "counted_questions": counted_questions,
                        "section_marks": section_marks
                    })

                except Exception:
                    has_errors = True
                    break

            if has_errors:
                messages.error(request, "Invalid section data or instructions")
                return redirect("create_template")

            if total_marks != max_marks:
                messages.error(request, 
                    f"Calculated marks ({total_marks}) don't match max marks ({max_marks})")
                return redirect("create_template")

            # Save template
            Template.objects.create(
                user=request.user,
                template_name=template_name,
                exam_title=exam_title,
                course_code=course_code,
                course_name=course_name,
                time_duration=time_duration,
                max_marks=max_marks,
                sections=sections
            )

            messages.success(request, "Template created successfully!")
            return redirect("upload_files")

        except Exception as e:
            messages.error(request, f"Error creating template: {str(e)}")
            return redirect("create_template")

    return redirect("create_template")




@login_required
@csrf_protect
def upload_files(request):
    if request.method == "POST":
        print("Received POST request:", request.POST)  

        if "generate_question_paper" in request.POST:
            print("Generating question paper...")

            template_id = request.POST.get("template_id")
            try:
                template = Template.objects.get(id=template_id, user=request.user)
            except Template.DoesNotExist:
                return JsonResponse({"error": "Invalid template selected."}, status=400)

            study_materials = request.FILES.getlist("study_material")
            if not study_materials:
                return JsonResponse({"error": "Study material is required."}, status=400)

            study_texts = [extract_text_from_pdf(pdf) for pdf in study_materials]
            study_text = "\n\n".join(study_texts)

            if not study_text.strip():
                return JsonResponse({"error": "Study material text extraction failed."}, status=400)

            prev_texts = [extract_text_from_pdf(pdf) for pdf in request.FILES.getlist("previous_question", [])]
            prev_text = "\n\n".join(prev_texts) if prev_texts else ""

            prev_qstn_text = f"### **Previous Exam Paper (Use as Reference, Do NOT Repeat Questions):**\n{prev_text[:4000]}" if prev_text else ""

            sections_formatted = "\n".join([
                f"### Section: {section['section_name']}\n"
                f"Number of Questions: {section['questions']}\n"
                f"Marks per Question: {section['marks_per_question']}\n"
                f"Instructions: {section['instructions']}\n"
                for section in template.sections
            ])

            # ✅ Fix: Construct the expected output section format outside the f-string
            formatted_sections_output = ''.join(
                f"### {section['section_name'].upper()}\n"
                f"{section['instructions']}\n\n" +
                '\n'.join(f"Q{i+1}. [Generated question here]" for i in range(section['questions'])) +
                "\n\n"
                for section in template.sections
            )

            # ✅ Prompt construction
            prompt = f"""
You are an expert university professor creating exam papers. Generate a question paper that EXACTLY matches the provided template structure.

### 🔹 STRICT REQUIREMENTS:
1. PRESERVE THE TEMPLATE STRUCTURE:
   - Maintain the exact number of sections in the given order
   - Each section must have precisely the specified number of questions
   - Never modify marks distribution or total marks

2. QUESTION GENERATION RULES:
   - Create ORIGINAL questions based on the study material
   - NEVER copy questions from previous papers (if provided)
   - Ensure appropriate difficulty for university-level exams
   - Questions should cover different aspects of the study material

3. FORMATTING:
   - Use the EXACT header format shown below
   - Maintain consistent numbering (Q1, Q2, etc.)
   - Include all specified section instructions
   - Preserve all template placeholders (Name, Reg No, etc.)

### 📝 TEMPLATE DETAILS (MUST INCLUDE VERBATIM):
Exam Title: {template.exam_title}
Course Code: {template.course_code}
Course Name: {template.course_name}
Time Duration: {template.time_duration}
Max Marks: {template.max_marks}

### 📑 SECTION STRUCTURE (FOLLOW EXACTLY):
{sections_formatted}

### 📚 STUDY MATERIAL CONTENT (Base questions on this):
{study_text[:10000]}  [First 10,000 characters]

### 🚫 PREVIOUS QUESTIONS TO AVOID (If provided):
{prev_text[:2000] if prev_text else "N/A"}

### ✏️ REQUIRED OUTPUT FORMAT:

[START OF FORMAT]
Name: ________________
Reg No: ________________

{template.exam_title.upper()}
Course Code: {template.course_code}
Course Name: {template.course_name}
Time Duration: {template.time_duration}
Max Marks: {template.max_marks}

---

{formatted_sections_output}
[END OF FORMAT]

### ✅ FINAL CHECK:
Before responding, verify:
1. All sections are present in correct order
2. Exact question counts per section
3. No duplication from previous papers
4. Proper formatting maintained
5. All template fields included verbatim
"""

            print(prompt)  # Debug prompt

            try:
                response = ollama.chat(model="qnest-tuned", messages=[{"role": "user", "content": prompt}])

                if "message" not in response or "content" not in response["message"]:
                    messages.error(request, "Invalid response from the model.")
                    return redirect('upload')

                questions = response["message"]["content"].strip()
                if not questions:
                    messages.error(request, "Question generation failed. No response from the model.")
                    return redirect('upload')

                messages.success(request, "Question paper generated successfully!")
                return render(request, "upload.html", {
                    "templates": Template.objects.filter(user=request.user).order_by("id"),
                    "generated_questions": questions,
                    "template_id": template_id
                })

            except Exception as e:
                print("Error calling Ollama:", str(e))
                messages.error(request, f"Ollama request failed: {str(e)}")
                return redirect('upload')

    # For GET requests or fallback
    templates = Template.objects.filter(user=request.user).order_by("id") 
    print("Templates in DB:", list(templates))  
    return render(request, "upload.html", {"templates": templates})



@login_required
def template_view(request):
    templates = Template.objects.filter(user=request.user).order_by("-created_at")
    return  render(request, 'template.html', {'templates':templates})

@login_required
def question_view(request):
    return render(request, 'question.html')

@login_required
def mcq(request):
    if request.method == 'POST' and 'generate_mcq' in request.POST:
        study_material = request.FILES.getlist('study_material')
        num_questions = int(request.POST.get('q_no', 10))
        
        if not study_material:
            return render(request, 'mcq.html', {'error': 'Please upload study material.'})

        try:
            # Extract text from PDFs
            study_texts = [extract_text_from_pdf(pdf) for pdf in study_material]
            study_text = "\n\n".join(study_texts)

            if not study_text.strip():
                return render(request, 'mcq.html', {'error': 'Failed to extract text from PDFs.'})

            prompt = f"""
                        Generate exactly {num_questions} multiple choice questions based on the following study material.

                        Each question must have:
                        - A question number
                        - 4 options labeled A to D
                        - NO ANSWERS embedded with the questions

                        After listing all questions, add a separate section titled `===ANSWER KEY===` with the correct options.

                        Use the following format:

                        1. [Question Text]
                        A) Option A
                        B) Option B
                        C) Option C
                        D) Option D

                        ...

                        ===ANSWER KEY===
                        1. [correct option]
                        2. [correct option]
                        ...

                        Study Material:
                        {study_text[:4000]}
                        """

            response = ollama.chat(
                model="qnest-tuned",
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )

            if 'message' in response and 'content' in response['message']:
                content = response['message']['content'].strip()
                
                # Split into questions and answers
                parts = content.split("===ANSWER KEY===")
                questions_part = parts[0].strip()
                answers_part = parts[1].strip() if len(parts) > 1 else ""
                
                # Process questions
                questions = []
                current_question = None
                
                import re
                question_pattern = re.compile(r'^\s*(\d+)\.\s*(.*)')
                option_pattern = re.compile(r'^\s*([A-D])\)\s*(.*)')
                
                for line in questions_part.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if this line is a new question
                    question_match = question_pattern.match(line)
                    if question_match:
                        # Save the previous question if it exists
                        if current_question:
                            questions.append(current_question)
                        
                        # Extract question number and text
                        number, text = question_match.groups()
                        current_question = {
                            'number': number.strip(),
                            'text': text.strip(),
                            'options': []
                        }
                    else:
                        # Check if this line is an option
                        option_match = option_pattern.match(line)
                        if option_match and current_question:
                            letter, text = option_match.groups()
                            current_question['options'].append({
                                'letter': letter.strip(),
                                'text': text.strip()
                            })

                # Don't forget to add the last question
                if current_question:
                    questions.append(current_question)

                # Process answers
                answers = []
                answer_pattern = re.compile(r'^\s*(\d+)\.\s*([A-D])')
                
                for line in answers_part.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    match = answer_pattern.match(line)
                    if match:
                        number, answer = match.groups()
                        answers.append({
                            'number': number.strip(),
                            'answer': answer.strip()
                        })

                return render(request, 'mcq.html', {
                    'questions': questions,
                    'answers': answers,
                    'success': True
                })

        except Exception as e:
            import traceback
            print(f"Error during MCQ generation: {str(e)}")
            print(traceback.format_exc())
            return render(request, 'mcq.html', {'error': f"An error occurred: {str(e)}"})

    return render(request, 'mcq.html')
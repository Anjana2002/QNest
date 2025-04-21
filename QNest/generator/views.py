from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from .models import Template, GeneratedPDF
from PyPDF2 import PdfReader
import ollama
from django.contrib import messages
import re
from django.conf import settings
import base64
from html import unescape
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
import subprocess, tempfile, os
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.core.files.base import ContentFile
from datetime import datetime
from django.utils.html import escape
import re
# from django.utils.html import unescape_html

# from django.utils.http import urlquote
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
import html


def escape_latex(text):
    """Comprehensive LaTeX escaping that handles all special cases"""
    if not text:
        return ""
    
    # First unescape HTML entities
    from html import unescape
    text = unescape(text)
    
    # Replace special characters in order of importance
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
        ('<', r'\textless{}'),
        ('>', r'\textgreater{}'),
        ('"', r'"{}'),
        ("'", r"'"),
        ('\r\n', '\n\n'),  # Windows
        ('\r', '\n\n'),    # Old Mac
        ('\n', '\n\n'),    # Unix
    ]
    
    for char, replacement in replacements:
        text = text.replace(char, replacement)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text


@login_required
@csrf_protect
def upload_files(request):
    templates = Template.objects.filter(user=request.user).order_by("id")
    
    if request.method == "POST":
        if "generate_question_paper" in request.POST:
            template_id = request.POST.get("template_id")
            try:
                template = Template.objects.get(id=template_id, user=request.user)
            except Template.DoesNotExist:
                messages.error(request, "Invalid template selected.")
                return render(request, "upload.html", {"templates": templates})

            study_materials = request.FILES.getlist("study_material")
            if not study_materials:
                messages.error(request, "Study material is required.")
                return render(request, "upload.html", {"templates": templates})

            # Extract text from study materials
            study_texts = []
            for pdf in study_materials:
                try:
                    text = extract_text_from_pdf(pdf)
                    if text.strip():
                        study_texts.append(text)
                except Exception as e:
                    print(f"Error extracting text from PDF: {e}")
                    messages.error(request, f"Error processing one of the study materials: {e}")
                    return render(request, "upload.html", {"templates": templates})
            
            if not study_texts:
                messages.error(request, "Study material text extraction failed - no valid text found.")
                return render(request, "upload.html", {"templates": templates})
            
            study_text = "\n\n".join(study_texts)

            # Process previous questions if provided
            prev_texts = []
            for pdf in request.FILES.getlist("previous_question", []):
                try:
                    text = extract_text_from_pdf(pdf)
                    if text.strip():
                        prev_texts.append(text)
                except Exception as e:
                    print(f"Error extracting text from previous questions PDF: {e}")
            prev_text = "\n\n".join(prev_texts) if prev_texts else ""

            sections_prompt = "\n".join(
                                f"""**{section['section_name'].upper()}**
                            {"**Answer all questions.**" if section.get('answer_all', True) 
                            else f"**Answer any {section.get('questions_to_answer', 3)} questions.**"} Each carries {section['marks_per_question']} mark(s). [TOTAL QUESTIONS: {section['total_questions']}]"""
                                for section in template.sections
                            )


            prompt = f"""
            You are an expert academic question paper generator. Generate a properly formatted exam paper following these rules:

            1. SECTION STRUCTURE:
            - For each section, follow this exact format:
                [SECTION NAME in uppercase]
                [Instruction line]
                [Questions listed line-by-line]

            2. QUESTION FORMATTING:
            - One question per line
            - Numbered sequentially (1., 2., 3., etc.)

            3. INSTRUCTIONS:
            - Must exactly match the template format:
                * "Answer all questions. Each carries X mark(s)." OR
                * "Answer any Y questions. Each carries X mark(s)."

            4. CONTENT REQUIREMENTS:
            - Questions must be derived from the study material
            - No chapter titles or source hints
            - Vary depth based on marks:
                * 1-2 marks: Concise, factual
                * 5-10 marks: Detailed, analytical
                ---

            STUDY MATERIAL (SOURCE CONTENT):
            {study_text[:10000]}

            PREVIOUS QUESTIONS (AVOID REPETITION):
            {prev_text[:2000] if prev_text else "NONE PROVIDED"}

            ---

        SECTION FORMATTING TEMPLATE:
            {sections_prompt}   

    ---

    GENERATE THE EXAM PAPER FOLLOWING THE ABOVE FORMAT EXACTLY:
    """
            try:
                response = ollama.chat(
                    model="mistral",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You must format exam papers EXACTLY as specified. Never omit required lines."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    options={
                        'temperature': 0.2,
                        'repeat_penalty': 1.2
                    }
                )

                questions = response["message"]["content"].strip()
                
                # Store the generated content
                request.session["last_generated_questions"] = questions
                request.session["last_template_id"] = template_id
                
                # Generate and save PDF
                pdf_bytes = generate_pdf_response(request, template, questions)
                if pdf_bytes:
                    request.session["pdf_preview"] = base64.b64encode(pdf_bytes).decode('utf-8')
                    request.session["pdf_filename"] = f"{template.exam_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                    messages.success(request, "Question paper generated successfully!")
                    return render(request, "upload.html", {
                        "templates": templates,
                        "pdf_preview": request.session["pdf_preview"],
                        "pdf_filename": request.session["pdf_filename"],
                        "generated_questions": questions
                    })
                else:
                    messages.error(request, "PDF generation failed. Please check the question format.")
                    return render(request, "upload.html", {
                        "templates": templates,
                        "generated_questions": questions
                    })

            except Exception as e:
                messages.error(request, f"Error generating question paper: {e}")
                return render(request, "upload.html", {"templates": templates})

    return render(request, "upload.html", {"templates": templates})


def generate_pdf_response(request, template, questions):
    """Robust PDF generation with proper template handling"""
    try:
        escaped_questions = escape_latex(questions)
        escaped_questions = re.sub(r'\\n', '\n', escaped_questions)  # Fix any remaining newline issues
        escaped_questions = re.sub(r'(?<!\\)\\', r'\\textbackslash{}',escaped_questions)
        latex_context = {
            "exam_title": escape_latex(template.exam_title),
            "course_code": escape_latex(template.course_code),
            "course_name": escape_latex(template.course_name),
            "time_duration": escape_latex(template.time_duration),
            "max_marks": escape_latex(str(template.max_marks)),
            "questions": escape_latex(questions),
        }

        # Render template with proper variable syntax
        latex_string = render_to_string("question_template.tex", latex_context)
        
        latex_string = render_to_string("question_template.tex", latex_context)

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "paper.tex")
            with open(tex_path, "w", encoding='utf-8') as f:
                f.write(latex_string)

            try:
                # Run pdflatex twice to resolve references
                latex_cmd = ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path]
                result = subprocess.run(latex_cmd, cwd=tmpdir, check=True, timeout=30, 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                result = subprocess.run(latex_cmd, cwd=tmpdir, check=True, timeout=30,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                pdf_path = os.path.join(tmpdir, "paper.pdf")
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()

                    # Save to database
                    pdf_instance = GeneratedPDF.objects.create(
                        user=request.user,
                        template=template,
                    )
                    pdf_instance.pdf_file.save(
                        f"{template.exam_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf",
                        ContentFile(pdf_bytes)
                    )
                    return pdf_bytes
                
            except subprocess.CalledProcessError as e:
                print(f"LaTeX compilation failed. Output:\n{e.stdout.decode()}\nError:\n{e.stderr.decode()}")
                return None
            except subprocess.TimeoutExpired:
                print("LaTeX compilation timed out")
                return None

    except Exception as e:
        print(f"Error in PDF generation: {str(e)}")
        return None

@login_required
def download_generated_pdf(request):
    """Download the most recently generated PDF"""
    if 'pdf_preview' not in request.session:
        messages.error(request, "No question paper found. Please generate one first.")
        return redirect("upload_files")
    
    try:
        pdf_bytes = base64.b64decode(request.session['pdf_preview'])
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{request.session.get("pdf_filename", "question_paper.pdf")}"'
        return response
    except Exception as e:
        messages.error(request, f"Error downloading PDF: {str(e)}")
        return redirect("upload_files")


@login_required
def template_view(request):
    templates = Template.objects.filter(user=request.user).order_by("-created_at")
    return  render(request, 'template.html', {'templates':templates})

@login_required
def view_generated_pdfs(request):
    generated_pdfs = GeneratedPDF.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "question.html", {"generated_pdfs": generated_pdfs})


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
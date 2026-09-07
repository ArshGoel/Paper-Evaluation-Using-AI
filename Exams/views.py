import base64
import time
from urllib import response
from django.conf import settings
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.http import FileResponse, Http404
from django.contrib import messages
import os
# pip install pdf2image pillow
import requests
import requests
from Exams.models import Exam, Submission, Question, SubQuestion,  QuestionImage, SubQuestionImage, Evaluation
import google.generativeai as genai
import fitz  # PyMuPDF
import json
import re
import time
import random
from Accounts.models import User
from PIL import Image
import io
import json
from .models import QuestionEvaluation, StudentSheetExtractVersion
from collections import defaultdict
from Exams.models import ExtractedQuestionAnswer


GEMINI_API_KEYS = settings.GEMINI_API_KEYS.copy()
GEMINI_MODELS = settings.GEMINI_MODELS.copy()
GEMINI_MODEL_CACHE = {}


def gemini_generate(contents, include_model=False):
    """Try configured keys/models once each and return response text."""
    last_error = None

    for api_key in GEMINI_API_KEYS:
        try:
            genai.configure(api_key=api_key)
            for model_name in GEMINI_MODELS:
                try:
                    cache_key = (api_key, model_name)
                    model = GEMINI_MODEL_CACHE.get(cache_key)
                    if model is None:
                        model = genai.GenerativeModel(model_name)
                        GEMINI_MODEL_CACHE[cache_key] = model

                    response = model.generate_content(contents)
                    response_text = getattr(response, 'text', '').strip()
                    if response_text:
                        if include_model:
                            return response_text, model_name
                        return response_text
                    last_error = ValueError(f'{model_name} returned an empty response')
                except Exception as error:
                    last_error = error
                    error_text = str(error).lower()
                    if 'quota' in error_text or 'limit' in error_text:
                        break
        except Exception as error:
            last_error = error

    if last_error:
        raise RuntimeError('All Gemini API attempts failed') from last_error
    raise RuntimeError('No Gemini API keys are configured')


def gemini_upload_pdf(pdf_data):
    """Upload a PDF once, falling back to another key only if needed."""
    if not GEMINI_API_KEYS:
        raise RuntimeError('No Gemini API keys are configured')

    last_error = None
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
        temp_pdf.write(pdf_data)
        temp_pdf_path = temp_pdf.name

    try:
        for api_key in GEMINI_API_KEYS:
            try:
                genai.configure(api_key=api_key)
                uploaded_file = genai.upload_file(temp_pdf_path)
                while uploaded_file.state.name == 'PROCESSING':
                    time.sleep(1)
                    uploaded_file = genai.get_file(uploaded_file.name)
                return uploaded_file
            except Exception as error:
                last_error = error
    finally:
        os.unlink(temp_pdf_path)

    raise RuntimeError('Unable to upload PDF to Gemini') from last_error

def get_pdf_bytes(file_data, legacy_file=None):
    if file_data:
        return bytes(file_data)

    if legacy_file:
        try:
            with legacy_file.open('rb') as pdf_file:
                return pdf_file.read()
        except Exception as error:
            raise Http404(
                'This uploaded file is unavailable. Please upload the PDF again.'
            ) from error

    raise Http404('No file found')

def view_pdf(request, exam_id, file_type, student_id=None):
    exam = get_object_or_404(Exam, id=exam_id)

    if file_type == 'question_paper':
        pdf_data = exam.question_paper_data
        filename = exam.question_paper_name or 'question_paper.pdf'
        legacy_file = exam.question_paper

    elif file_type == 'answer_key':
        pdf_data = exam.answer_key_data
        filename = exam.answer_key_name or 'answer_key.pdf'
        legacy_file = exam.answer_key

    elif file_type == 'submission':
        submission = get_object_or_404(
            Submission,
            exam=exam,
            student_id=student_id
        )
        pdf_data = submission.file_data
        filename = submission.file_name or 'submission.pdf'
        legacy_file = submission.file

    else:
        raise Http404('Invalid file type')

    response = FileResponse(
        io.BytesIO(get_pdf_bytes(pdf_data, legacy_file)),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

def teacher_exams(request):
    teacher = request.user.teacher_profile

    exams = Exam.objects.filter(
        course__in=teacher.courses.all(),
        class_assigned__in=teacher.classes.all()
    ).distinct()

    for exam in exams:
        if exam.question_paper:
            exam.full_url = request.build_absolute_uri(
                reverse('view_pdf', args=[exam.id, 'question_paper'])
            )
        elif exam.question_paper_data:
            exam.full_url = request.build_absolute_uri(
                reverse('view_pdf', args=[exam.id, 'question_paper'])
            )

    return render(request, 'teacher_exams.html', {
        'exams': exams
    })

def clean_json_output(raw_text):
    # remove ```json and ```
    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    return json.loads(cleaned)

def clean_question_number(q):
    digits = re.sub(r'\D', '', str(q or ''))
    if not digits:
        raise ValueError('Question number is missing')
    return int(digits)  # removes '.', 'Q', etc


def first_value(data, *keys, default=None):
    for key in keys:
        value = data.get(key)
        if value not in (None, ''):
            return value
    return default

def save_exam_from_json(exam, raw_output):
    data = clean_json_output(raw_output)

    # ✅ Save instructions
    exam.instructions = data.get("instructions", "")
    exam.save()

    questions = data.get('questions') or data.get('question') or []
    if isinstance(questions, dict):
        questions = [questions]

    for sequence, q in enumerate(questions, start=1):
        question_text = first_value(q, 'question_text', 'text', 'question', default='').strip()
        if not question_text:
            continue

        raw_number = first_value(q, 'question_number', 'question_no', 'number', 'no')
        try:
            question_number = clean_question_number(raw_number)
        except ValueError:
            question_number = sequence

        question, created = Question.objects.update_or_create(
            exam=exam,
            question_number=question_number,
            defaults={
                'part': first_value(q, 'part', 'section', default='') or '',
                'text': question_text,
                'marks': first_value(q, 'marks', 'mark', default=0) or 0,
            }
        )

        # 🔥 handle sub-questions
        sub_questions = q.get('sub_questions') or q.get('subquestions') or []
        for sub in sub_questions:
            SubQuestion.objects.update_or_create(
                question=question,
                label=first_value(sub, 'label', 'name', default=''),
                defaults={
                    'text': first_value(sub, 'text', 'question_text', default=''),
                    'marks': first_value(sub, 'marks', 'mark')
                }
            )
import tempfile
def pdf_to_images(pdf_data):
    document = fitz.open(stream=pdf_data, filetype='pdf')
    images = []

    for page in document:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        images.append(Image.open(io.BytesIO(pixmap.tobytes('png'))).convert('RGB'))

    document.close()
    return images

import base64
from io import BytesIO

def image_to_base64(img):
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def gemini_call_question_paper(pdf_data):
    prompt = '''
        Extract the content of this question paper into STRICT JSON format.
        Rules:
        1. Return ONLY valid JSON. Do not include explanations, notes, markdown, or extra text.
        2. Extract:
        * only extract the text not text in table or image.
        * Instructions (general instructions at the beginning)
        * u must ensure instruction must contain the part wise marks and how many questions to attempt.
        * After analyzing the paper in instruction add a short instruction.
        * Questions
        3. Each question must include:
        * part (e.g., A, B, C)
        * question_number (exactly as shown)
        * question_text (full question text)
        * marks (number; if not explicitly mentioned, use null)
        4. If sub-questions exist (like a, b, i, ii), include them inside "sub_questions" array.
        5. Each sub-question must include:
        * label (e.g., a, b, i, ii)
        * text (full text)
        * marks (number or null)
        6. Preserve original wording. Do NOT summarize or modify.
        7. Ignore page numbers, headers, footers, logos, or irrelevant text.
        8. If marks are written like (5), [5], "5 marks", extract only the numeric value.
        Output format:
        {
            "instructions": "string",
            "questions": [
                {
                    "part": "A",
                    "question_number": "1",
                    "question_text": "....",
                    "marks": 5,
                    "sub_questions": [
                        {
                            "label": "a",
                            "text": "....",
                            "marks": 2
                        }
                    ]
                }
            ]
        }
    '''

    images = pdf_to_images(pdf_data)

    parts = [{"text": prompt}]

    # 🔥 add each page as image
    for img in images:
        encoded = image_to_base64(img)

        parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": encoded
            }
        })

    return gemini_generate([{"parts": parts}])

def edit_exam_teacher(request, id):
    exam = get_object_or_404(Exam, id=id)

    if request.method == "POST":
        exam.title = request.POST.get('title')
        exam.total_marks = request.POST.get('total_marks')
        exam.date = request.POST.get('date')
        exam.instructions = request.POST.get('instructions')
        if request.POST.get("delete_qp"):
            exam.question_paper_data = None
            exam.question_paper_name = ''
            exam.question_paper = None

        # 🔥 DELETE ANSWER KEY
        if request.POST.get("delete_ak"):
            exam.answer_key_data = None
            exam.answer_key_name = ''
            exam.answer_key = None

        new_qp = request.FILES.get('question_paper')
        new_ak = request.FILES.get('answer_key')

        # 🔥 track if new file uploaded
        parse_needed = False

        if new_qp:
            exam.question_paper_data = new_qp.read()
            exam.question_paper_name = new_qp.name
            parse_needed = True   # ✅ trigger parsing

        if new_ak:
            exam.answer_key_data = new_ak.read()
            exam.answer_key_name = new_ak.name

        exam.save()

        # 🔥 AUTO PARSE AFTER SAVE
        if parse_needed:
            try:
                output = gemini_call_question_paper(exam.question_paper_data)

                exam.questions.all().delete()

                save_exam_from_json(exam, output)

                messages.success(request, "Parsed & saved successfully!")

            except Exception as e:
                print(f"Error: {e}")
                messages.error(request, f"Parsing failed: {str(e)}")

        return redirect('teacher_exams')

    return render(request, 'edit_exam.html', {
        'exam': exam
    })

def view_parsed_exam(request, id):
    exam = get_object_or_404(Exam, id=id)

    # group questions by part
    questions = exam.questions.all().order_by('part', 'question_number')

    grouped_questions = {}
    for q in questions:
        part = q.part or "General"

        if part not in grouped_questions:
            grouped_questions[part] = []

        grouped_questions[part].append(q)

    return render(request, 'view_parsed_exam.html', {
        'exam': exam,
        'grouped_questions': grouped_questions
    })

def upload_question_image(request, q_id):
    question = get_object_or_404(Question, id=q_id)

    if request.method == "POST":
        files = request.FILES.getlist('images')

        for f in files:
            QuestionImage.objects.create(
                question=question,
                image=f
            )

    return redirect('view_parsed_exam', id=question.exam.id)

def upload_subquestion_image(request, sub_id):
    sub = get_object_or_404(SubQuestion, id=sub_id)

    if request.method == "POST":
        files = request.FILES.getlist('images')

        for f in files:
            SubQuestionImage.objects.create(
                sub_question=sub,
                image=f
            )

    return redirect('view_parsed_exam', id=sub.question.exam.id)

def admin_upload_submission_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    students = User.objects.filter(role='student')

    submissions = Submission.objects.filter(exam=exam)
    submission_map = {s.student_id: s for s in submissions}

    if request.method == 'POST':
        student_id = request.POST.get('student_id')

        # 🔥 DELETE
        if 'delete' in request.POST:
            submission = Submission.objects.filter(
                student_id=student_id,
                exam=exam
            ).first()

            if submission:
                submission.delete()

        # 🔥 UPLOAD / REPLACE
        file = request.FILES.get('file')
        if file and student_id:
            student = User.objects.get(id=student_id)

            Submission.objects.update_or_create(
                student=student,
                exam=exam,
                defaults={
                    'file': None,
                    'file_data': file.read(),
                    'file_name': file.name,
                }
            )

        return redirect('admin_upload_submission_exam', exam_id=exam.id)

    return render(request, 'exam_admin/upload_submission_exam.html', {
        'exam': exam,
        'students': students,
        'submission_map': submission_map
    }) 

def teacher_view_submissions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    students = User.objects.filter(role='student')

    submissions = Submission.objects.filter(exam=exam)
    submission_map = {s.student_id: s for s in submissions}

    # 🔥 attach submission + evaluation
    for student in students:
        submission = submission_map.get(student.id)
        student.submission = submission
        student.evaluation = getattr(submission, 'evaluation', None) if submission else None

    return render(request, 'view_submissions.html', {
        'exam': exam,
        'students': students
    })

def parse_gemini_output(text):
    pages = []

    # Split pages
    page_blocks = re.split(r'Page\s+\d+', text)

    page_numbers = re.findall(r'Page\s+(\d+)', text)

    for i, block in enumerate(page_blocks[1:]):  # skip first empty split
        page_data = {}

        page_data["page"] = int(page_numbers[i]) if i < len(page_numbers) else i + 1

        # Extract metadata
        meta_match = re.search(r'---(.*?)---', block, re.DOTALL)
        if meta_match:
            meta_text = meta_match.group(1)

            def get_val(key, cast=str):
                match = re.search(rf'{key}:\s*(.+)', meta_text)
                if match:
                    val = match.group(1).strip()
                    if cast == bool:
                        return val.lower() == "true"
                    if cast == int:
                        try:
                            return int(re.search(r'-?\d+', val).group())
                        except (AttributeError, ValueError):
                            return None
                    return val
                return None

            page_data["primary_language"] = get_val("primary_language")
            page_data["is_rotation_valid"] = get_val("is_rotation_valid", bool)
            page_data["rotation_correction"] = get_val("rotation_correction", int)
            page_data["confidence_score"] = get_val("confidence_score", int)
            page_data["contains_math"] = get_val("contains_math", bool)
            page_data["contains_diagram"] = get_val("contains_diagram", bool)
            page_data["contains_code"] = get_val("contains_code", bool)

        # Extract content (after metadata block)
        content = re.split(r'---', block)
        if len(content) >= 3:
            page_data["content"] = content[2].strip()
        else:
            page_data["content"] = block.strip()

        pages.append(page_data)

    return {"pages": pages}

def save_extracted_answers(extract_version, gemini_json):
    """
    Properly splits multiple questions per page
    """

    question_data = defaultdict(str)
    current_q = None

    for page in gemini_json.get("pages", []):
        content = page.get("content", "")

        # 🔥 SPLIT by Question pattern
        parts = re.split(r"(Question\s*\d+)", content, flags=re.IGNORECASE)

        # Example result:
        # ["", "Question 1", " text...", "Question 2", " text..."]

        for i in range(1, len(parts), 2):
            q_label = parts[i]
            q_text = parts[i + 1] if i + 1 < len(parts) else ""

            # extract number
            match = re.search(r"\d+", q_label)
            if not match:
                continue

            q_no = match.group()

            current_q = q_no
            question_data[q_no] += "\n" + q_text.strip()

        # 🔥 handle continuation (no new question)
        if len(parts) == 1 and current_q:
            question_data[current_q] += "\n" + content

    # ✅ SAVE TO DB
    ExtractedQuestionAnswer.objects.filter(
        extract_version=extract_version
    ).delete()

    for q_no in sorted(question_data.keys(), key=int):
        answer_text = question_data[q_no].strip()
        lower = answer_text.lower()

        answer_data = {
            'extract_version': extract_version,
            'question_number': q_no,
            'answer_text': answer_text,
        }
        model_fields = {field.name for field in ExtractedQuestionAnswer._meta.fields}
        optional_flags = {
            'contains_diagram': "diagram" in lower or "graph" in lower,
            'contains_math': "=" in answer_text,
            'contains_code': "def " in answer_text or "class " in answer_text,
        }
        answer_data.update({
            name: value for name, value in optional_flags.items()
            if name in model_fields
        })
        ExtractedQuestionAnswer.objects.create(**answer_data)


def get_next_extract_version(submission):
    latest = StudentSheetExtractVersion.objects.filter(
        submission=submission
    ).order_by('-version_number').values_list('version_number', flat=True).first()
    return (latest or 0) + 1


def mark_best_extract_version(submission):
    best_version = StudentSheetExtractVersion.objects.filter(
        submission=submission
    ).order_by('-confidence_score', '-version_number').first()
    if best_version:
        StudentSheetExtractVersion.objects.filter(
            submission=submission
        ).exclude(pk=best_version.pk).update(is_best=False)
        if not best_version.is_best:
            best_version.is_best = True
            best_version.save(update_fields=['is_best'])

def extract_student_sheets(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    file_data = get_pdf_bytes(submission.file_data, submission.file)

    prompt = """

        You are an expert document parser.
        The answer sheet has a leftmost column labeled "Q.No". Always read the question number from that column only.
        Attached are MULTIPLE images representing consecutive pages of a handwritten student answer sheet.

        These pages belong to ONE continuous answer sheet and must be processed in the SAME order.

        Your task is to extract ALL question–answer content exactly as written.
        --------------------------------------------------

        QUESTION NUMBER DETECTION RULE (VERY IMPORTANT)

        The answer sheet contains a dedicated column labeled **Q.No**.

        Question numbers MUST be extracted ONLY from the **Q.No column**.

        STRICT RULES:

        1. Only treat a number as a question number if it appears inside the **Q.No column**.

        2. Numbers appearing inside the answer text such as:
        - Step numbers (Step 1, Step 2)
        - Table row numbers
        - Mathematical values
        - Diagram labels
        - Bullet numbering
        MUST NOT be treated as question numbers.

        3. If a page contains content but the **Q.No column is empty**, then the content is a continuation of the previous question.

        Format it as:

        Question N (continued): <answer>

        4. NEVER infer question numbers from:
        - Step headings
        - Table content
        - Mathematical expressions
        - Text like "Step 2", "Part B", "Example 3"

        5. If the **Q.No column value is unreadable**, write:

        Question ?: [Unclear/Illegible]

        6. If a table appears inside the answer, it belongs to the current question and does NOT indicate a new question.

        --------------------------------------------------

        STRICT PARSING RULES

        1. Only extract what is visible in the images.

        2. NEVER invent question numbers.

        3. If a question number is not clearly written,
        DO NOT create one.

        4. If text appears without a question number,
        treat it as a continuation of the LAST detected question.

        5. If the answer continues on the next page,
        continue the SAME question number.

        6. If a question number is unreadable or unclear, write:

        Question ?: [Unclear/Illegible]

        7. Maintain the EXACT order of answers across pages.

        --------------------------------------------------

        PAGE INTERPRETATION RULES

        Notebook ruling lines are background lines.

        They MUST NOT be interpreted as tables.

        Text alignment does NOT imply tabular structure unless a table
        is clearly drawn by the student.

        --------------------------------------------------

        CONTENT TYPES TO EXTRACT

        Extract ALL answer formats including:

        • Plain text explanations  
        • Bullet points or numbered lists  
        • Multiple choice answers (a), (b), (c), (d)  
        • True / False answers  
        • Fill in the blanks  
        • Numerical values (e.g., 360000, -1)  
        • Mathematical equations  
        • Algebraic expressions  
        • Derivations (multi-step math)  
        • Physics formulas  
        • Scientific symbols (√, π, ∑, ∫, Δ, ≥, ≤, ≠, →)  
        • Units (m/s, kg, Ω, A, V)  
        • Chemical formulas (H₂O, CO₂, NaCl)  
        • Programming code snippets  
        • Flowcharts  
        • Circuit diagrams  
        • Graphs  
        • Diagrams  
        • Tables drawn by the student  

        --------------------------------------------------

        MATHEMATICAL FORMATTING RULES

        Convert all mathematical expressions into LaTeX.

        Examples:

        V = IR → $V = IR$

        R = V/I → $R = \frac{V}{I}$

        Preserve subscripts and superscripts.

        Example:

        H₂O → H_2O  
        x² → x^2

        Derivations must be converted into steps.

        Example:

        Step 1: $V = IR$

        Step 2: $R = \frac{V}{I}$

        --------------------------------------------------

        DIAGRAM RULES

        If a diagram exists:

        DO NOT redraw the diagram.

        Instead describe it clearly using brackets.

        Example:

        [Diagram: Labeled block diagram showing transmitter → communication channel → receiver]

        --------------------------------------------------

        GRAPH RULES

        If a graph exists:

        Describe the axes and trend.

        Example:

        [Graph: Current (X-axis) vs Voltage (Y-axis) showing linear increase]

        --------------------------------------------------

        CONTINUATION RULE

        If a page begins without a question number:

        Assume it continues from the previous page.

        Format it as:

        Question N (continued): <text>

        --------------------------------------------------

        OUTPUT FORMAT (STRICT)

        Return ONLY clean markdown.

        Do NOT add explanations.

        --------------------------------------------------

        For EACH page use the following structure:

        Page <number>

        ---
        primary_language: <detected_language>
        is_rotation_valid: <true/false>
        rotation_correction: <degrees_if_any>
        confidence_score: <0-100>
        contains_math: <true/false>
        contains_diagram: <true/false>
        contains_code: <true/false>
        ---

        Question <number>: <answer>

        Example:

        Question 1: Pushdown automata is a computational model...

        Question 2:
        Step 1: $V = IR$

        Step 2: $R = \frac{V}{I}$

        Question 3: (a) True

        --------------------------------------------------

        If an answer continues:

        Question 3 (continued): <text>

        --------------------------------------------------

        Process ALL pages sequentially.

        Do NOT hallucinate missing questions.

        Only extract what is visible.
    """

    final_output = None

    processing_time_ms = 0
    start_time = None   # 👈 important

    try:
        uploaded_file = gemini_upload_pdf(file_data)
        start_time = time.time()
        final_output, model_name = gemini_generate(
            [prompt, uploaded_file],
            include_model=True,
        )
        processing_time_ms = int((time.time() - start_time) * 1000)
    except Exception as extraction_error:
        print(f'Answer extraction failed: {extraction_error}')

    if not final_output:
        messages.error(
            request,
            'Answer extraction failed: Gemini could not process this PDF. '
            'Please check the API keys and upload the answer sheet again.'
        )
        return redirect('view_submissions', exam_id=submission.exam.id)

    # Step 1: Convert to JSON (temporary)
    parsed_json = parse_gemini_output(final_output)

    # Step 2: version
    version = get_next_extract_version(submission)

    # Step 3: create object
    extract_data = {
        'submission': submission,
        'version_number': version,
        'raw_markdown': final_output,
        'structured_json': parsed_json,
        'confidence_score': parsed_json.get("pages", [{}])[0].get("confidence_score") or 0,
    }
    model_fields = {field.name for field in StudentSheetExtractVersion._meta.fields}
    optional_data = {
        'model_used': model_name,
        'processing_time_ms': processing_time_ms // 1000,
        'primary_language': parsed_json.get("pages", [{}])[0].get("primary_language"),
    }
    extract_data.update({
        name: value for name, value in optional_data.items()
        if name in model_fields
    })
    obj = StudentSheetExtractVersion.objects.create(**extract_data)
    mark_best_extract_version(submission)
    obj.refresh_from_db()
    # The parsed JSON is already stored in structured_json. Avoid uploading it
    # to Cloudinary's image endpoint as a redundant JSON file.
    obj.save()
    save_extracted_answers(obj, parsed_json)
    
    return redirect('view_submissions', exam_id=submission.exam.id)

def view_extracted_data(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    versions = submission.extract_versions.all()
    version_id = request.GET.get("version")

    if version_id:
        extract_version = get_object_or_404(StudentSheetExtractVersion, id=version_id)
    else:
        extract_version = versions.filter(is_best=True).first() or versions.first()

    context = {
        "submission": submission,
        "versions": versions,
        "extract_version": extract_version,
        "json_data": extract_version.structured_json,
        "questions": extract_version.questions.all()
    }

    return render(request, "view_extract.html", context)

def evaluate_question(question_text, student_answer, max_marks):
    if not student_answer or not student_answer.strip():
        return {
            "marks": 0,
            "feedback": "No answer was provided for this question."
        }

    prompt = f"""
    You are a fair and helpful exam evaluator.

    Evaluate the student's answer based on correctness, completeness, and clarity.
    Award reasonable partial credit for correct concepts, relevant examples, and
    valid steps even when the answer has grammar, spelling, or formatting errors.
    Do not penalize minor language mistakes unless they change the meaning.

    ----------------------------------------

    Question:
    {question_text}

    Student Answer:
    {student_answer}

    Max Marks: {max_marks}

    ----------------------------------------

    Evaluation Rules:

    1. Award marks step-by-step (partial marking allowed)
    2. If answer is correct → full marks
    3. If partially correct → give proportional partial marks
    4. If wrong or irrelevant → give 0 or very low marks
    5. If diagram is described → evaluate based on components/labels
    6. If math → check steps + final answer
    7. Do not require wording identical to the question or answer key.
    8. Give concise, constructive feedback explaining the awarded marks.

    ----------------------------------------

    Return STRICT JSON ONLY:

    {{
        "marks": number,
        "feedback": "short explanation"
    }}
    """

    try:
        raw = gemini_generate(prompt)
        raw = raw.replace("```json", "").replace("```", "").strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            raise ValueError('Gemini returned no JSON object')
        data = json.loads(json_match.group(0))

        marks = float(data.get("marks", 0))
        feedback = str(data.get("feedback", "")).strip()
        marks = min(max(marks, 0), float(max_marks))

        return {
            "marks": round(marks, 2),
            "feedback": feedback or "Evaluated based on the submitted answer."
        }
    except Exception as evaluation_error:
        print(f"Evaluation API failed: {evaluation_error}")

    # Keep failed calls distinguishable from a genuine zero score.
    return {
        "marks": 0,
        "feedback": "AI evaluation was unavailable. Please retry the evaluation."
    }


def evaluate_questions_batch(question_items):
    prompt = """
You are a fair exam evaluator. Evaluate each submitted answer against its question.
Give reasonable partial credit for correct concepts and valid steps. Do not penalize
minor grammar, spelling, or formatting mistakes unless they change the meaning.
If an answer is blank, award zero and say that no answer was provided.
Return JSON only in this format:
{"evaluations": [{"question_number": 1, "marks": 0, "feedback": "..."}]}

Questions and answers:
""" + json.dumps(question_items, ensure_ascii=False)

    raw = gemini_generate(prompt).replace('```json', '').replace('```', '').strip()
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        raise ValueError('Gemini returned no batch JSON object')
    data = json.loads(json_match.group(0))
    return {
        str(item['question_number']): item
        for item in data.get('evaluations', [])
        if 'question_number' in item
    }

def evaluate_submission_view(request, submission_id):

    submission = get_object_or_404(Submission, id=submission_id)

    # 🔥 get best extracted version
    extract_version = submission.extract_versions.filter(is_best=True).first()

    if not extract_version:
        messages.error(request, "No extracted data found")
        return redirect('view_submissions', exam_id=submission.exam.id)

    answers = ExtractedQuestionAnswer.objects.filter(
        extract_version=extract_version
    )

    answer_map = {}
    for answer in answers:
        question_key = str(answer.question_number)
        existing_answer = answer_map.get(question_key, '')
        if len(answer.answer_text or '') > len(existing_answer):
            answer_map[question_key] = answer.answer_text or ''

    questions = Question.objects.filter(
        exam=submission.exam
    ).order_by('question_number', 'id')

    # Older parses may have created duplicate rows before the uniqueness
    # constraint on exam and question number was enforced.
    unique_questions = []
    seen_question_numbers = set()
    for question in questions:
        if question.question_number in seen_question_numbers:
            continue
        seen_question_numbers.add(question.question_number)
        unique_questions.append(question)

    # 🔥 create / reset evaluation
    evaluation, _ = Evaluation.objects.get_or_create(
        submission=submission
    )

    # 🔥 clear old question evaluations
    evaluation.question_evaluations.all().delete()

    batch_items = [
        {
            'question_number': q.question_number,
            'question': q.text,
            'max_marks': q.marks,
            'student_answer': answer_map.get(str(q.question_number), ''),
        }
        for q in unique_questions
    ]
    try:
        batch_results = evaluate_questions_batch(batch_items)
    except Exception as batch_error:
        print(f'Batch evaluation failed: {batch_error}')
        batch_results = {}

    total_score = 0

    for q in unique_questions:

        q_no = str(q.question_number)
        student_answer = answer_map.get(q_no, "")

        if not student_answer or not student_answer.strip():
            result = {
                'marks': 0,
                'feedback': 'No answer was provided for this question.'
            }
        else:
            batch_result = batch_results.get(q_no)
            if batch_result:
                result = {
                    'marks': min(max(float(batch_result.get('marks', 0)), 0), q.marks),
                    'feedback': str(batch_result.get('feedback', '')).strip()
                    or 'Evaluated based on the submitted answer.'
                }
            else:
                result = evaluate_question(q.text, student_answer, q.marks)

        total_score += result["marks"]

        # ✅ SAVE QUESTION LEVEL
        QuestionEvaluation.objects.create(
            evaluation=evaluation,
            question=q,
            score=result["marks"],
            feedback=result["feedback"]
        )

    # ✅ SAVE FINAL
    evaluation.total_score = round(total_score, 2)
    evaluation.evaluated = True
    evaluation.save()

    messages.success(request, "Evaluation completed ✅")

    return redirect('view_submissions', exam_id=submission.exam.id)
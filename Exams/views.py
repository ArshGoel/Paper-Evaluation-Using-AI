import time
from django.conf import settings
from django.shortcuts import redirect, render, get_object_or_404
from django.http import FileResponse, Http404
from django.contrib import messages
import os

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
from django.core.files.base import ContentFile
import json
from .models import QuestionEvaluation, StudentSheetExtractVersion
from collections import defaultdict
from Exams.models import ExtractedQuestionAnswer


GEMINI_API_KEYS = settings.GEMINI_API_KEYS.copy()
GEMINI_MODELS = settings.GEMINI_MODELS.copy()

# 🔀 Shuffle both lists (true randomness)
random.shuffle(GEMINI_API_KEYS)
random.shuffle(GEMINI_MODELS)
def view_pdf(request, exam_id, file_type, student_id=None):
    exam = get_object_or_404(Exam, id=exam_id)

    if file_type == 'question_paper':
        file_field = exam.question_paper

    elif file_type == 'answer_key':
        file_field = exam.answer_key

    elif file_type == 'submission':
        submission = get_object_or_404(
            Submission,
            exam=exam,
            student_id=student_id
        )
        file_field = submission.file

    else:
        raise Http404('Invalid file type')

    if not file_field:
        raise Http404('No file found')

    file_path = file_field.path
    filename = os.path.basename(file_path)

    response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
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
            exam.full_url = request.build_absolute_uri(exam.question_paper.url)

    return render(request, 'teacher_exams.html', {
        'exams': exams
    })

def clean_json_output(raw_text):
    # remove ```json and ```
    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    return json.loads(cleaned)

def clean_question_number(q):
    return int(re.sub(r'\D', '', str(q)))  # removes '.', 'Q', etc

def save_exam_from_json(exam, raw_output):
    data = clean_json_output(raw_output)

    # ✅ Save instructions
    exam.instructions = data.get("instructions", "")
    exam.save()

    for q in data.get("questions", []):
        # avoid duplicates
        question, created = Question.objects.get_or_create(
            exam=exam,
            part = q.get("part"),
            question_number=clean_question_number(data['question_number']),
            defaults={
                "text": q.get("question_text"),
                "marks": q.get("marks") or 0,
            }
        )

        # if already exists → update
        if not created:
            question.text = q.get("question_text")
            question.marks = q.get("marks") or 0
            question.save()

        # 🔥 handle sub-questions
        for sub in q.get("sub_questions", []):
            SubQuestion.objects.update_or_create(
                question=question,
                label=sub.get("label"),
                defaults={
                    "text": sub.get("text"),
                    "marks": sub.get("marks")
                }
            )

def gemini_call_question_paper(file_url):
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
    response = requests.get(file_url)
    file_bytes = response.content
    for api_key in GEMINI_API_KEYS:
        try:
            print(f"\n🔑 Using KEY: {api_key[:6]}***")
            genai.configure(api_key=api_key)

            # 🔥 STEP 2: Send file bytes directly
            for model_name in GEMINI_MODELS:
                try:
                    print(f"🤖 Model: {model_name}")

                    model = genai.GenerativeModel(model_name)

                    response = model.generate_content(
                        [
                            prompt,
                            {
                                "mime_type": "application/pdf",
                                "data": file_bytes
                            }
                        ]
                    )

                    if response.text:
                        print("✅ SUCCESS")
                        return response.text

                except Exception as model_error:
                    err = str(model_error).lower()
                    print(f"❌ Model failed: {err}")

                    if "quota" in err or "limit" in err:
                        break

        except Exception as key_error:
            print(f"❌ Key failed: {key_error}")
            continue

    raise Exception("🚨 All Gemini keys + models exhausted")

def edit_exam_teacher(request, id):
    exam = get_object_or_404(Exam, id=id)

    if request.method == "POST":
        exam.title = request.POST.get('title')
        exam.total_marks = request.POST.get('total_marks')
        exam.date = request.POST.get('date')
        exam.instructions = request.POST.get('instructions')
        if request.POST.get("delete_qp"):
            if exam.question_paper:
                exam.question_paper.delete(save=False)
                exam.question_paper = None

        # 🔥 DELETE ANSWER KEY
        if request.POST.get("delete_ak"):
            if exam.answer_key:
                exam.answer_key.delete(save=False)
                exam.answer_key = None

        new_qp = request.FILES.get('question_paper')
        new_ak = request.FILES.get('answer_key')

        # 🔥 track if new file uploaded
        parse_needed = False

        if new_qp:
            exam.question_paper = new_qp
            parse_needed = True   # ✅ trigger parsing

        if new_ak:
            exam.answer_key = new_ak

        exam.save()

        # 🔥 AUTO PARSE AFTER SAVE
        if parse_needed:
            try:
                output = gemini_call_question_paper(exam.question_paper.url)

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
                file_path = submission.file.path if submission.file else None

                # ✅ Django delete
                if submission.file:
                    submission.file.delete(save=False)

                # ✅ EXTRA SAFETY (force delete)
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

                # ✅ delete db
                submission.delete()

        # 🔥 UPLOAD / REPLACE
        file = request.FILES.get('file')
        if file and student_id:
            student = User.objects.get(id=student_id)

            Submission.objects.update_or_create(
                student=student,
                exam=exam,
                defaults={'file': file}
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

        page_data["page"] = int(page_numbers[i])

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
                        return int(val)
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

        ExtractedQuestionAnswer.objects.create(
            extract_version=extract_version,
            question_number=q_no,
            answer_text=answer_text,

            contains_diagram=("diagram" in lower or "graph" in lower),
            contains_math=("=" in answer_text),
            contains_code=("def " in answer_text or "class " in answer_text)
        )

def extract_student_sheets(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    file_path = submission.file.path

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

    for api_key in GEMINI_API_KEYS:
        try:
            print(f"\n🔑 Using KEY: {api_key[:6]}***")
            genai.configure(api_key=api_key)

            uploaded_file = genai.upload_file(file_path)

            while uploaded_file.state.name == "PROCESSING":
                time.sleep(1)
                uploaded_file = genai.get_file(uploaded_file.name)

            for model_name in GEMINI_MODELS:
                try:
                    print(f"🤖 Model: {model_name}")

                    model = genai.GenerativeModel(model_name)

                    # ✅ START TIMER ONLY HERE (VALID CALL)
                    start_time = time.time()

                    response = model.generate_content(
                        [prompt, uploaded_file]
                    )

                    # ✅ END TIMER
                    end_time = time.time()

                    if response.text:
                        print("✅ SUCCESS")
                        final_output = response.text

                        processing_time_ms = int((end_time - start_time) * 1000)
                        break

                except Exception as model_error:
                    err = str(model_error).lower()
                    print(f"❌ Model failed: {err}")

                    # ❌ DO NOT measure time for failed calls
                    if "quota" in err or "limit" in err:
                        break

            if final_output:
                break

        except Exception as key_error:
            print(f"❌ Key failed: {key_error}")
            continue

    if not final_output:
        final_output = "Evaluation failed: All Gemini keys exhausted"
    # Step 1: Convert to JSON (temporary)
    parsed_json = parse_gemini_output(final_output)

    # Step 2: version
    version = StudentSheetExtractVersion.get_next_version(submission)

    # Step 3: create object
    obj = StudentSheetExtractVersion.objects.create(
        submission=submission,
        version_number=version,
        raw_markdown=final_output,
        structured_json=parsed_json,
        model_used=model_name,
        processing_time_ms=processing_time_ms//1000,
        primary_language=parsed_json.get("pages", [{}])[0].get("primary_language"),
        confidence_score=parsed_json.get("pages", [{}])[0].get("confidence_score") or 0,
    )
    StudentSheetExtractVersion.update_best_version(submission)
    obj.refresh_from_db()
    # Step 4: save file
    json_content = json.dumps(parsed_json, indent=4)

    obj.json_file.save(
        f"v{version}.json",
        ContentFile(json_content)
    )

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

    prompt = f"""
    You are a strict but fair exam evaluator.

    Evaluate the student's answer based on correctness, completeness, and clarity.

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
    3. If partially correct → give proportional marks
    4. If wrong → give 0 or very low marks
    5. If diagram is described → evaluate based on components/labels
    6. If math → check steps + final answer
    7. Do NOT be too lenient

    ----------------------------------------

    Return STRICT JSON ONLY:

    {{
        "marks": number,
        "feedback": "short explanation"
    }}
    """

    for api_key in GEMINI_API_KEYS:
        try:
            genai.configure(api_key=api_key)

            for model_name in GEMINI_MODELS:
                try:
                    model = genai.GenerativeModel(model_name)

                    response = model.generate_content(prompt)

                    if response.text:
                        raw = response.text.strip()

                        # 🔥 Clean JSON
                        raw = raw.replace("```json", "").replace("```", "").strip()

                        data = json.loads(raw)

                        marks = float(data.get("marks", 0))
                        feedback = data.get("feedback", "")

                        # ✅ Safety cap
                        marks = min(marks, float(max_marks))

                        return {
                            "marks": round(marks, 2),
                            "feedback": feedback
                        }

                except Exception as model_error:
                    err = str(model_error).lower()

                    # 🔁 switch API key if quota hit
                    if "quota" in err or "limit" in err:
                        break

        except Exception:
            continue

    # ❌ fallback (VERY IMPORTANT)
    return {
        "marks": 0,
        "feedback": "AI evaluation failed"
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

    answer_map = {
        str(a.question_number): a.answer_text
        for a in answers
    }

    questions = Question.objects.filter(exam=submission.exam)

    # 🔥 create / reset evaluation
    evaluation, _ = Evaluation.objects.get_or_create(
        submission=submission
    )

    # 🔥 clear old question evaluations
    evaluation.question_evaluations.all().delete()

    total_score = 0

    for q in questions:

        q_no = str(q.question_number)
        student_answer = answer_map.get(q_no, "")

        result = evaluate_question(
            q.text,
            student_answer,
            q.marks
        )

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
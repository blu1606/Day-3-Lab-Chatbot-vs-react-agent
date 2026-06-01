from typing import List, Dict, Any, Optional
import json
import os

# Reference: gaptutor-data-contract.yaml & gaptutor-tools-contract.yaml

def get_sessions() -> List[Dict[str, Any]]:
    """
    CONTRACT: get_sessions
    Description: Lấy danh sách mã và tiêu đề các buổi học đang lưu trên hệ thống.
    Input: None
    Output: List of SessionInfo (session_id, title, concepts)
    """
    return [
        {
            "session_id": "SESSION-RAG-20260601",
            "title": "Xây dựng Hệ thống RAG và Đánh giá Hiệu năng (Evaluation & Agentic Loops)",
            "concepts": ["evaluation", "prompting", "reasoning", "tool_use", "agentic_loops"]
        },
        {
            "session_id": "session-03",
            "title": "Kỹ thuật Prompt nâng cao & Khớp nối Công cụ (Advanced Prompting & Tool Use)",
            "concepts": ["prompting", "tool_use", "evaluation"]
        }
    ]

def get_session_cohort_data(session_id: str) -> Dict[str, Any]:
    """
    CONTRACT: get_session_cohort_data
    Description: Lấy toàn bộ dữ liệu học lực, hành vi và điểm số của cả lớp trong buổi học chỉ định.
    Input: session_id (str - Bắt buộc)
    Output: Dict chứa thông tin buổi học và danh sách học viên theo gaptutor-data-contract.yaml
    """
    # 1. Validate session_id
    sessions = get_sessions()
    session = None
    for s in sessions:
        if s["session_id"].lower() == session_id.lower():
            session = s
            break

    if not session:
        raise ValueError(f"SESSION_NOT_FOUND: Không tìm thấy thông tin buổi học '{session_id}'. Vui lòng chọn lại.")

    # 2. Load student data from data/students.json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "data", "students.json")

    if not os.path.exists(data_path):
        raise ValueError(f"Không tìm thấy tệp dữ liệu học viên tại {data_path}")

    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            students = json.load(f)
    except Exception as e:
        raise ValueError(f"Không thể đọc cơ sở dữ liệu học viên: {str(e)}")

    # 3. Apply Data Sanitization / Auto-Correction Rules for each student
    cleaned_students = []
    session_concepts = session["concepts"]

    for stu in students:
        # Clone to avoid mutating original loaded JSON in memory
        cleaned_stu = dict(stu)

        # Rule: Nếu thiếu background, gán mặc định là "non-tech"
        if not cleaned_stu.get("background") or cleaned_stu.get("background") not in ["ai-engineer", "student", "business", "non-tech"]:
            cleaned_stu["background"] = "non-tech"

        # Rule: Nếu thiếu diagnostic_score, tự động kế thừa lab_score
        if "diagnostic_score" not in cleaned_stu or cleaned_stu["diagnostic_score"] is None:
            cleaned_stu["diagnostic_score"] = cleaned_stu.get("lab_score", 0)

        # Rule: Nếu thiếu điểm số thành thạo từng concept hoặc rỗng, gán giá trị mặc định là 50
        if "concept_mastery" not in cleaned_stu or not isinstance(cleaned_stu["concept_mastery"], dict):
            cleaned_stu["concept_mastery"] = {}
        else:
            cleaned_stu["concept_mastery"] = dict(cleaned_stu["concept_mastery"])

        # Ensure all concepts defined in this session exist in concept_mastery
        for concept in session_concepts:
            if concept not in cleaned_stu["concept_mastery"] or cleaned_stu["concept_mastery"][concept] is None:
                cleaned_stu["concept_mastery"][concept] = 50

        cleaned_students.append(cleaned_stu)

    return {
        "session_id": session["session_id"],
        "cohort_name": f"Cohort {session['title']}",
        "students": cleaned_students
    }

def analyze_concept_mastery(students: List[Dict[str, Any]], concepts: List[str]) -> List[Dict[str, Any]]:
    """
    CONTRACT: analyze_concept_mastery
    Description: Phân tích định lượng điểm thành thạo của lớp để lọc ra những khái niệm học viên hiểu kém nhất.
    Input:
      - students: Danh sách học viên (List)
      - concepts: Các khái niệm cần kiểm tra (List)
    Output: Danh sách các khái niệm bị hổng (yếu) kèm điểm trung bình lớp và tỷ lệ học viên yếu (< 50%)
    """
    if not students or not concepts:
        return []

    analysis_results = []
    total_students = len(students)

    for concept in concepts:
        total_mastery = 0
        weak_student_count = 0

        for student in students:
            # Safe retrieval with auto-correction fallback of 50
            mastery_dict = student.get("concept_mastery", {})
            if not isinstance(mastery_dict, dict):
                mastery_dict = {}
            score = mastery_dict.get(concept)
            if score is None:
                score = 50
            
            total_mastery += score
            if score < 50:
                weak_student_count += 1

        average_mastery = round(total_mastery / total_students)
        weak_percentage = round((weak_student_count / total_students) * 100)

        analysis_results.append({
            "concept": concept,
            "average_mastery": average_mastery,
            "weak_student_count": weak_student_count,
            "weak_percentage": weak_percentage
        })

    # Sort results by average_mastery ascending (so that the weakest concepts are first)
    analysis_results.sort(key=lambda x: x["average_mastery"])

    return analysis_results


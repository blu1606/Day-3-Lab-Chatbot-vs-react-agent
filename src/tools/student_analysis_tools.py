import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Reference: gaptutor-data-contract.yaml, gaptutor-tools-contract.yaml & agent-tools.md

MASTERY_WEAK_CUTOFF = 50
PRACTICE_CUTOFF = 75
DATA_STUDENTS_PATH = Path(__file__).resolve().parents[2] / "data" / "students.json"

_SESSION_STUDENTS: Dict[str, List[Dict[str, Any]]] = {
    "session-03": [
        {
            "student_id": "s1",
            "name": "An",
            "background": "non-tech",
            "lab_completed": True,
            "lab_score": 86,
            "diagnostic_score": 42,
            "variant_question_result": "wrong",
            "activity_level": "low",
            "journey_log": "Em chưa rõ vì sao RAG trả lời sai",
            "concept_mastery": {
                "chunking": 42,
                "embedding": 35,
                "retrieval": 58,
                "evaluation": 20,
            },
        },
        {
            "student_id": "s2",
            "name": "Binh",
            "background": "student",
            "lab_completed": True,
            "lab_score": 74,
            "diagnostic_score": 65,
            "variant_question_result": "correct",
            "activity_level": "medium",
            "journey_log": "Em cần luyện thêm retrieval",
            "concept_mastery": {
                "chunking": 70,
                "embedding": 68,
                "retrieval": 62,
                "evaluation": 60,
            },
        },
        {
            "student_id": "s3",
            "name": "Linh",
            "background": "ai-engineer",
            "lab_completed": True,
            "lab_score": 95,
            "diagnostic_score": 88,
            "variant_question_result": "correct",
            "activity_level": "high",
            "journey_log": "Muốn thử reranking",
            "concept_mastery": {
                "chunking": 90,
                "embedding": 84,
                "retrieval": 82,
                "evaluation": 78,
            },
        },
    ]
}


def _average_mastery(student: Dict[str, Any]) -> float:
    mastery = student.get("concept_mastery") or {}
    if not mastery:
        return 0.0
    return sum(mastery.values()) / len(mastery)


def _weak_concepts(student: Dict[str, Any]) -> List[str]:
    mastery = student.get("concept_mastery") or {}
    return [
        concept
        for concept, score in mastery.items()
        if score < MASTERY_WEAK_CUTOFF
    ]


def _risk_map(risk_flags: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {risk["student_id"]: risk for risk in risk_flags or []}


def _load_real_students() -> List[Dict[str, Any]]:
    if not DATA_STUDENTS_PATH.exists():
        return []
    return json.loads(DATA_STUDENTS_PATH.read_text(encoding="utf-8"))


def _get_session_students(session_id: str) -> List[Dict[str, Any]]:
    return _load_real_students() + _SESSION_STUDENTS.get(session_id, [])

def detect_learning_risks(students: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    CONTRACT: detect_learning_risks
    Description: Quét cơ sở dữ liệu học tập của học viên để tự động phát hiện các biểu hiện rủi ro học thuật.
    Input: students (List - Bắt buộc)
    Output: List of StudentRiskFlag (student_id, name, flags, evidence)
    Rules cần kiểm tra:
      - fake_understanding: lab_completed == True và variant_question_result == "wrong"
      - silent_at_risk: activity_level == "low" và điểm thành thạo trung bình < 50
      - lab_following_not_understanding: diagnostic_score < 50 và lab_score > 80
    """
    risks = []

    for student in students:
        flags = []
        evidence = []
        average_mastery = _average_mastery(student)

        if student.get("lab_completed") is True and student.get("variant_question_result") == "wrong":
            flags.append("fake_understanding")
            evidence.append("Lab completed but variant question wrong")

        if student.get("activity_level") == "low" and average_mastery < MASTERY_WEAK_CUTOFF:
            flags.append("silent_at_risk")
            evidence.append(f"Low activity with average mastery {average_mastery:.1f}")

        if student.get("diagnostic_score", 0) < MASTERY_WEAK_CUTOFF and student.get("lab_score", 0) > 80:
            flags.append("lab_following_not_understanding")
            evidence.append(
                f"Diagnostic score {student.get('diagnostic_score')} but lab score {student.get('lab_score')}"
            )

        for concept in _weak_concepts(student):
            evidence.append(f"{concept} mastery = {student['concept_mastery'][concept]}")

        if flags:
            risks.append(
                {
                    "student_id": student["student_id"],
                    "name": student["name"],
                    "flags": flags,
                    "evidence": evidence,
                }
            )

    return risks

def group_students(students: List[Dict[str, Any]], risk_flags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    CONTRACT: group_students
    Description: Tự động phân chia học viên vào 3 làn học tập dựa trên năng lực và cờ rủi ro đã phát hiện.
    Input:
      - students: Danh sách học viên
      - risk_flags: Danh sách các cờ rủi ro đã quét được
    Output: Danh sách 3 nhóm làn học tập (Needs Foundation, Needs Practice, Ready for Advanced)
    Rules cần phân nhóm:
      - Needs Foundation: Điểm TB < 50% hoặc bị cờ silent_at_risk
      - Needs Practice: Điểm TB từ 50% đến < 75% hoặc bị cờ fake_understanding/lab_following_not_understanding
      - Ready for Advanced: Điểm TB >= 75% và không có bất kỳ cờ cảnh báo nào
    """
    groups = [
        {
            "group_name": "Needs Foundation",
            "students": [],
            "reason": "Mastery thấp hoặc có cờ silent_at_risk.",
            "weak_concepts": [],
        },
        {
            "group_name": "Needs Practice",
            "students": [],
            "reason": "Mastery trung bình hoặc có dấu hiệu làm được lab nhưng chưa hiểu sâu.",
            "weak_concepts": [],
        },
        {
            "group_name": "Ready for Advanced",
            "students": [],
            "reason": "Mastery tốt và không có cờ rủi ro.",
            "weak_concepts": [],
        },
    ]
    by_name = {group["group_name"]: group for group in groups}
    risks_by_student = _risk_map(risk_flags)

    for student in students:
        student_risk = risks_by_student.get(student["student_id"], {})
        flags = set(student_risk.get("flags", []))
        average_mastery = _average_mastery(student)

        if average_mastery < MASTERY_WEAK_CUTOFF or "silent_at_risk" in flags:
            target = by_name["Needs Foundation"]
        elif average_mastery < PRACTICE_CUTOFF or flags:
            target = by_name["Needs Practice"]
        else:
            target = by_name["Ready for Advanced"]

        target["students"].append(
            {
                "student_id": student["student_id"],
                "name": student["name"],
            }
        )
        target["weak_concepts"].extend(_weak_concepts(student))

    for group in groups:
        group["weak_concepts"] = sorted(set(group["weak_concepts"]))

    return groups

def generate_remediation_plan(groups: List[Dict[str, Any]], weak_concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    CONTRACT: generate_remediation_plan
    Description: Đề xuất các hành động khắc phục cụ thể theo từng nhóm năng lực.
    Input:
      - groups: Danh sách các nhóm học viên
      - weak_concepts: Danh sách các concept yếu của cả lớp
    Output: Lộ trình hành động chi tiết dành riêng cho mentor hỗ trợ từng nhóm (Needs Foundation, Needs Practice, Ready for Advanced)
    """
    cohort_weak_names = [item["concept"] for item in weak_concepts]
    focus_text = ", ".join(cohort_weak_names[:3]) if cohort_weak_names else "core concepts"
    plan = []

    for group in groups:
        group_name = group["group_name"]

        if group_name == "Needs Foundation":
            actions = [
                f"Ôn lại nền tảng {focus_text} bằng notebook rút gọn.",
                "Làm 3 câu diagnostic cơ bản trước buổi tiếp theo.",
                "Mentor check lại evidence từng học viên trước khi giao bài nâng cao.",
            ]
        elif group_name == "Needs Practice":
            actions = [
                f"Làm mini-task debug lỗi liên quan {focus_text}.",
                "Giải thích claim -> evidence -> recommendation cho một case RAG sai.",
                "So sánh output trước/sau khi thay đổi retrieval hoặc chunking strategy.",
            ]
        else:
            actions = [
                "Giao bài advanced: thử reranking hoặc custom evaluation metric.",
                "Yêu cầu học viên viết reflection ngắn về trade-off trong RAG pipeline.",
                "Khuyến khích hỗ trợ peer review cho nhóm Needs Practice.",
            ]

        plan.append(
            {
                "group_name": group_name,
                "actions": actions,
            }
        )

    return plan

def generate_report_student(students: Optional[List[Dict[str, Any]]] = None, session_id: str = "session-03") -> Dict[str, Any]:
    """
    CONTRACT: generate_report_student
    Description: Tạo response API tổng hợp tình trạng học tập của toàn bộ học viên.
    Input:
      - students: Danh sách học viên tùy chọn. Nếu không truyền, tool sẽ đọc data/students.json và mock fallback.
      - session_id: Mã buổi học dùng khi cần fallback dữ liệu.
    Output: Dict JSON-serializable gồm summary, số lượng theo nhóm, risk flags, và report từng học viên.
    """
    report_students = students if students is not None else _get_session_students(session_id)
    risk_flags = detect_learning_risks(report_students)
    groups = group_students(report_students, risk_flags)
    risks_by_student = _risk_map(risk_flags)
    group_by_student = {
        student["student_id"]: group["group_name"]
        for group in groups
        for student in group["students"]
    }
    group_counts = {
        group["group_name"]: len(group["students"])
        for group in groups
    }

    student_reports = []
    for student in report_students:
        average_mastery = round(_average_mastery(student))
        weak_concepts = _weak_concepts(student)
        risk = risks_by_student.get(student["student_id"], {})
        risk_flags_for_student = risk.get("flags", [])
        evidence = risk.get("evidence", [])
        group_name = group_by_student.get(student["student_id"], "Unassigned")

        if group_name == "Needs Foundation":
            risk_level = "high"
        elif group_name == "Needs Practice":
            risk_level = "medium"
        else:
            risk_level = "low"

        if weak_concepts:
            diagnosis = (
                f"{student['name']} cần hỗ trợ ở {', '.join(weak_concepts)} "
                f"với average mastery {average_mastery}%."
            )
            next_actions = [f"Ôn lại {concept}" for concept in weak_concepts[:3]]
        else:
            diagnosis = (
                f"{student['name']} đang nắm tốt các concept chính "
                f"với average mastery {average_mastery}%."
            )
            next_actions = ["Giao bài nâng cao hoặc peer review cho nhóm cần luyện tập."]

        if student.get("variant_question_result") == "wrong":
            next_actions.append("Làm lại câu hỏi biến thể và giải thích bằng evidence.")

        student_reports.append(
            {
                "student_id": student["student_id"],
                "name": student["name"],
                "background": student.get("background", "non-tech"),
                "average_mastery": average_mastery,
                "group_name": group_name,
                "risk_level": risk_level,
                "risk_flags": risk_flags_for_student,
                "weak_concepts": weak_concepts,
                "evidence": evidence,
                "diagnosis": diagnosis,
                "next_actions": next_actions,
            }
        )

    return {
        "report_type": "student_status_report",
        "total_students": len(report_students),
        "at_risk_count": len(risk_flags),
        "group_counts": group_counts,
        "risk_flags": risk_flags,
        "students": student_reports,
    }

def get_student_detail(student_id: str, session_id: str) -> Dict[str, Any]:
    """
    CONTRACT: get_student_detail
    Description: Truy vấn sâu thông tin của một học viên cụ thể để Next.js render bảng thông tin cá nhân.
    Input:
      - student_id: Mã học viên (Bắt buộc)
      - session_id: Mã buổi học (Bắt buộc)
    Output: Chi tiết điểm thành thạo, các bằng chứng rủi ro phát hiện được, nhận định chẩn đoán và hành động tiếp theo
    """
    students = _get_session_students(session_id)
    student = next((item for item in students if item["student_id"] == student_id), None)

    if not student:
        raise ValueError(f"Student {student_id} not found in session {session_id}")

    risks = detect_learning_risks([student])
    evidence = risks[0]["evidence"] if risks else []
    weak_concepts = _weak_concepts(student)

    if weak_concepts:
        diagnosis = (
            f"{student['name']} cần hỗ trợ ở {', '.join(weak_concepts)}; "
            "kết luận dựa trên mastery và risk evidence, không dựa trên background."
        )
    else:
        diagnosis = (
            f"{student['name']} đang nắm tốt các concept chính và có thể nhận nhiệm vụ nâng cao."
        )

    next_actions = [
        f"Ôn lại {concept}" for concept in weak_concepts[:3]
    ] or ["Thử bài nâng cao về reranking hoặc custom evaluation metric"]

    if student.get("variant_question_result") == "wrong":
        next_actions.append("Làm lại câu hỏi biến thể và giải thích bằng evidence")

    return {
        "student_id": student["student_id"],
        "name": student["name"],
        "background": student["background"],
        "concept_mastery": student["concept_mastery"],
        "evidence": evidence,
        "diagnosis": diagnosis,
        "next_actions": next_actions,
    }

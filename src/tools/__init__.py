from src.tools.cohort_diagnostic_tools import (
    get_sessions,
    get_session_cohort_data,
    analyze_concept_mastery
)
from src.tools.student_analysis_tools import (
    detect_learning_risks,
    group_students,
    generate_remediation_plan,
    get_student_detail
)

# Reference: gaptutor-tools-contract.yaml
# Danh sách đặc tả công cụ đầy đủ (Tool Specifications) phục vụ ReActAgent hệ thống
ALL_TOOLS = [
    {
        "name": "get_sessions",
        "description": "Lấy danh sách mã và tiêu đề các buổi học đang lưu trên hệ thống để AI xác định đúng ID buổi học.",
        "input_schema": {},
        "output_schema": {
            "sessions": "array of session info (session_id, title, concepts)"
        },
        "func": get_sessions
    },
    {
        "name": "get_session_cohort_data",
        "description": "Lấy toàn bộ dữ liệu học lực, hành vi và điểm số chi tiết của tập thể học sinh trong buổi học được chỉ định.",
        "input_schema": {
            "session_id": "string (bắt buộc)"
        },
        "output_schema": {
            "session_id": "string",
            "cohort_name": "string",
            "students": "array of student diagnostic data"
        },
        "func": get_session_cohort_data
    },
    {
        "name": "analyze_concept_mastery",
        "description": "Phân tích định lượng điểm thành thạo của lớp để lọc ra những khái niệm học viên hiểu kém nhất.",
        "input_schema": {
            "students": "array of student data (bắt buộc)",
            "concepts": "array of strings (bắt buộc)"
        },
        "output_schema": "array of concept analysis with average mastery and weak percentage",
        "func": analyze_concept_mastery
    },
    {
        "name": "detect_learning_risks",
        "description": "Quét cơ sở dữ liệu học tập của học viên để tự động phát hiện các biểu hiện rủi ro học thuật như fake_understanding, silent_at_risk, lab_following_not_understanding.",
        "input_schema": {
            "students": "array of student data (bắt buộc)"
        },
        "output_schema": "array of student risk flags with student_id, name, flags and evidence",
        "func": detect_learning_risks
    },
    {
        "name": "group_students",
        "description": "Tự động phân chia học viên vào 3 làn học tập thích ứng (Needs Foundation, Needs Practice, Ready for Advanced) dựa trên năng lực và cờ rủi ro.",
        "input_schema": {
            "students": "array of student data (bắt buộc)",
            "risk_flags": "array of risk flags (bắt buộc)"
        },
        "output_schema": "array of 3 student groups with group_name, students, reasons and weak_concepts",
        "func": group_students
    },
    {
        "name": "generate_remediation_plan",
        "description": "Đề xuất các bước khắc phục lỗ hổng kiến thức và lộ trình hành động chi tiết theo từng nhóm yếu.",
        "input_schema": {
            "groups": "array of student groups (bắt buộc)",
            "weak_concepts": "array of weak concept objects (bắt buộc)"
        },
        "output_schema": "array of remediation plans per group containing specific recommended actions",
        "func": generate_remediation_plan
    },
    {
        "name": "get_student_detail",
        "description": "Lấy báo cáo chẩn đoán chi tiết và bằng chứng rủi ro học tập cụ thể của riêng một học viên.",
        "input_schema": {
            "student_id": "string (bắt buộc)",
            "session_id": "string (bắt buộc)"
        },
        "output_schema": "detailed student diagnostic profile with evidence, diagnosis and next actions",
        "func": get_student_detail
    }
]

# Từ điển tra cứu nhanh để Agent gọi hàm động bằng tên
TOOL_REGISTRY = {t["name"]: t["func"] for t in ALL_TOOLS}

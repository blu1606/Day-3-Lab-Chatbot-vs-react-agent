from typing import List, Dict, Any, Optional

# Reference: gaptutor-data-contract.yaml, gaptutor-tools-contract.yaml & agent-tools.md

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
    # TODO: Học viên tự hiện thực logic phát hiện rủi ro học tập
    pass

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
    # TODO: Học viên tự hiện thực logic phân chia làn học tập thích ứng
    pass

def generate_remediation_plan(groups: List[Dict[str, Any]], weak_concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    CONTRACT: generate_remediation_plan
    Description: Đề xuất các hành động khắc phục cụ thể theo từng nhóm năng lực.
    Input:
      - groups: Danh sách các nhóm học viên
      - weak_concepts: Danh sách các concept yếu của cả lớp
    Output: Lộ trình hành động chi tiết dành riêng cho mentor hỗ trợ từng nhóm (Needs Foundation, Needs Practice, Ready for Advanced)
    """
    # TODO: Học viên tự hiện thực đề xuất kế hoạch khắc phục lỗ hổng
    pass

def get_student_detail(student_id: str, session_id: str) -> Dict[str, Any]:
    """
    CONTRACT: get_student_detail
    Description: Truy vấn sâu thông tin của một học viên cụ thể để Next.js render bảng thông tin cá nhân.
    Input:
      - student_id: Mã học viên (Bắt buộc)
      - session_id: Mã buổi học (Bắt buộc)
    Output: Chi tiết điểm thành thạo, các bằng chứng rủi ro phát hiện được, nhận định chẩn đoán và hành động tiếp theo
    """
    # TODO: Học viên tự hiện thực lấy chi tiết thông tin và chẩn đoán học viên
    pass

from typing import List, Dict, Any, Optional

# Reference: gaptutor-data-contract.yaml & gaptutor-tools-contract.yaml

def get_sessions() -> List[Dict[str, Any]]:
    """
    CONTRACT: get_sessions
    Description: Lấy danh sách mã và tiêu đề các buổi học đang lưu trên hệ thống.
    Input: None
    Output: List of SessionInfo (session_id, title, concepts)
    """
    # TODO: Học viên tự hiện thực logic truy xuất danh sách buổi học
    pass

def get_session_cohort_data(session_id: str) -> Dict[str, Any]:
    """
    CONTRACT: get_session_cohort_data
    Description: Lấy toàn bộ dữ liệu học lực, hành vi và điểm số của cả lớp trong buổi học chỉ định.
    Input: session_id (str - Bắt buộc)
    Output: Dict chứa thông tin buổi học và danh sách học viên theo gaptutor-data-contract.yaml
    """
    # TODO: Học viên tự hiện thực logic lấy dữ liệu lớp học
    pass

def analyze_concept_mastery(students: List[Dict[str, Any]], concepts: List[str]) -> List[Dict[str, Any]]:
    """
    CONTRACT: analyze_concept_mastery
    Description: Phân tích định lượng điểm thành thạo của lớp để lọc ra những khái niệm học viên hiểu kém nhất.
    Input:
      - students: Danh sách học viên (List)
      - concepts: Các khái niệm cần kiểm tra (List)
    Output: Danh sách các khái niệm bị hổng (yếu) kèm điểm trung bình lớp và tỷ lệ học viên yếu (< 50%)
    """
    # TODO: Học viên tự hiện thực logic tính toán điểm thành thạo các khái niệm RAG
    pass

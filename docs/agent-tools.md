# 🛠️ Agentic Tools Specification - GapTutor Agent Demo

Hệ thống AI Agent hoạt động trên **FastAPI Backend** dựa vào cơ chế gọi công cụ (Tool Calling) để tương tác với các hàm logic chẩn đoán phi cấu trúc và có cấu trúc. 

Dưới đây là danh sách các công cụ, định nghĩa tham số đầu vào/đầu ra và các quy tắc (rules) hoạt động.

---

## 1. Công cụ chẩn đoán Cohort & Session

### 1.1. Công cụ: `get_sessions`
*   **Mô tả:** Truy xuất danh sách các buổi học đang lưu trên hệ thống để AI xác định đúng ID buổi học từ câu hỏi của Mentor.
*   **Tham số đầu vào:** Không yêu cầu.
*   **Tham số trả về:** Danh sách đối tượng chứa mã buổi học (`session_id`), tiêu đề buổi học (`title`), và danh sách các concept lý thuyết (`concepts`).

### 1.2. Công cụ: `get_session_cohort_data`
*   **Mô tả:** Lấy toàn bộ dữ liệu học lực, hành vi và điểm số chi tiết của tập thể học sinh trong buổi học được chỉ định.
*   **Tham số đầu vào:** `session_id` (Mã định danh buổi học - Bắt buộc).
*   **Tham số trả về:** Một đối tượng chứa metadata buổi học và một mảng (array) danh sách học viên kèm theo đầy đủ điểm lab, điểm kiểm tra, và điểm thành thạo từng concept.

### 1.3. Công cụ: `analyze_concept_mastery`
*   **Mô tả:** Phân tích định lượng điểm thành thạo của lớp để lọc ra những khái niệm học viên hiểu kém nhất.
*   **Tham số đầu vào:** Danh sách học viên (`students`) và danh sách các khái niệm cần kiểm tra (`concepts`).
*   **Tham số trả về:** Danh sách các khái niệm bị gán nhãn yếu (`weak_concepts`) kèm theo điểm trung bình của lớp và tỷ lệ học viên bị hổng kiến thức này (Mastery dưới 50%).

---

## 2. Công cụ Phân tích Rủi ro & Phân nhóm thích ứng

### 2.1. Công cụ: `detect_learning_risks`
*   **Mô tả:** Quét cơ sở dữ liệu học tập của học viên để tự động phát hiện các biểu hiện rủi ro học thuật dựa trên các quy tắc chốt chặn.
*   **Tham số đầu vào:** Danh sách học viên (`students`).
*   **Tham số trả về:** Danh sách học viên bị gắn cờ rủi ro (`risk_flags`) kèm bằng chứng (evidence) thực tế.
*   **Quy tắc phân tích (Risk Detection Rules):**
    *   **Hiểu giả tạo (`fake_understanding`):** Gắn cờ khi học viên hoàn thành bài lab (`lab_completed` là `true`) nhưng lại làm sai câu hỏi biến thể (`variant_question_result` là `wrong`).
    *   **Nguy cơ âm thầm (`silent_at_risk`):** Gắn cờ khi học viên ít hoạt động (`activity_level` là `low`) và có điểm thành thạo trung bình dưới 50%.
    *   **Học vẹt làm lab (`lab_following_not_understanding`):** Gắn cờ khi điểm thi chẩn đoán độc lập thấp dưới 50% trong khi điểm bài lab thực hành lại cao trên 80%.

### 2.2. Công cụ: `group_students`
*   **Mô tả:** Tự động phân chia học viên vào 3 làn học tập dựa trên năng lực và cờ rủi ro đã phát hiện.
*   **Tham số đầu vào:** Danh sách học viên (`students`) và danh sách cờ rủi ro (`risk_flags`).
*   **Tham số trả về:** Danh sách 3 nhóm làn học tập kèm lý do phân loại và các concept bị hổng tương ứng:
    *   **Needs Foundation:** Dành cho học viên điểm trung bình dưới 50% hoặc bị cờ `silent_at_risk`.
    *   **Needs Practice:** Dành cho học viên điểm trung bình từ 50% đến dưới 75% hoặc bị cờ `fake_understanding`.
    *   **Ready for Advanced:** Dành cho học viên điểm trung bình trên 75% và không có cờ rủi ro.

### 2.3. Công cụ: `generate_remediation_plan`
*   **Mô tả:** Đề xuất các hành động khắc phục cụ thể theo từng nhóm năng lực.
*   **Tham số đầu vào:** Danh sách các nhóm học viên (`groups`) và danh sách các concept yếu của cohort (`weak_concepts`).
*   **Tham số trả về:** Lộ trình hành động chi tiết dành riêng cho mentor hỗ trợ từng nhóm.

### 2.4. Công cụ: `get_student_detail`
*   **Mô tả:** Truy vấn sâu thông tin của một học viên để Next.js render bảng thông tin cá nhân.
*   **Tham số đầu vào:** `student_id` (Mã học viên - Bắt buộc) và `session_id` (Mã buổi học dùng để kiểm tra quyền truy cập cohort - Bắt buộc).
*   **Tham số trả về:** Chi tiết điểm thành thạo, các bằng chứng rủi ro phát hiện được, nhận định chẩn đoán (diagnosis) và hành động tiếp theo cần thực hiện.

# 🌐 FastAPI Endpoints Specification - GapTutor Agent Demo

Tài liệu này đặc tả các điểm cuối API (Endpoints) được cung cấp bởi Backend chạy bằng **FastAPI** phục vụ cho **Next.js UI**. Các phản hồi đều tuân thủ chuẩn JSON và được cấu trúc sẵn để Next.js dễ dàng xử lý.

---

## 1. Danh sách Endpoints

### 1.1. Lấy danh sách buổi học (`GET /api/v1/sessions`)
*   **Mô tả:** Trả về toàn bộ danh sách các buổi học đang được chẩn đoán cùng danh sách khái niệm (concepts) cốt lõi của buổi học đó.
*   **Phản hồi (200 OK - Application/JSON):**
    *   `session_id` (String): Mã định danh duy nhất của buổi học.
    *   `title` (String): Tên hiển thị của buổi học.
    *   `concepts` (List of Strings): Các khái niệm chuyên sâu sẽ được đánh giá.

---

### 1.2. Lấy dữ liệu cohort theo buổi học (`GET /api/v1/sessions/{session_id}/cohort`)
*   **Mô tả:** Truy xuất dữ liệu học viên (học lực, hành vi, bài lab) của một buổi học để render bảng tổng quan.
*   **Tham số đường dẫn (Path Parameter):**
    *   `session_id` (String): Mã buổi học (ví dụ: `session-03`).
*   **Phản hồi (200 OK - Application/JSON):**
    *   `session_id` (String): Mã buổi học đã chọn.
    *   `title` (String): Tên buổi học.
    *   `students` (Array of Objects): Danh sách chi tiết thông tin học viên của lớp học.

---

### 1.3. Thực thi phân tích chẩn đoán thời gian thực (`POST /api/v1/diagnose`)
*   **Mô tả:** Nhận yêu cầu chẩn đoán và trả về **Luồng Sự Kiện Thời Gian Thực (Server-Sent Events - SSE)** giúp Next.js hiển thị tiến trình tư duy (thinking logs) và hoạt động gọi công cụ (tool calling) trực quan.
*   **Yêu cầu (Request Body - Application/JSON):**
    *   `session_id` (String): ID của buổi học muốn phân tích.
    *   `query` (String): Truy vấn tự nhiên từ Mentor.
*   **Phản hồi (200 OK - Content-Type: `text/event-stream`):**
    *   Trả về chuỗi sự kiện được phân tách bằng cấu trúc `data: {JSON_EVENT_STRING}\n\n`.
    *   **Các loại sự kiện stream (Event Types):**
        *   `agent_thought`: Chứa suy nghĩ nội bộ (internal reasoning) của Agent.
        *   `tool_start`: Báo hiệu bắt đầu gọi một công cụ (ví dụ: `detect_learning_risks`).
        *   `tool_end`: Kết quả trả về và thời gian chạy (latency) của công cụ đó.
        *   `agent_metrics`: Tổng kết số token tiêu thụ và hiệu năng cuối cùng.
        *   `agent_result`: Toàn bộ kết quả chẩn đoán cuối cùng (summary, groups, remediation).

---

### 1.4. Lấy chi tiết chỉ số Telemetry và Logs của Agent (`GET /api/v1/diagnose/{task_id}/telemetry`)
*   **Mô tả:** Truy xuất báo cáo chi tiết về nhật ký suy nghĩ, các công cụ đã gọi, thời gian chạy và số lượng tokens tiêu thụ của một phiên chạy chẩn đoán cũ.
*   **Tham số đường dẫn (Path Parameter):**
    *   `task_id` (String): Mã định danh duy nhất của lượt chạy chẩn đoán.
*   **Phản hồi (200 OK - Application/JSON):**
    *   `task_id` (String): Mã định danh của task.
    *   `session_id` (String): ID buổi học liên quan.
    *   `timestamp` (String): Thời gian thực hiện.
    *   `thinking_logs` (List of Strings): Toàn bộ các dòng suy luận nội bộ của Agent.
    *   `tool_calls` (Array): Lịch sử gọi các công cụ kèm input, output, trạng thái và thời gian chạy.
    *   `telemetry_metrics` (Object): Đo lường hiệu năng, trạng thái timeout, tổng số token sử dụng và ước tính chi phí.

---

### 1.5. Lấy chi tiết chẩn đoán một học viên (`GET /api/v1/students/{student_id}`)
*   **Mô tả:** Trả về báo cáo chi tiết, bằng chứng (evidence) và đề xuất khắc phục lỗi sai dành cho một học viên cụ thể khi Mentor click chọn trên Next.js UI.
*   **Tham số đường dẫn (Path Parameter):**
    *   `student_id` (String): Mã học viên cần truy vấn.
*   **Query Parameter:**
    *   `session_id` (String): Mã buổi học dùng để kiểm tra quyền truy cập cohort.
*   **Phản hồi (200 OK - Application/JSON):**
    *   `student_id` (String): ID học viên.
    *   `name` (String): Tên học viên.
    *   `background` (String): Nền tảng đầu vào.
    *   `concept_mastery` (Object): Điểm thành thạo của học viên theo từng kỹ năng.
    *   `evidence` (List of Strings): Các dữ liệu chứng minh cho chẩn đoán (ví dụ: điểm lab cao nhưng sai câu hỏi biến thể).
    *   `diagnosis` (String): Nhận định cụ thể của hệ thống về nguyên nhân yếu.
    *   `next_actions` (List of Strings): Các hành động cụ thể học viên cần thực hiện tiếp theo.

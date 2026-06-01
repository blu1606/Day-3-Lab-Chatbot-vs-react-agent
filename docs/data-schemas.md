# 🗂️ Data & Rendering Schemas Specification - GapTutor Agent Demo

Tài liệu này định nghĩa cấu trúc dữ liệu (Data Schemas) tại Backend (FastAPI Pydantic Models) và định dạng JSON tương thích được Next.js UI dùng để render các thành phần giao diện.

---

## 1. Cấu trúc dữ liệu Học viên (Student Schema Definition)
Mỗi học viên tham gia hệ thống được mô tả bằng mô hình dữ liệu chứa các thuộc tính định lượng và định tính:

*   `student_id` (String): Mã định danh duy nhất (Bắt buộc).
*   `name` (String): Họ và tên học viên.
*   `background` (Enum: "ai-engineer", "student", "business", "non-tech"): Nền tảng học thuật của học viên.
*   `lab_completed` (Boolean): Trạng thái hoàn thành bài thực hành Lab (True/False).
*   `lab_score` (Integer, 0 - 100): Điểm số đánh giá của bài Lab.
*   `diagnostic_score` (Integer, 0 - 100): Điểm kiểm tra chẩn đoán nhanh độc lập.
*   `variant_question_result` (Enum: "correct", "wrong"): Kết quả giải câu hỏi biến thể ứng dụng.
*   `activity_level` (Enum: "low", "medium", "high"): Mức độ tương tác của học viên trên hệ thống LMS/Discord.
*   `journey_log` (String): Ghi nhận phản hồi tự học hoặc khó khăn mà học viên tự báo cáo.
*   `concept_mastery` (Dict/Map): Cặp khóa-giá trị ánh xạ từ Tên Khái niệm (String) sang Điểm Thành Thạo (Integer, 0 - 100).

---

## 2. Giao thức cấu trúc phản hồi render UI (Frontend Rendering JSON Structures)

Để Next.js render giao diện trực quan hóa dữ liệu mà không cần tính toán thêm, FastAPI chuẩn hóa dữ liệu trả về theo các cụm thành phần UI sau:

### 2.1. Thẻ tóm tắt Cohort (Cohort Summary Cards)
Định nghĩa dữ liệu tổng quan cho khối chỉ số trên cùng giao diện:
*   `average_score` (Integer): Điểm trung bình của cả lớp.
*   `completion_rate` (Integer): Tỷ lệ hoàn thành bài Lab (%).
*   `at_risk_count` (Integer): Số học viên đang gặp rủi ro học tập.
*   `total_students` (Integer): Tổng số học viên được chẩn đoán trong Cohort.

### 2.2. Bản đồ Khái niệm Yếu (Weak Concepts)
Định nghĩa danh sách các concept có điểm số kém nhất để render biểu đồ cột:
*   `concept` (String): Tên khái niệm (ví dụ: `evaluation`).
*   `average_mastery` (Integer): Điểm thành thạo trung bình của cohort.
*   `weak_student_count` (Integer): Số học viên có mastery dưới ngưỡng yếu, mặc định dưới 50%.
*   `weak_percentage` (Integer): Tỷ lệ phần trăm học viên yếu trên tổng số lớp (%).

### 2.3. Bảng Phân nhóm Lộ trình (Student Groups)
Phân chia danh sách học viên theo 3 làn học tập nhằm cá nhân hóa bài tập bổ sung:
*   `group_name` (Enum: "Needs Foundation", "Needs Practice", "Ready for Advanced"): Tên làn học tập.
*   `students` (List of Objects): Danh sách học viên thuộc nhóm, mỗi object gồm `student_id` và `name`.
*   `reason` (String): Lý do phân nhóm dựa trên dữ liệu bằng chứng.
*   `weak_concepts` (List of Strings): Các khái niệm nhóm này cần bổ túc gấp.

### 2.4. Kế hoạch Khắc phục (Remediation Plan)
Danh sách các hành động mentor cần thực hiện cho từng nhóm:
*   `group_name` (String): Tên nhóm nhận lộ trình.
*   `actions` (List of Strings): Các đầu việc chi tiết được đề xuất.

---

## 3. Cấu trúc dữ liệu Đo lường Hiệu năng & Logs Agent (Telemetry & Logs Schema)

Next.js UI sử dụng cấu trúc dữ liệu này để render bảng thông tin "Thought Process Console", sơ đồ timeline gọi các tools, và bảng thống kê chi phí API (tokens).

### 3.1. Đối tượng Lịch sử gọi Tool (`ToolCallRecord`)
Mô tả chi tiết một lần Agent gọi công cụ:
*   `tool_name` (String): Tên công cụ được gọi (ví dụ: `detect_learning_risks`).
*   `arguments` (Dict): Tham số truyền vào công cụ.
*   `result_summary` (String): Tóm tắt ngắn gọn kết quả công cụ trả về.
*   `status` (Enum: "success", "failed", "timeout"): Trạng thái thực thi.
*   `execution_time_ms` (Integer): Thời gian chạy của công cụ (mili-giây).

### 3.2. Chỉ số Đo lường Hiệu năng và Token (`TelemetryMetrics`)
Thống kê tài nguyên tiêu thụ của AI Agent trong một phiên chẩn đoán:
*   `total_execution_time_ms` (Integer): Tổng thời gian thực thi của Agent (từ khi nhận request đến khi hoàn thành).
*   `is_fallback_triggered` (Boolean): Có kích hoạt cơ chế dự phòng toán học tĩnh (FastAPI local fallback) do AI bị lỗi/timeout hay không.
*   `prompt_tokens` (Integer): Số lượng token đầu vào (Input Tokens).
*   `completion_tokens` (Integer): Số lượng token đầu ra do AI sinh (Output Tokens).
*   `total_tokens` (Integer): Tổng số token tiêu thụ.
*   `estimated_cost_usd` (Float): Chi phí ước tính bằng USD (tính theo bảng giá mô hình AI sử dụng).

### 3.3. Mô hình Báo cáo Telemetry hoàn chỉnh (`AgentTelemetryReport`)
Cấu trúc JSON tổng hợp trả về cho API `GET /api/v1/diagnose/{task_id}/telemetry`:
*   `task_id` (String): ID định danh phiên chạy.
*   `session_id` (String): ID buổi học được chẩn đoán.
*   `timestamp` (String): Thời gian chạy (ISO Format).
*   `thinking_logs` (List of Strings): Các bước lập luận, diễn giải logic của AI Agent theo thứ tự thời gian.
*   `tool_calls` (List of `ToolCallRecord` Objects): Timeline các công cụ đã được gọi.
*   `telemetry_metrics` (Object: `TelemetryMetrics` Schema): Số liệu đo lường hiệu năng và token.

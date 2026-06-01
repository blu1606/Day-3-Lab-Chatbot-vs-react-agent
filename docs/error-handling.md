# 🛡️ Error Handling Specification - GapTutor Agent Demo

Tài liệu này đặc tả quy trình phát hiện, cô lập và xử lý sự cố trong quá trình trao đổi dữ liệu giữa **Next.js UI**, **FastAPI Backend** và các dịch vụ AI bên ngoài. Hệ thống áp dụng triết lý thiết kế tự phục hồi (resilient design) để đảm bảo trải nghiệm giảng dạy liên tục.

---

## 1. Lỗi Không Tìm Thấy Buổi Học (Session Mismatch)
*   **Tình huống:** Người dùng gửi yêu cầu chẩn đoán cho một `session_id` không tồn tại hoặc dữ liệu bị khuyết.
*   **Cơ chế xử lý tại Backend (FastAPI):**
    *   Sử dụng Middleware hoặc Exception Handler để đánh chặn các giá trị ID không hợp lệ.
    *   Tự động ghi lại nhật ký sự kiện cấp độ hệ thống để TA/Mentor có thể debug sau này.
    *   Trả lời bằng mã lỗi HTTP `404 Not Found` kèm danh sách các ID buổi học đang có hiệu lực.
*   **Cơ chế xử lý tại UI (Next.js):**
    *   Next.js chặn lỗi 404, hiển thị thông báo lỗi trực quan trên góc màn hình và tự động kích hoạt lại Session Selector để đưa mentor về buổi học hợp lệ gần nhất.

---

## 2. Sự Cố Gián Đoạn Kết Nối AI (AI Microservice Timeout)
*   **Tình huống:** Quá trình gọi API phân tích ngữ nghĩa hoặc tạo Socratic Hint sang AI Microservice bị quá hạn phản hồi (Timeout cấu hình mặc định là 10 giây) hoặc dịch vụ AI báo lỗi 500.
*   **Cơ chế tự phục hồi (Fallback Mechanism):**
    *   **FastAPI Backend** được trang bị bộ điều khiển **Fallback Engine** chạy bằng thuật toán toán học tĩnh (deterministic rules).
    *   Khi AI Microservice không phản hồi, Backend lập tức tự động chạy các công cụ tính toán nội bộ để tính toán điểm ELO, tìm concept yếu, chia nhóm học viên dựa theo dữ liệu thực tế và xuất ra kế hoạch hành động.
    *   Dữ liệu trả về Next.js sẽ được đóng gói bình thường kèm theo cờ `is_fallback_triggered = true`.
*   **Trải nghiệm Next.js UI:**
    *   Next.js nhận diện cờ `is_fallback_triggered = true` và hiển thị một thanh thông báo nhỏ màu vàng: *"Hệ thống đang hoạt động ở chế độ dự phòng. Các chỉ số phân nhóm học viên và concept yếu vẫn đảm bảo chính xác 100% dựa trên thuật toán ELO."*
    *   Phần tóm tắt phân tích bằng ngôn ngữ tự nhiên sẽ được thay thế bằng một chuỗi văn bản mẫu chuẩn sư phạm định sẵn tương ứng với các concept yếu tìm thấy.

---

## 3. Ghi nhận lỗi vào hệ thống Chỉ số Telemetry (Telemetry Error Logging)
Khi xảy ra sự cố trong lúc thực thi các công cụ (Tools), hệ thống bắt buộc phải ghi nhận chính xác trạng thái vào báo cáo `AgentTelemetryReport` để Mentor có thể theo dõi trực tiếp qua "Thought Process Console" trên Next.js UI:

### 3.1. Kịch bản lỗi Tool Calling bị Thất bại hoặc Timeout:
*   **Tình huống:** Một công cụ (ví dụ: `get_session_cohort_data`) chạy bị lỗi kết nối dữ liệu hoặc kéo dài quá 3 giây.
*   **Ghi nhận sự kiện:**
    *   Hệ thống bắt lỗi tại hàm thực thi công cụ.
    *   Cập nhật `ToolCallRecord` tương ứng: Gán trường `status = "failed"` hoặc `"timeout"`, lưu thông tin chi tiết lỗi vào `result_summary` để phục vụ debug, và lưu thời gian chạy thực tế tại `execution_time_ms`.
    *   Đồng thời ghi một dòng mô tả sự kiện lỗi vào mảng `thinking_logs` (ví dụ: *"[ERROR] Tool detect_learning_risks failed due to database connection issue. Triggering local recovery."*).

### 3.2. Kịch bản lỗi LLM Token Limit / API Rate Limit:
*   **Tình huống:** AI Microservice từ chối dịch vụ do vượt quá giới hạn token hoặc lượt gọi (Rate Limit).
*   **Ghi nhận sự kiện:**
    *   Hệ thống gán cờ `is_fallback_triggered = True` trong cấu trúc `TelemetryMetrics`.
    *   Thiết lập số lượng `total_tokens = 0` (do không tiêu tốn token thực tế từ AI).
    *   Thông báo lỗi được đẩy trực tiếp lên luồng sự kiện SSE để Next.js UI hiển thị thông tin cảnh báo tức thời.

---

## 4. Lỗi Định Dạng Dữ Liệu Đầu Vào (Data Integrity & Type Validation)
*   **Tình huống:** Dữ liệu học viên đồng bộ từ hệ thống LMS bị khuyết thiếu các trường điểm số hoặc thông tin nền tảng.
*   **Rào chắn Bảo vệ dữ liệu (Data Sanitization Guard):**
    *   Sử dụng thư viện xác thực cấu trúc đầu vào (**Pydantic** của FastAPI) để tự động kiểm tra kiểu dữ liệu khi nạp dữ liệu lớp học.
    *   **Nguyên tắc tự động sửa lỗi (Auto-Correction Rules):**
        *   Nếu thiếu trường điểm kiểm tra nhanh (`diagnostic_score`), hệ thống tự động kế thừa điểm số bài Lab (`lab_score`).
        *   Nếu điểm số thành thạo từng concept bị rỗng, gán giá trị mặc định là `50` (Mức độ hiểu trung bình) để tránh lỗi chia cho 0 hoặc lỗi giá trị rỗng (Null Pointer) khi chạy thuật toán phân nhóm.
        *   Nếu thiếu thông tin nền tảng (`background`), gán mặc định là `non-tech` để ưu tiên hỗ trợ khích lệ cao nhất.

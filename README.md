# 🎓 GapTutor ReAct Agent - Hệ thống Chẩn đoán Học tập

**GapTutor ReAct Agent** là hệ thống AI Agent hỗ trợ Giảng viên/Mentor chẩn đoán lỗ hổng kiến thức của học viên. Hệ thống sử dụng vòng lặp **ReAct (Reasoning and Acting)** để đưa ra các nhận định chính xác, có bằng chứng từ dữ liệu thực tế thay vì suy luận cảm tính hay giả lập kết quả.

---

## 🛠️ Công cụ Chẩn đoán (Tools)

Hệ thống được tích hợp các công cụ chuyên biệt để phân tích dữ liệu học tập:
*   **Truy xuất dữ liệu:**
    *   `get_sessions`: Lấy danh sách các buổi học hiện có trên hệ thống.
    *   `get_session_cohort_data`: Tải dữ liệu điểm số bài lab, điểm chẩn đoán và mức độ thành thạo của cả lớp học.
    *   `get_student_detail`: Truy vấn chi tiết thông tin học tập, phân tích rủi ro và gợi ý hành động cho từng học viên.
*   **Phân tích & Phân nhóm:**
    *   `analyze_concept_mastery`: Phân tích định lượng điểm thành thạo của lớp để lọc ra các khái niệm yếu (Mastery < 50%).
    *   `detect_learning_risks`: Phát hiện các học viên gặp rủi ro học tập theo 3 nhóm:
        *   *Hiểu giả tạo (`fake_understanding`):* Làm xong bài lab nhưng trả lời sai câu hỏi biến thể.
        *   *Nguy cơ âm thầm (`silent_at_risk`):* Ít hoạt động và điểm thành thạo trung bình < 50%.
        *   *Học vẹt làm lab (`lab_following_not_understanding`):* Điểm lab thực hành cao (> 80%) nhưng điểm thi chẩn đoán độc lập thấp (< 50%).
    *   `group_students`: Tự động phân chia học viên vào 3 nhóm năng lực thích ứng: *Needs Foundation*, *Needs Practice*, và *Ready for Advanced*.
    *   `generate_remediation_plan`: Đề xuất lộ trình khắc phục cụ thể theo từng nhóm năng lực học viên.

---

## 🤖 Hỗ trợ LLM Providers

Hệ thống hỗ trợ cấu hình chuyển đổi linh hoạt giữa các mô hình:
*   **Primary:** OpenAI `gpt-4o` (mạnh mẽ nhất, độ tin cậy cao nhất).
*   **Secondary:** Google Gemini `gemini-1.5-flash` (tối ưu chi phí và tốc độ).
*   **Tertiary (Offline):** Local LLM qua `llama-cpp` (chạy offline bằng file `.gguf` của `Phi-3-mini-4k` trên CPU).
*   **Testing:** MockProvider / FakeLLM phục vụ kiểm thử đơn vị tự động.

---

## 🛡️ Cơ chế Bảo vệ (Guardrails)

*   **Ngăn chặn Hallucination (Programmatic Guardrail):** Truncate (cắt ngắn) kết quả sinh của LLM tại thẻ `Observation:` nhằm ngăn chặn hoàn toàn việc mô hình tự bịa kết quả gọi công cụ. Hệ thống sẽ tự động thực thi công cụ thật và điền dữ liệu thực tế vào vòng lặp tiếp theo.
*   **Giới hạn số bước (Max Steps Loop):** Ràng buộc tối đa 5 vòng lặp ReAct để tránh hiện tượng lặp vô hạn và bùng nổ chi phí token.
*   **Phòng chống Prompt Injection (Regex Sanitizer):** Lọc các từ khóa độc hại (`ignore`, `bypass`, `system prompt`, `simulate`,...) tại backend. Trả về lỗi `400 Bad Request` lập tức mà không gửi request sang LLM.
*   **Bảo vệ mã nguồn (System Instruction Leakage Prevention):** Đóng gói prompt của người dùng tách biệt hoàn toàn với System Prompt và bổ sung chỉ thị nội tại cấm tiết lộ thông tin cấu hình.
*   **Cô lập dữ liệu (Cross-Cohort Isolation):** Middleware kiểm tra quyền sở hữu (RBAC) đối chiếu Mentor ID với `session_id`/`student_id` để ngăn rò rỉ dữ liệu giữa các lớp học (trả về lỗi `403 Forbidden`).

---

## 🚨 Xử lý Lỗi & Tự Phục hồi (Error Handling)

*   **Không tìm thấy buổi học (Session Mismatch):** Trả về mã lỗi `404 Not Found` kèm danh sách ID buổi học hợp lệ hiện có. Next.js UI sẽ tự kích hoạt lại bộ chọn buổi học để dẫn hướng Mentor.
*   **AI Timeout / Rate Limit (Fallback Engine):** Khi API AI bị ngắt kết nối hoặc quá thời gian phản hồi (10 giây), hệ thống tự động kích hoạt chế độ dự phòng cục bộ. Sử dụng các thuật toán ELO tĩnh để tính toán điểm số và hiển thị cảnh báo hoạt động dự phòng trên Next.js UI (kèm cờ `is_fallback_triggered = true`).
*   **Ghi vết sự cố (Telemetry Error Logging):** Lỗi tool calling hoặc lỗi giới hạn token sẽ được ghi lại chi tiết vào `AgentTelemetryReport` thông qua trạng thái `failed`/`timeout` để theo dõi tại console "Thought Process".
*   **Lỗi định dạng dữ liệu đầu vào (Data Sanitization Guard):** Xác thực kiểu dữ liệu bằng **Pydantic**. Tự động sửa lỗi dữ liệu khuyết thiếu:
    *   Điểm chẩn đoán thiếu -> Tự động lấy điểm bài Lab.
    *   Điểm mastery rỗng -> Gán mặc định `50`.
    *   Thông tin nền tảng thiếu -> Gán mặc định `non-tech` để đảm bảo hệ thống không bị crash.

---

## 🚀 Khởi chạy Nhanh

1.  **Cấu hình môi trường:**
    ```bash
    cp .env.example .env
    # Điền các API Key tương ứng
    ```
2.  **Cài đặt thư viện:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Khởi chạy Server:**
    ```bash
    PYTHONPATH=. python -m uvicorn api.main:app --reload
    ```

# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Hồ Tất Bảo Hoàng
- **Student ID**: 2A202600699
- **Date**: 2026/06/01

---

## I. Technical Contribution (15 Points)

Đóng góp chính của tôi bao gồm **thiết kế hệ thống đặc tả dữ liệu (Data Contracts)**, **phát triển API Backend/Frontend** và **tài liệu hóa kiến trúc** dự án:

- **Modules Implementated**:
  - **Data Contracts & Architecture**: Khởi tạo 4 file schema YAML tại thư mục `contracts/` định nghĩa cấu trúc dữ liệu học viên, đặc tả tham số gọi công cụ (tool calls), logs telemetry và mã lỗi. Viết tài liệu kỹ thuật tại `docs/data-schemas.md`.
  - **Frontend UI & Diagnostics**: Phát triển giao diện Next.js, khắc phục triệt để lỗi tràn layout chat bằng cách tối ưu CSS Flexbox (`h-full` constraint), đảm bảo giao diện cuộn mượt mà khi hiển thị luồng tư duy (`thinking_logs`), các tín hiệu telemetry và logs của AI Agent.
  - **FastAPI Backend API**: Thiết lập API Server bằng FastAPI (`src/api/main.py`), xây dựng các endpoints `/api/v1/diagnose` và `/health` tích hợp toàn bộ pipeline phân tích dữ liệu lớp học.
  - **Mock Model & Registry**: Hiện thực `MockProvider` mô phỏng LLM phản hồi, tính toán token/độ trễ và thiết lập bộ đăng ký cơ sở dữ liệu mẫu của học viên phục vụ kiểm thử cục bộ.

- **Code Highlights**:
  *Định nghĩa quy tắc phát hiện học vẹt (fake_understanding) tại [gaptutor-data-contract.yaml](file:///d:/CODE/AITHUCCHIEN/LABS/Day-3-Lab-Chatbot-vs-react-agent/contracts/gaptutor-data-contract.yaml#L46-L50):*
  ```yaml
  quality_rules:
    - id: "fake_understanding"
      description: "Cảnh báo nếu hoàn thành Lab nhưng làm sai câu hỏi biến thể"
      severity: "warn"
  ```
  *Luật chặn Prompt Injection tại [gaptutor-security-errors-contract.yaml](file:///d:/CODE/AITHUCCHIEN/LABS/Day-3-Lab-Chatbot-vs-react-agent/contracts/gaptutor-security-errors-contract.yaml#L31-L40):*
  ```yaml
  security_guardrails:
    query_blacklist:
      - "ignore"
      - "forget"
      - "system prompt"
  ```

- **Documentation**:
  - **Tránh lỗi parse của Agent**: Thiết kế cấu trúc `input_payload` trong `gaptutor-tools-contract.yaml` giúp ReAct Agent gọi đúng định dạng tham số của công cụ mà không bị lỗi logic.
  - **Khôi phục lỗi và bảo mật**: Thiết kế schema mã lỗi và guardrails giúp Backend lập tức chặn đứng Prompt Injection hoặc trả lỗi dự phòng (Fallback) khi ReAct loop gặp sự cố.
  - **Đồng bộ hóa render UI**: Định nghĩa JSON schema trong `docs/data-schemas.md` giúp Frontend Next.js render trực tiếp luồng tư duy (`thinking_logs`) và timeline gọi tool từ dữ liệu của Agent.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: [e.g., Agent caught in an infinite loop with `Action: search(None)`]
- **Log Source**: [Link or snippet from `logs/YYYY-MM-DD.log`]
- **Diagnosis**: [Why did the LLM do this? Was it the prompt, the model, or the tool spec?]
- **Solution**: [How did you fix it? (e.g., updated `Thought` examples in the system prompt)]

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: How did the `Thought` block help the agent compared to a direct Chatbot answer?
2.  **Reliability**: In which cases did the Agent actually perform *worse* than the Chatbot?
3.  **Observation**: How did the environment feedback (observations) influence the next steps?

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: [e.g., Use an asynchronous queue for tool calls]
- **Safety**: [e.g., Implement a 'Supervisor' LLM to audit the agent's actions]
- **Performance**: [e.g., Vector DB for tool retrieval in a many-tool system]

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.

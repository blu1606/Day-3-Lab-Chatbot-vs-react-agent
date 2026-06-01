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

Trong quá trình tích hợp và kiểm thử hệ thống API, tôi đã trực tiếp phân tích và xử lý một sự cố nghiêm trọng khiến ASGI Server (Uvicorn) sụp đổ hoàn toàn khi khởi động:

- **Problem Description**: Lỗi sụp đổ ứng dụng khi chạy chẩn đoán do gặp ngoại lệ `NameError: name 'Path' is not defined` và `NameError: name 'json' is not defined` bên trong module `src/tools/student_analysis_tools.py` khi cố gắng nạp tệp dữ liệu động `data/students.json`. Ngoài ra, hệ thống cũng gặp lỗi `ModuleNotFoundError: No module named 'src'` khi chạy server từ bên trong thư mục con `src/`.
- **Log Source**: Trích xuất log sụp đổ từ Uvicorn reloader trong terminal:
  ```text
  File "D:\CODE\AITHUCCHIEN\LABS\Day-3-Lab-Chatbot-vs-react-agent\src\tools\student_analysis_tools.py", line 16, in <module>
    DATA_STUDENTS_PATH = Path(__file__).resolve().parents[2] / "data" / "students.json"
  NameError: name 'Path' is not defined
  ```
- **Diagnosis**: 
  1. Thiếu sót thư viện: File template kéo về từ remote có sử dụng đối tượng `Path` (định vị file) và hàm `json.loads` (để phân tích JSON) nhưng lại bị thiếu các dòng import cơ bản `from pathlib import Path` và `import json` ở đầu file.
  2. Xung đột đường dẫn làm việc (CWD): Khi di chuyển vào thư mục con `src/` và chạy `uvicorn`, Python thêm `src/` vào `sys.path` dẫn đến cơ chế Import tuyệt đối `from src.core...` bị hiểu sai thành `src/src/...` (không tồn tại).
- **Solution**: 
  1. Tôi đã bổ sung các import cần thiết `import json` và `from pathlib import Path` vào đầu file `student_analysis_tools.py`.
  2. Hướng dẫn cấu hình lại môi trường chạy thông qua biến `PYTHONPATH` trỏ ra thư mục cha (ví dụ `PYTHONPATH=.. uv run uvicorn api.main:app --reload`), giúp Python nhận diện chính xác cấu trúc gói thư mục gốc của toàn dự án mà không cần sửa đổi bất cứ đường dẫn tương đối nào trong code.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

Từ các kết quả đo lường và theo dõi (telemetry) của buổi Lab, tôi rút ra được các nhận định sâu sắc về sự khác biệt giữa Chatbot truyền thống và ReAct Agent:

1.  **Reasoning (Khả năng lập luận)**: Khối `Thought` giúp ReAct Agent định hình rõ mục tiêu phụ (sub-goals) trước khi gọi các công cụ ngoài. Thay vì chỉ đưa ra câu trả lời dựa trên xác suất từ của một chatbot thông thường (dễ bị ảo tưởng), ReAct Agent áp dụng chuỗi logic "Suy nghĩ ➔ Hành động ➔ Quan sát" giúp câu trả lời cuối cùng được neo (grounded) trên các bằng chứng số liệu thực tế được truy xuất từ cơ sở dữ liệu.
2.  **Reliability (Độ tin cậy)**: ReAct Agent đôi khi hoạt động **kém hiệu quả hơn** Chatbot trong các tác vụ đơn giản vì quy trình suy luận vòng lặp của nó làm tăng đáng kể độ trễ (latency lên tới vài giây) và chi phí token sử dụng (token consumption). Ngoài ra, nếu LLM tạo ra câu lệnh gọi tool sai định dạng JSON hoặc lặp vô hạn, Agent sẽ thất bại hoàn toàn. Do đó, thiết lập cơ chế **Fallback** (trả lỗi dự phòng an toàn bằng thuật toán toán học tĩnh) là bắt buộc để đảm bảo tính ổn định trong sản xuất.
3.  **Observation (Ý nghĩa của phản hồi)**: Các phản hồi từ môi trường (Observations) đóng vai trò như bộ nhớ ngoài của Agent. Kết quả đầu ra của tool chẩn đoán trước (ví dụ cờ rủi ro quét được) sẽ lập tức tác động làm thay đổi tham số đầu vào của tool tiếp theo (ví dụ phân làn học tập và lên kế hoạch khắc phục), tạo ra một chuỗi thực thi thích ứng cực kỳ linh hoạt mà Chatbot tĩnh không thể làm được.

---

## IV. Future Improvements (5 Points)

Để mở rộng hệ thống AI Agent này lên cấp độ sản xuất (Production-ready) phục vụ hàng ngàn học viên, tôi đề xuất các hướng cải tiến sau:

- **Scalability (Khả năng mở rộng)**: Chuyển đổi mô hình gọi tool đồng bộ của uvicorn hiện tại sang hàng đợi tác vụ bất đồng bộ (Asynchronous Task Queue) sử dụng **Celery** và **Redis**. Các tác vụ chạy ReAct Agent tốn nhiều thời gian suy luận sẽ được đẩy xuống background workers xử lý để tránh chặn (block) luồng xử lý Web chính.
- **Safety (Tính an toàn)**: Triển khai một **Supervisor Agent** (Agent Giám sát) hoặc tích hợp các framework guardrail (như Llama Guard) đứng trước cổng API. Nhiệm vụ của nó là lọc và ngăn chặn hoàn toàn các dạng Prompt Injection (như câu lệnh "ignore previous instructions") trước khi đưa vào luồng lập luận của Agent chính.
- **Performance (Tối ưu hiệu năng)**: Tích hợp cơ sở dữ liệu Vector (như **ChromaDB** hoặc **Milvus**) để thực hiện kỹ thuật **Semantic Tool Retrieval**. Khi số lượng tools tăng lên hàng trăm, thay vì đưa toàn bộ mô tả tool vào System Prompt (gây tốn token và loãng ngữ cảnh), chúng ta sẽ chỉ truy xuất động các tools có độ tương đồng ngữ nghĩa cao nhất với câu hỏi học viên.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.

# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Vũ Trọng
- **Student ID**: 2A202600960
- **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- Tạo mock datas.
- Viết cohort_diagnostic_tools.py
- Viết test_cohort_tools

- **Modules Implementated**: src\tools\cohort_diagnostic_tools.py
- **Code Highlights**: cài đặt các hàm phân tích mastery theo concept, trả về danh sách `weak_concepts` và hỗ trợ truy vấn session bằng `get_session_cohort_data(session_id)`.
- **Documentation**: Các hàm trong `cohort_diagnostic_tools` được thiết kế để là công cụ (tool) gọi bởi ReAct Agent — trả về dữ liệu JSON đơn giản, hạn chế side-effect, dễ serialize cho agent.


---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: ReAct Agent gặp lỗi khi phân tích các tool call với tham số không đúng format JSON hoặc thiếu tên hàm. Cụ thể, khi agent sinh ra `Action: get_diagnosis_snapshot({"extra_key": "value"})`, hàm không nhận được kwargs mong đợi, dẫn đến `Observation: Tool get_diagnosis_snapshot not found` mặc dù tool tồn tại.

- **Log Source**: Lỗi được ghi trong telemetry event `DIAGNOSE_PROVIDER_RUNTIME_ERROR` khi agent chạy, với stack trace chỉ ra lỗi parsing trong `ReActAgent.run()` — regex pattern `r'Action: (\w+)\((.*)\)'` không match chính xác các tool call có structure phức tạp.

- **Diagnosis**: LLM (đặc biệt là model nhỏ như Phi-3) không hiểu rõ format mong đợi `Action: tool_name({json_params})`, dẫn đến sinh ra JSON không hợp lệ hoặc dấu ngoặc không cân bằng. Ngoài ra, `get_diagnosis_snapshot()` không có tham số, nhưng agent lại cố gắng truyền keyword arguments.

- **Solution**: 
  1. Cải thiện prompt: Thêm ví dụ cụ thể vào `agent_prompt` trong `src/api/main.py` để minh họa đúng format: `Action: tool_name()` hoặc `Action: tool_name({"param": "value"})`.
  2. Robust parsing: Cải thiện regex và bổ sung try-catch trong `ReActAgent._parse_action()` để xử lý JSON không hợp lệ gracefully, trả về observation: `"Tool call format invalid. Please use Action: name(params)"`.
  3. Tool schema validation: Thêm trường `required_params` vào tool definition để agent biết tool nào có tham số, tool nào không.
  4. Test: Thêm unit test `test_react_agent_handles_malformed_action()` trong `tests/test_react_agent.py` để kiểm tra các trường hợp parsing sai.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: How did the `Thought` block help the agent compared to a direct Chatbot answer?

- Khối Thought giúp Agent phân tích vấn đề và lập kế hoạch trước khi đưa ra câu trả lời. Thay vì trả lời ngay như Chatbot thông thường, Agent có thể xác định cần tìm kiếm thông tin nào, sử dụng công cụ nào và thực hiện các bước cần thiết trước khi kết luận. Điều này giúp câu trả lời có cơ sở hơn và giảm nguy cơ trả lời sai do suy đoán.

2.  **Reliability**: In which cases did the Agent actually perform *worse* than the Chatbot?

- Agent có thể hoạt động kém hơn Chatbot trong một số trường hợp như công cụ gặp lỗi, dữ liệu truy xuất không chính xác hoặc quá trình suy luận quá phức tạp đối với những câu hỏi đơn giản. Ngoài ra, việc phụ thuộc vào nhiều bước xử lý khiến Agent tốn nhiều thời gian và tài nguyên hơn, đôi khi dẫn đến kết quả không ổn định bằng Chatbot trực tiếp.

3.  **Observation**: How did the environment feedback (observations) influence the next steps?

- Các Observation đóng vai trò là phản hồi từ môi trường sau mỗi hành động của Agent. Dựa trên những thông tin này, Agent có thể điều chỉnh kế hoạch, lựa chọn hành động tiếp theo hoặc thay đổi hướng tiếp cận nếu kết quả chưa phù hợp. Nhờ đó, Agent có khả năng thích nghi tốt hơn và đưa ra quyết định dựa trên dữ liệu thực tế thay vì chỉ dựa vào suy luận ban đầu.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: 
  - Chuyển từ mô hình đồng bộ (synchronous blocking) sang Celery + Redis cho các tác vụ agent chạy lâu. Agent reasoning có latency cao (3–10 giây/step), nên đẩy xuống background worker pool sẽ giải phóng Web thread.
  - Sử dụng PostgreSQL + pgvector thay vì in-memory data để lưu trữ session cohort data, cho phép horizontal scaling với nhiều API instances.
  - Thêm request queuing và rate limiting (với Redis) để xử lý spike traffic khi nhiều mentor dùng agent cùng lúc.

- **Safety**: 
  - Thêm Supervisor LLM — một agent thứ hai kiểm tra output của agent chính trước khi trả về user, đặc biệt là các claim về sinh viên (để tránh hallucinogenic student names).
  - Mở rộng prompt injection guardrails: hiện tại chỉ kiểm tra keyword, nên thêm semantic classifier (small BERT) để phát hiện jailbreak attempts tinh vi.
  - Logging chi tiết: ghi lại toàn bộ agent history, tool calls, LLM responses vào immutable audit log (e.g., AWS S3) để có thể trace lại quyết định nếu có sai sót.
  - Token budget enforcement: Đặt hard limit trên tokens/session để tránh cost explosion khi agent lặp vô hạn.

- **Performance**: 
  - Caching tool results: Nếu `get_diagnosis_snapshot()` được gọi nhiều lần trong cùng session, cache kết quả trong Redis (TTL 5 phút) thay vì tính toán lại.
  - Vector embeddings for tool retrieval: Khi số tools tăng > 10–20, dùng embedding (OpenAI ada) + FAISS để tìm tool phù hợp nhất dựa trên intent, thay vì hardcode list.
  - Giảm `max_steps` mặc định từ 3 → 2 hoặc sử dụng early stopping (nếu độ tin cậy observation > threshold, dừng sớm).
  - Batch processing: Nếu mentor gửi hàng chục query cùng lúc, group chúng lại và chạy parallel agents với shared cohort context.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.

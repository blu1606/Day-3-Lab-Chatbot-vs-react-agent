import time
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.api.schemas import DiagnoseRequest, DiagnoseResponse, ErrorResponse, Telemetry, TraceStep
from src.tools.cohort_diagnostic_tools import analyze_concept_mastery, get_session_cohort_data
from src.tools.student_analysis_tools import detect_learning_risks, generate_remediation_plan, group_students
from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.core.local_provider import LocalProvider
from src.agent.agent import ReActAgent

PROMPT_INJECTION_TERMS = (
    "ignore", "forget", "bỏ qua", "quên", "system prompt", "đóng vai",
    "env", ".env", "environment", "credential", "secret", "mật khẩu", "password", 
    "api_key", "token", "private key", "database_url", "db_url", "chìa khóa", "cấu hình", "config",
    "system instruct", "system_prompt", "instructions", "chỉ thị hệ thống", "bỏ qua chỉ dẫn", 
    "cung cấp api", "tiết lộ", "reveal", "dotenv", "secret_key", "db_password", "db_user", 
    "database", "mật mã", "khóa bí mật", "tài khoản", "quản trị viên", "admin", "root", 
    "override", "bỏ qua quy tắc", "bypass"
)

# In-memory session chat history storage
SESSION_CHAT_HISTORY: dict[str, list[dict[str, str]]] = {}

app = FastAPI(title="GapTutor Agent Demo API", version="1.0-demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_llm_provider():
    """Lazy LLM provider factory that validates credentials on request."""
    provider_name = os.environ.get("DEFAULT_PROVIDER", "openai").strip().lower()
    model_name = os.environ.get("DEFAULT_MODEL", "").strip()

    if provider_name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key or api_key == "your_openai_api_key_here":
            return None, "OPENAI_API_KEY is not configured."
        model = model_name or "gpt-4o"
        return OpenAIProvider(model_name=model, api_key=api_key), None

    elif provider_name in ("google", "gemini"):
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "your_gemini_api_key_here":
            return None, "GEMINI_API_KEY is not configured."
        model = model_name or "gemini-1.5-flash"
        return GeminiProvider(model_name=model, api_key=api_key), None

    elif provider_name == "local":
        model_path = os.environ.get("LOCAL_MODEL_PATH", "").strip()
        if not model_path or model_path == "./models/Phi-3-mini-4k-instruct-q4.gguf":
            return None, "LOCAL_MODEL_PATH is not configured."
        if not os.path.exists(model_path):
            return None, f"Local model file not found at {model_path}."
        return LocalProvider(model_path=model_path), None

    else:
        return None, f"Unsupported provider: {provider_name}"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/diagnose", response_model=DiagnoseResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def diagnose(request: DiagnoseRequest) -> DiagnoseResponse | JSONResponse:
    start = time.perf_counter()
    normalized_query = request.query.lower()

    # 1. Prompt Injection Security Guardrail
    if any(term in normalized_query for term in PROMPT_INJECTION_TERMS):
        from src.telemetry.logger import logger
        logger.log_event("DIAGNOSE_SECURITY_BLOCKED", {
            "query": request.query,
            "session_id": request.session_id,
            "error_code": "PROMPT_INJECTION_DETECTED"
        })
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "PROMPT_INJECTION_DETECTED",
                "message": "Yêu cầu bị từ chối: Phát hiện dấu hiệu chèn câu lệnh (Prompt Injection) không an toàn.",
            },
        )

    # 2. Provider Lazy Initialization and Configuration Check
    provider, config_error = get_llm_provider()
    if not provider:
        from src.telemetry.logger import logger
        logger.log_event("DIAGNOSE_PROVIDER_UNCONFIGURED", {
            "session_id": request.session_id,
            "error_code": "AI_PROVIDER_NOT_CONFIGURED",
            "details": config_error
        })
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "AI_PROVIDER_NOT_CONFIGURED",
                "message": "Real AI provider is not configured. Set OPENAI_API_KEY or configure DEFAULT_PROVIDER."
            }
        )

    task_id = f"diag-{uuid4().hex[:10]}"
    is_fallback = "timeout" in normalized_query or "slow" in normalized_query

    # Check if the query is a general conversation vs. a diagnostic query
    DIAGNOSTIC_KEYWORDS = (
        "chẩn đoán", "diagnose", "cohort", "lớp", "học viên", "học sinh", "student", 
        "nhóm", "yếu", "kém", "rủi ro", "risk", "remediation", "khắc phục", "báo cáo", "report",
        "s1", "s2", "s3", "stu", "tổng quan", "phân tích", "công cụ", "tool", "tools"
    )
    is_diagnostic_query = any(keyword in normalized_query for keyword in DIAGNOSTIC_KEYWORDS)

    # 2.1 Fast-route for General Conversation (Bypasses cohort pipeline and agent loop)
    if not is_diagnostic_query:
        try:
            # Format chat history from RAM
            chat_history_str = ""
            if request.session_id in SESSION_CHAT_HISTORY and SESSION_CHAT_HISTORY[request.session_id]:
                chat_history_str = "Lịch sử trò chuyện trước đó:\n"
                for msg in SESSION_CHAT_HISTORY[request.session_id]:
                    role_name = "Mentor" if msg["role"] == "user" else "Trợ lý"
                    chat_history_str += f"- {role_name}: {msg['content']}\n"
                chat_history_str += "\n"

            system_instruction = (
                "Bạn là GapTutor Agent, trợ lý chẩn đoán học tập cho mentor. "
                "Người dùng đang chào hỏi hoặc trò chuyện xã giao. Hãy phản hồi một cách tự nhiên, "
                "thân thiện bằng tiếng Việt và gợi ý rằng họ có thể yêu cầu chẩn đoán học tập lớp học hoặc học viên."
            )
            fast_prompt = f"{chat_history_str}Mentor: {request.query}"
            result = provider.generate(fast_prompt, system_prompt=system_instruction)
            summary = result.get("content", "")
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_ai_latency_ms = result.get("latency_ms", 0)
        except Exception as e:
            from src.telemetry.logger import logger
            logger.log_event("DIAGNOSE_GENERAL_CHAT_ERROR", {"error": str(e)})
            summary = "Xin chào! Hiện tại tôi đang gặp sự cố kết nối AI. Tôi có thể hỗ trợ chẩn đoán lớp học nếu bạn cung cấp từ khóa chẩn đoán."
            prompt_tokens = 0
            completion_tokens = 0
            total_ai_latency_ms = 0

        # Save to RAM chat history
        if request.session_id not in SESSION_CHAT_HISTORY:
            SESSION_CHAT_HISTORY[request.session_id] = []
        SESSION_CHAT_HISTORY[request.session_id].append({"role": "user", "content": request.query})
        SESSION_CHAT_HISTORY[request.session_id].append({"role": "assistant", "content": summary})

        total_execution_time_ms = max(1, round((time.perf_counter() - start) * 1000))

        steps = [
            TraceStep(
                id="diag-thought-guardrail",
                title="Guardrail scan",
                kind="thought",
                content="Query hợp lệ, chuyển tiếp sang luồng hội thoại chung.",
            ),
            TraceStep(
                id="diag-final",
                title="Final Answer",
                kind="final",
                content=summary,
            )
        ]

        thinking_logs = [
            "Nhận truy vấn mentor và kiểm tra guardrail.",
            "Phát hiện đây là cuộc hội thoại xã giao. Chuyển tiếp sang luồng phản hồi trực tiếp từ LLM.",
            "Tổng hợp phản hồi xã giao thân thiện bằng tiếng Việt."
        ]

        response = DiagnoseResponse(
            task_id=task_id,
            session_id=request.session_id,
            summary=summary,
            student_groups=[],
            remediation_plan=[],
            telemetry=Telemetry(
                task_id=task_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                total_execution_time_ms=total_execution_time_ms,
                is_fallback_triggered=False,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                thinking_logs=thinking_logs,
              ),
              steps=steps,
        )

        from src.telemetry.logger import logger
        from src.telemetry.metrics import tracker
        tracker.track_request(
            provider=os.environ.get("DEFAULT_PROVIDER", "openai").strip().lower(),
            model=provider.model_name,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            latency_ms=total_execution_time_ms
        )
        logger.log_event("DIAGNOSE_SUCCESS", {
            "task_id": task_id,
            "session_id": request.session_id,
            "is_fallback": False,
            "steps_count": len(steps),
            "summary": summary
        })
        return response

    # 3. Retrieve Cohort Data
    try:
        cohort = get_session_cohort_data(request.session_id)
    except ValueError as error:
        if str(error).startswith("SESSION_NOT_FOUND"):
            return JSONResponse(
                status_code=404,
                content={
                    "error_code": "SESSION_NOT_FOUND",
                    "message": "Không tìm thấy thông tin buổi học được chọn. Vui lòng chọn lại.",
                },
            )
        raise

    # Robust fix for skeleton bug: inject 'concepts' into cohort if missing
    if "concepts" not in cohort:
        from src.tools.cohort_diagnostic_tools import get_sessions
        sessions = get_sessions()
        session_info = next((s for s in sessions if s["session_id"].lower() == request.session_id.lower()), None)
        cohort["concepts"] = session_info["concepts"] if session_info else ["prompting", "tool_use", "evaluation"]

    # 4. Standard Quantitative Pipeline
    students = cohort["students"]
    weak_concepts = analyze_concept_mastery(students, cohort["concepts"])
    risk_flags = detect_learning_risks(students)
    student_groups = group_students(students, risk_flags)
    remediation_plan = generate_remediation_plan(student_groups, weak_concepts)

    # 5. Define API-local ReAct Tools
    import json
    from src.tools.cohort_diagnostic_tools import get_sessions
    from src.tools.student_analysis_tools import get_student_detail

    def get_sessions_tool(*args, **kwargs) -> str:
        """Lấy danh sách mã và tiêu đề các buổi học đang lưu trên hệ thống."""
        warning = ""
        if args or kwargs:
            warning = "Cảnh báo: Bạn đã truyền thừa hoặc sai tham số cho get_sessions (công cụ này không yêu cầu tham số). Đang tự động trả về toàn bộ danh sách lớp học để hỗ trợ.\n\n"
        return warning + json.dumps(get_sessions(), ensure_ascii=False, indent=2)

    def get_session_cohort_data_tool(session_id: str = None, *args, **kwargs) -> str:
        """Lấy toàn bộ dữ liệu học lực, hành vi và điểm số của cả lớp trong buổi học chỉ định (session_id)."""
        if not session_id or session_id in ("Ellipsis", "null", "None", ""):
            all_sessions = get_sessions()
            return (
                "Lỗi: Bạn đã truyền thiếu hoặc sai tham số 'session_id'. "
                "Công cụ này yêu cầu truyền session_id hợp lệ (ví dụ: 'session-03' hoặc 'SESSION-RAG-20260601').\n"
                "Danh sách các session_id hiện có trên hệ thống:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )
        try:
            res = get_session_cohort_data(session_id)
            return json.dumps(res, ensure_ascii=False, indent=2)
        except Exception as e:
            all_sessions = get_sessions()
            return (
                f"Lỗi: Không tìm thấy session '{session_id}'. {str(e)}\n"
                "Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )

    def analyze_concept_mastery_tool(session_id: str = None, *args, **kwargs) -> str:
        """Phân tích định lượng điểm thành thạo của lớp để lọc ra những khái niệm học viên hiểu kém nhất trong buổi học chỉ định (session_id)."""
        if not session_id or session_id in ("Ellipsis", "null", "None", ""):
            all_sessions = get_sessions()
            return (
                "Lỗi: Bạn đã truyền thiếu hoặc sai tham số 'session_id'. "
                "Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )
        try:
            cohort = get_session_cohort_data(session_id)
            res = analyze_concept_mastery(cohort["students"], cohort.get("concepts", ["prompting", "tool_use", "evaluation"]))
            return json.dumps(res, ensure_ascii=False, indent=2)
        except Exception as e:
            all_sessions = get_sessions()
            return (
                f"Lỗi: {str(e)}. Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )

    def detect_learning_risks_tool(session_id: str = None, *args, **kwargs) -> str:
        """Quét cơ sở dữ liệu học tập của học viên để tự động phát hiện các biểu hiện rủi ro học thuật trong buổi học chỉ định (session_id)."""
        if not session_id or session_id in ("Ellipsis", "null", "None", ""):
            all_sessions = get_sessions()
            return (
                "Lỗi: Bạn đã truyền thiếu hoặc sai tham số 'session_id'. "
                "Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )
        try:
            cohort = get_session_cohort_data(session_id)
            res = detect_learning_risks(cohort["students"])
            return json.dumps(res, ensure_ascii=False, indent=2)
        except Exception as e:
            all_sessions = get_sessions()
            return (
                f"Lỗi: {str(e)}. Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )

    def group_students_tool(session_id: str = None, *args, **kwargs) -> str:
        """Tự động phân chia học viên vào 3 làn học tập dựa trên năng lực và cờ rủi ro đã phát hiện trong buổi học chỉ định (session_id)."""
        if not session_id or session_id in ("Ellipsis", "null", "None", ""):
            all_sessions = get_sessions()
            return (
                "Lỗi: Bạn đã truyền thiếu hoặc sai tham số 'session_id'. "
                "Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )
        try:
            cohort = get_session_cohort_data(session_id)
            risks = detect_learning_risks(cohort["students"])
            res = group_students(cohort["students"], risks)
            return json.dumps(res, ensure_ascii=False, indent=2)
        except Exception as e:
            all_sessions = get_sessions()
            return (
                f"Lỗi: {str(e)}. Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )

    def generate_remediation_plan_tool(session_id: str = None, *args, **kwargs) -> str:
        """Đề xuất các hành động khắc phục cụ thể theo từng nhóm năng lực trong buổi học chỉ định (session_id)."""
        if not session_id or session_id in ("Ellipsis", "null", "None", ""):
            all_sessions = get_sessions()
            return (
                "Lỗi: Bạn đã truyền thiếu hoặc sai tham số 'session_id'. "
                "Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )
        try:
            cohort = get_session_cohort_data(session_id)
            risks = detect_learning_risks(cohort["students"])
            groups = group_students(cohort["students"], risks)
            weak_concepts = analyze_concept_mastery(cohort["students"], cohort.get("concepts", ["prompting", "tool_use", "evaluation"]))
            res = generate_remediation_plan(groups, weak_concepts)
            return json.dumps(res, ensure_ascii=False, indent=2)
        except Exception as e:
            all_sessions = get_sessions()
            return (
                f"Lỗi: {str(e)}. Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )

    def get_student_detail_tool(student_id: str = None, session_id: str = None, *args, **kwargs) -> str:
        """Truy vấn sâu thông tin của một học viên cụ thể bằng student_id (ví dụ: 's1', 's2') trong buổi học chỉ định (session_id)."""
        if not student_id or not session_id or student_id in ("Ellipsis", "null", "") or session_id in ("Ellipsis", "null", ""):
            all_sessions = get_sessions()
            return (
                "Lỗi: Bạn đã truyền thiếu hoặc sai tham số 'student_id' hoặc 'session_id'. "
                "Công cụ này yêu cầu cả student_id và session_id hợp lệ.\n"
                "Danh sách các session_id hiện có:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )
        try:
            res = get_student_detail(student_id, session_id)
            return json.dumps(res, ensure_ascii=False, indent=2)
        except Exception as e:
            all_sessions = get_sessions()
            return (
                f"Lỗi: {str(e)}. Hãy chắc chắn bạn đã truyền đúng student_id (ví dụ 's1') và session_id.\n"
                "Danh sách các session_id hiện có:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )

    def list_students_tool(session_id: str = None, *args, **kwargs) -> str:
        """Lấy danh sách tất cả học viên (student_id và name) trong lớp học của buổi học chỉ định (session_id)."""
        if not session_id or session_id in ("Ellipsis", "null", "None", ""):
            all_sessions = get_sessions()
            return (
                "Lỗi: Bạn đã truyền thiếu hoặc sai tham số 'session_id'. "
                "Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )
        try:
            cohort = get_session_cohort_data(session_id)
            student_list = [
                {
                    "student_id": s["student_id"],
                    "name": s["name"],
                    "background": s.get("background", "non-tech")
                } for s in cohort["students"]
            ]
            return json.dumps(student_list, ensure_ascii=False, indent=2)
        except Exception as e:
            all_sessions = get_sessions()
            return (
                f"Lỗi: {str(e)}. Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )

    def get_diagnosis_snapshot_tool(session_id: str = None, *args, **kwargs) -> str:
        """Lấy tóm tắt chẩn đoán cả lớp bao gồm concept yếu, cờ rủi ro, phân nhóm học viên và kế hoạch hành động khắc phục trong buổi học chỉ định (session_id)."""
        if not session_id or session_id in ("Ellipsis", "null", "None", ""):
            all_sessions = get_sessions()
            return (
                "Lỗi: Bạn đã truyền thiếu hoặc sai tham số 'session_id'. "
                "Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )
        try:
            cohort = get_session_cohort_data(session_id)
            weak_concepts_snapshot = analyze_concept_mastery(cohort["students"], cohort.get("concepts", ["prompting", "tool_use", "evaluation"]))
            risk_flags_snapshot = detect_learning_risks(cohort["students"])
            student_groups_snapshot = group_students(cohort["students"], risk_flags_snapshot)
            remediation_plan_snapshot = generate_remediation_plan(student_groups_snapshot, weak_concepts_snapshot)
            snapshot = {
                "weak_concepts": weak_concepts_snapshot,
                "risk_flags": risk_flags_snapshot,
                "student_groups": [
                    {
                        "group_name": g["group_name"],
                        "reason": g["reason"],
                        "students": [s["name"] for s in g["students"]],
                        "weak_concepts": g["weak_concepts"]
                    } for g in student_groups_snapshot
                ],
                "remediation_plan": remediation_plan_snapshot
            }
            return json.dumps(snapshot, ensure_ascii=False, indent=2)
        except Exception as e:
            all_sessions = get_sessions()
            return (
                f"Lỗi: {str(e)}. Hãy chọn một trong các session_id hợp lệ sau:\n" +
                json.dumps(all_sessions, ensure_ascii=False, indent=2)
            )

    def list_tools_tool(**kwargs) -> str:
        """Lấy danh sách tất cả các công cụ mà trợ lý AI đang sở hữu và có thể gọi."""
        available_tools = [
            {"name": "get_sessions", "description": "Lấy danh sách mã và tiêu đề các buổi học đang lưu trên hệ thống."},
            {"name": "get_session_cohort_data", "description": "Lấy toàn bộ dữ liệu học lực, hành vi và điểm số của cả lớp trong buổi học chỉ định (session_id)."},
            {"name": "analyze_concept_mastery", "description": "Phân tích định lượng điểm thành thạo của lớp để lọc ra những khái niệm học viên hiểu kém nhất trong buổi học chỉ định (session_id)."},
            {"name": "detect_learning_risks", "description": "Quét cơ sở dữ liệu học tập của học viên để tự động phát hiện các biểu hiện rủi ro học thuật trong buổi học chỉ định (session_id)."},
            {"name": "group_students", "description": "Tự động phân chia học viên vào 3 làn học tập dựa trên năng lực và cờ rủi ro đã phát hiện trong buổi học chỉ định (session_id)."},
            {"name": "generate_remediation_plan", "description": "Đề xuất các hành động khắc phục cụ thể theo từng nhóm năng lực trong buổi học chỉ định (session_id)."},
            {"name": "get_student_detail", "description": "Truy vấn sâu thông tin của một học viên cụ thể bằng student_id (ví dụ: 's1', 's2') trong buổi học chỉ định (session_id)."},
            {"name": "list_students", "description": "Lấy danh sách tất cả học viên (student_id và name) trong lớp học của buổi học chỉ định (session_id)."},
            {"name": "get_diagnosis_snapshot", "description": "Lấy tóm tắt chẩn đoán cả lớp bao gồm concept yếu, cờ rủi ro, phân nhóm học viên và kế hoạch hành động khắc phục trong buổi học chỉ định (session_id)."},
            {"name": "list_tools", "description": "Lấy danh sách tất cả các công cụ mà trợ lý AI đang sở hữu và có thể gọi."}
        ]
        return json.dumps(available_tools, ensure_ascii=False, indent=2)

    tools = [
        {"name": "get_sessions", "description": "Get the list of all learning session IDs and titles stored on the system.", "func": get_sessions_tool},
        {"name": "get_session_cohort_data", "description": "Get full cohort details, learning behavior, and scores for a specific session_id.", "func": get_session_cohort_data_tool},
        {"name": "analyze_concept_mastery", "description": "Analyze class concept mastery to identify weakest concepts for a specific session_id.", "func": analyze_concept_mastery_tool},
        {"name": "detect_learning_risks", "description": "Scan learning logs to auto-detect student academic risk flags for a specific session_id.", "func": detect_learning_risks_tool},
        {"name": "group_students", "description": "Group students into 3 learning paths (Needs Foundation, Needs Practice, Ready for Advanced) for a specific session_id.", "func": group_students_tool},
        {"name": "generate_remediation_plan", "description": "Generate dynamic remediation action steps for each student group for a specific session_id.", "func": generate_remediation_plan_tool},
        {"name": "get_student_detail", "description": "Get deep learning profiles, metrics, risk evidence, and next actions for a specific student_id and session_id.", "func": get_student_detail_tool},
        {"name": "list_students", "description": "Get the names, backgrounds, and IDs of all students in the class for a specific session_id.", "func": list_students_tool},
        {"name": "get_diagnosis_snapshot", "description": "Get class quantitative diagnostic snapshot (weak concepts, risk flags, student groups, remediation plan) for a specific session_id.", "func": get_diagnosis_snapshot_tool},
        {"name": "list_tools", "description": "List all available diagnostic tools and descriptions that the AI agent has access to.", "func": list_tools_tool}
    ]

    # 6. Initialize ReAct Agent
    agent = ReActAgent(llm=provider, tools=tools, max_steps=5)
    
    # Format chat history from RAM
    chat_history_str = ""
    if request.session_id in SESSION_CHAT_HISTORY and SESSION_CHAT_HISTORY[request.session_id]:
        chat_history_str = "Lịch sử trò chuyện trước đó giữa bạn (GapTutor Agent) và Mentor:\n"
        for msg in SESSION_CHAT_HISTORY[request.session_id]:
            role_name = "Mentor" if msg["role"] == "user" else "GapTutor Agent"
            chat_history_str += f"- {role_name}: {msg['content']}\n"
        chat_history_str += "\n"

    agent_prompt = (
        f"Bạn là GapTutor Agent, trợ lý chẩn đoán học tập cho mentor.\n"
        f"Hãy trả lời yêu cầu sau của mentor bằng tiếng Việt. Bạn bắt buộc phải sử dụng công cụ "
        f"để thu thập dữ liệu học viên thực tế trước khi đưa ra nhận định chẩn đoán. Tuyệt đối không tự "
        f"bịa ra thông tin học viên không tồn tại trong dữ liệu hệ thống.\n"
        f"Bạn có toàn quyền sử dụng 10 công cụ từ đơn lẻ đến tổng hợp sau đây để thu thập dữ liệu: "
        f"get_sessions, get_session_cohort_data, analyze_concept_mastery, detect_learning_risks, "
        f"group_students, generate_remediation_plan, get_student_detail, list_students, get_diagnosis_snapshot, list_tools.\n"
        f"Mỗi chẩn đoán cần rõ ràng theo cấu trúc: Nhận định (Claim) -> Bằng chứng từ công cụ (Evidence) -> Khuyến nghị hành động (Recommendation).\n"
        f"Lưu ý: Không tự ý thay đổi cấu trúc phân nhóm học viên hoặc kế hoạch remediation đã tính toán tự động.\n\n"
        f"{chat_history_str}"
        f"Mentor query hiện tại: {request.query}"
    )

    # 7. Execute AI Provider with Fallback Strategy
    summary = ""
    is_fallback_triggered = is_fallback
    fallback_reason = None

    if is_fallback:
        summary = build_summary("Hệ thống đang hoạt động ở chế độ dự phòng bằng thuật toán toán học tĩnh.", weak_concepts, risk_flags, True)
    else:
        try:
            summary = agent.run(agent_prompt)
        except Exception as e:
            is_fallback_triggered = True
            fallback_reason = str(e)
            from src.telemetry.logger import logger
            logger.log_event("DIAGNOSE_PROVIDER_RUNTIME_ERROR", {
                "session_id": request.session_id,
                "error": fallback_reason
            })
            # Premium Dynamic Fallback Summary incorporating real computed data
            weakest_concept = weak_concepts[0]['concept'] if weak_concepts else "N/A"
            weakest_mastery = weak_concepts[0]['average_mastery'] if weak_concepts else 0
            summary = (
                "Hệ thống đang hoạt động ở chế độ dự phòng do lỗi kết nối AI. "
                f"Dữ liệu phân tích tĩnh cho thấy concept yếu nhất lớp là '{weakest_concept}' "
                f"với mức độ thành thạo trung bình {weakest_mastery}%. "
                f"Có {len(risk_flags)} học viên đang có cờ cảnh báo rủi ro học tập."
            )

    # Save to RAM chat history on success
    if request.session_id not in SESSION_CHAT_HISTORY:
        SESSION_CHAT_HISTORY[request.session_id] = []
    SESSION_CHAT_HISTORY[request.session_id].append({"role": "user", "content": request.query})
    SESSION_CHAT_HISTORY[request.session_id].append({"role": "assistant", "content": summary})

    # 8. Token and Latency Telemetry Aggregation
    prompt_tokens = 0
    completion_tokens = 0
    total_ai_latency_ms = 0

    for item in agent.history:
        usage = item.get("usage", {})
        prompt_tokens += usage.get("prompt_tokens", 0)
        completion_tokens += usage.get("completion_tokens", 0)
        total_ai_latency_ms += item.get("latency_ms", 0)

    total_execution_time_ms = max(1, round((time.perf_counter() - start) * 1000))

    # 9. Update Thinking Logs
    thinking_logs = [
        "Nhận truy vấn mentor và kiểm tra guardrail.",
        "Tải dữ liệu cohort theo session_id.",
        "Phân tích concept yếu, risk flags và phân nhóm học viên.",
    ]
    if is_fallback_triggered:
        if fallback_reason:
            thinking_logs.append(f"Gặp sự cố kết nối với AI provider ({fallback_reason}). Đang kích hoạt chế độ dự phòng.")
        else:
            thinking_logs.append("Kích hoạt chế độ dự phòng bằng thuật toán tĩnh theo yêu cầu.")
    else:
        thinking_logs.append(f"Chạy agent ReAct thông qua AI Provider '{provider.model_name}'.")
        thinking_logs.append(f"Agent thực hiện {len(agent.history)} bước lập luận ReAct và gọi các công cụ chẩn đoán cục bộ.")
        thinking_logs.append("Tổng hợp kết quả chẩn đoán cuối cùng bằng tiếng Việt.")

    # 10. Build Trace Steps for Frontend Trace Rail
    steps = [
        TraceStep(
            id="diag-thought-guardrail",
            title="Guardrail scan",
            kind="thought",
            content="Query hợp lệ, tiếp tục chạy pipeline chẩn đoán theo contract.",
        ),
    ]

    # Add step-by-step ReAct agent loops
    for h in agent.history:
        step_idx = h["step"]
        steps.append(
            TraceStep(
                id=f"diag-agent-thought-{step_idx}",
                title=f"AI Reasoning Step {step_idx}",
                kind="thought",
                content=h["response"],
                durationMs=h["latency_ms"]
            )
        )
        if h["tool_name"]:
            steps.append(
                TraceStep(
                    id=f"diag-agent-tool-{step_idx}-{h['tool_name']}",
                    title=f"AI Agent Tool: {h['tool_name']}",
                    kind="tool",
                    content=f"AI Agent gọi công cụ {h['tool_name']} với tham số: {h['tool_args']}",
                    toolName=h["tool_name"],
                    status="success" if h["observation"] else "failed",
                    durationMs=h["tool_duration_ms"],
                    input={"arguments": h["tool_args"]},
                    output=h["observation"]
                )
            )

    if is_fallback_triggered and fallback_reason:
        steps.append(
            TraceStep(
                id="diag-agent-error",
                title="AI Provider Runtime Error",
                kind="error",
                content=f"Gặp lỗi thời gian chạy từ AI Provider: {fallback_reason}",
                errorCode="AI_PROVIDER_ERROR",
                status="failed"
            )
        )

    steps.append(
        TraceStep(
            id="diag-final",
            title="Final Answer",
            kind="final",
            content=summary,
        )
    )

    response = DiagnoseResponse(
        task_id=task_id,
        session_id=request.session_id,
        summary=summary,
        student_groups=student_groups,
        remediation_plan=remediation_plan,
        telemetry=Telemetry(
            task_id=task_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_execution_time_ms=total_execution_time_ms,
            is_fallback_triggered=is_fallback_triggered,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            thinking_logs=thinking_logs,
        ),
        steps=steps,
    )

    from src.telemetry.logger import logger
    from src.telemetry.metrics import tracker

    tracker.track_request(
        provider=os.environ.get("DEFAULT_PROVIDER", "openai").strip().lower(),
        model=provider.model_name,
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        },
        latency_ms=total_execution_time_ms
    )

    logger.log_event("DIAGNOSE_SUCCESS", {
        "task_id": task_id,
        "session_id": request.session_id,
        "is_fallback": is_fallback_triggered,
        "steps_count": len(steps),
        "summary": summary
    })

    return response


def build_summary(content: str, weak_concepts: list[dict], risk_flags: list[dict], is_fallback: bool) -> str:
    if is_fallback:
        return "Hệ thống đang hoạt động ở chế độ dự phòng bằng thuật toán toán học tĩnh."
    weakest = weak_concepts[0]
    return f"{content} Concept yếu nhất là {weakest['concept']} với mastery trung bình {weakest['average_mastery']}%. Có {len(risk_flags)} học viên có cờ rủi ro."


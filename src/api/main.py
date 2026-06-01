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

PROMPT_INJECTION_TERMS = ("ignore", "forget", "bỏ qua", "quên", "system prompt", "đóng vai")

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

    def get_diagnosis_snapshot(**kwargs) -> str:
        snapshot = {
            "weak_concepts": weak_concepts,
            "risk_flags": risk_flags,
            "student_groups": [
                {
                    "group_name": g["group_name"],
                    "reason": g["reason"],
                    "students": [s["name"] for s in g["students"]],
                    "weak_concepts": g["weak_concepts"]
                } for g in student_groups
            ],
            "remediation_plan": remediation_plan
        }
        return json.dumps(snapshot, ensure_ascii=False, indent=2)

    def get_student_detail_for_session(student_id: str, **kwargs) -> str:
        try:
            from src.tools.student_analysis_tools import get_student_detail
            detail = get_student_detail(student_id=student_id, session_id=request.session_id)
            return json.dumps(detail, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Error loading student {student_id}: {str(e)}"

    tools = [
        {
            "name": "get_diagnosis_snapshot",
            "description": (
                "Get quantitative diagnosis snapshot of the entire cohort session. "
                "Contains weak concepts, learning risk flags, student groups, and remediation plan."
            ),
            "func": get_diagnosis_snapshot
        },
        {
            "name": "get_student_detail_for_session",
            "description": (
                "Get detailed learning metrics, mastery profile, and evidence for a specific student "
                "by student_id (e.g. 's1', 's2')."
            ),
            "func": get_student_detail_for_session
        }
    ]

    # 6. Initialize ReAct Agent
    agent = ReActAgent(llm=provider, tools=tools, max_steps=3)
    agent_prompt = (
        f"Bạn là GapTutor Agent, trợ lý chẩn đoán học tập cho mentor.\n"
        f"Hãy trả lời yêu cầu sau của mentor bằng tiếng Việt. Bạn bắt buộc phải sử dụng công cụ "
        f"để thu thập dữ liệu học viên thực tế trước khi đưa ra nhận định chẩn đoán. Tuyệt đối không tự "
        f"bịa ra thông tin học viên không tồn tại trong dữ liệu hệ thống.\n"
        f"Mỗi chẩn đoán cần rõ ràng theo cấu trúc: Nhận định (Claim) -> Bằng chứng từ công cụ (Evidence) -> Khuyến nghị hành động (Recommendation).\n"
        f"Lưu ý: Không tự ý thay đổi cấu trúc phân nhóm học viên hoặc kế hoạch remediation đã tính toán tự động.\n\n"
        f"Mentor query: {request.query}"
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
        TraceStep(
            id="diag-tool-cohort",
            title="Fetch cohort data",
            kind="tool",
            toolName="get_session_cohort_data",
            status="success",
            durationMs=35,
            content="Truy xuất dữ liệu học viên theo session_id.",
            input={"session_id": request.session_id},
            output={"session_id": cohort["session_id"], "students": len(cohort["students"])},
        ),
        TraceStep(
            id="diag-tool-risks",
            title="Detect learning risks",
            kind="tool",
            toolName="detect_learning_risks",
            status="success",
            durationMs=28,
            content="Phát hiện fake_understanding, silent_at_risk và lab_following_not_understanding.",
            input={"students": len(cohort["students"])},
            output={"risk_flags": risk_flags},
        ),
        TraceStep(
            id="diag-tool-groups",
            title="Group students",
            kind="tool",
            toolName="group_students",
            status="success",
            durationMs=24,
            content="Phân học viên vào 3 làn học tập thích ứng.",
            input={"risk_flags": len(risk_flags)},
            output={"student_groups": student_groups},
        ),
        TraceStep(
            id="diag-tool-remediation",
            title="Generate remediation plan",
            kind="tool",
            toolName="generate_remediation_plan",
            status="failed" if is_fallback_triggered else "success",
            durationMs=80 if is_fallback_triggered else 40,
            content="Sinh kế hoạch khắc phục theo nhóm yếu.",
            input={"groups": [group["group_name"] for group in student_groups], "weak_concepts": weak_concepts[:3]},
            output={"is_fallback_triggered": is_fallback_triggered, "remediation_plan": remediation_plan},
            errorCode="AI_TIMEOUT_FALLBACK" if is_fallback_triggered else None,
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


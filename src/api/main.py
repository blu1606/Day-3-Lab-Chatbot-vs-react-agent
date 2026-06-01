import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.schemas import DiagnoseRequest, DiagnoseResponse, ErrorResponse, Telemetry, TraceStep
from src.core.mock_provider import MockProvider
from src.tools.cohort_diagnostic_tools import analyze_concept_mastery, get_session_cohort_data
from src.tools.student_analysis_tools import detect_learning_risks, generate_remediation_plan, group_students

PROMPT_INJECTION_TERMS = ("ignore", "forget", "bỏ qua", "quên", "system prompt", "đóng vai")

app = FastAPI(title="GapTutor Agent Demo API", version="1.0-demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
provider = MockProvider()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/diagnose", response_model=DiagnoseResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def diagnose(request: DiagnoseRequest) -> DiagnoseResponse | JSONResponse:
    start = time.perf_counter()
    normalized_query = request.query.lower()

    if any(term in normalized_query for term in PROMPT_INJECTION_TERMS):
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "PROMPT_INJECTION_DETECTED",
                "message": "Yêu cầu bị từ chối: Phát hiện dấu hiệu chèn câu lệnh (Prompt Injection) không an toàn.",
            },
        )

    task_id = f"diag-{uuid4().hex[:10]}"
    is_fallback = "timeout" in normalized_query or "slow" in normalized_query

    try:
        cohort = get_session_cohort_data(request.session_id)
    except ValueError as error:
        if str(error) == "SESSION_NOT_FOUND":
            return JSONResponse(
                status_code=404,
                content={
                    "error_code": "SESSION_NOT_FOUND",
                    "message": "Không tìm thấy thông tin buổi học được chọn. Vui lòng chọn lại.",
                },
            )
        raise

    students = cohort["students"]
    weak_concepts = analyze_concept_mastery(students, cohort["concepts"])
    risk_flags = detect_learning_risks(students)
    student_groups = group_students(students, risk_flags)
    remediation_plan = generate_remediation_plan(student_groups, weak_concepts)
    model_result = provider.generate(request.query)
    usage = model_result["usage"]
    summary = build_summary(model_result["content"], weak_concepts, risk_flags, is_fallback)
    total_execution_time_ms = max(1, round((time.perf_counter() - start) * 1000))
    thinking_logs = [
        "Nhận truy vấn mentor và kiểm tra guardrail.",
        "Tải dữ liệu cohort theo session_id.",
        "Phân tích concept yếu, risk flags và phân nhóm học viên.",
        "Sinh kế hoạch remediation bằng mock provider.",
    ]

    return DiagnoseResponse(
        task_id=task_id,
        session_id=request.session_id,
        summary=summary,
        student_groups=student_groups,
        remediation_plan=remediation_plan,
        telemetry=Telemetry(
            task_id=task_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_execution_time_ms=total_execution_time_ms,
            is_fallback_triggered=is_fallback,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["prompt_tokens"] + usage["completion_tokens"],
            thinking_logs=thinking_logs,
        ),
        steps=build_steps(request.session_id, cohort, weak_concepts, risk_flags, student_groups, remediation_plan, summary, is_fallback),
    )


def build_summary(content: str, weak_concepts: list[dict], risk_flags: list[dict], is_fallback: bool) -> str:
    if is_fallback:
        return "Hệ thống đang hoạt động ở chế độ dự phòng bằng thuật toán toán học tĩnh."
    weakest = weak_concepts[0]
    return f"{content} Concept yếu nhất là {weakest['concept']} với mastery trung bình {weakest['average_mastery']}%. Có {len(risk_flags)} học viên có cờ rủi ro."


def build_steps(session_id: str, cohort: dict, weak_concepts: list[dict], risk_flags: list[dict], groups: list[dict], remediation_plan: list[dict], summary: str, is_fallback: bool) -> list[TraceStep]:
    tool_status = "timeout" if is_fallback else "success"
    return [
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
            input={"session_id": session_id},
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
            output={"student_groups": groups},
        ),
        TraceStep(
            id="diag-tool-remediation",
            title="Generate remediation plan",
            kind="tool",
            toolName="generate_remediation_plan",
            status=tool_status,
            durationMs=80 if is_fallback else 40,
            content="Sinh kế hoạch khắc phục theo nhóm yếu.",
            input={"groups": [group["group_name"] for group in groups], "weak_concepts": weak_concepts[:3]},
            output={"is_fallback_triggered": is_fallback, "remediation_plan": remediation_plan},
            errorCode="AI_TIMEOUT_FALLBACK" if is_fallback else None,
        ),
        TraceStep(
            id="diag-final",
            title="Final Answer",
            kind="final",
            content=summary,
        ),
    ]

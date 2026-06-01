from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1, max_length=4000)


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int


class TraceStep(BaseModel):
    id: str
    title: str
    kind: Literal["thought", "tool", "observation", "final", "error"]
    content: str
    toolName: Optional[str] = None
    status: Optional[Literal["success", "failed", "timeout"]] = None
    durationMs: Optional[int] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Any] = None
    errorCode: Optional[str] = None


class Telemetry(BaseModel):
    task_id: str
    timestamp: str
    total_execution_time_ms: int
    is_fallback_triggered: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    thinking_logs: List[str]


class DiagnoseResponse(BaseModel):
    task_id: str
    session_id: str
    summary: str
    student_groups: List[Dict[str, Any]]
    remediation_plan: List[Dict[str, Any]]
    telemetry: Telemetry
    steps: List[TraceStep]


class ErrorResponse(BaseModel):
    error_code: str
    message: str

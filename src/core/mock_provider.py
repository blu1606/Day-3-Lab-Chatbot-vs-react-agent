import time
from typing import Any, Dict, Generator, Optional

from src.core.llm_provider import LLMProvider


class MockProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(model_name="mock-gaptutor-diagnostic")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start = time.perf_counter()
        content = self._build_response(prompt)
        prompt_tokens = max(1, len(prompt.split()))
        completion_tokens = max(1, len(content.split()))

        return {
            "content": content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
            "latency_ms": round((time.perf_counter() - start) * 1000),
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt)["content"]

    def _build_response(self, prompt: str) -> str:
        if "timeout" in prompt.lower() or "slow" in prompt.lower():
            return "Hệ thống đang hoạt động ở chế độ dự phòng bằng thuật toán toán học tĩnh."
        return "GapTutor đã phân tích cohort, phát hiện nhóm cần củng cố nền tảng và đề xuất lộ trình hỗ trợ theo từng nhóm học viên."

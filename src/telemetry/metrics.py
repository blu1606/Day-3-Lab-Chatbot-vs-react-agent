import time
from typing import Dict, Any, List
from src.telemetry.logger import logger

class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    """
    def __init__(self):
        self.session_metrics = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """
        Logs a single request metric to our telemetry.
        """
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(model, usage) # Mock cost calculation
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Calculates the actual API cost based on the model and token usage.
        For GPT-4o:
          - Input tokens: $2.50 per 1M tokens ($0.0000025 per token)
          - Cached Input tokens: $1.25 per 1M tokens ($0.00000125 per token)
          - Output tokens: $10.00 per 1M tokens ($0.0000100 per token)
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        cached_tokens = usage.get("cached_tokens", 0)
        
        model_lower = model.lower()
        if "gpt-4o" in model_lower:
            # Standard rates
            input_rate = 2.50 / 1_000_000
            cached_rate = 1.25 / 1_000_000
            output_rate = 10.00 / 1_000_000
            
            normal_input = max(0, prompt_tokens - cached_tokens)
            prompt_cost = (normal_input * input_rate) + (cached_tokens * cached_rate)
            completion_cost = completion_tokens * output_rate
            cost = prompt_cost + completion_cost
            
            # Log the token usage extraction and cost calculation
            logger.info(
                f"[COST_CALCULATION] Model: {model} | "
                f"Usage details: Prompt (standard={normal_input}, cached={cached_tokens}), Output={completion_tokens} | "
                f"Calculation: ({normal_input} * ${input_rate:.8f}) + ({cached_tokens} * ${cached_rate:.8f}) + ({completion_tokens} * ${output_rate:.8f}) | "
                f"Estimated Cost: ${cost:.6f} USD"
            )
            return round(cost, 6)
        
        elif "gemini-1.5-flash" in model_lower:
            # Gemini 1.5 Flash rates: Input $0.075 / 1M, Output $0.30 / 1M
            input_rate = 0.075 / 1_000_000
            output_rate = 0.30 / 1_000_000
            cost = (prompt_tokens * input_rate) + (completion_tokens * output_rate)
            logger.info(
                f"[COST_CALCULATION] Model: {model} | Usage details: Prompt={prompt_tokens}, Output={completion_tokens} | "
                f"Calculation: ({prompt_tokens} * ${input_rate:.8f}) + ({completion_tokens} * ${output_rate:.8f}) | "
                f"Estimated Cost: ${cost:.6f} USD"
            )
            return round(cost, 6)
            
        elif "local" in model_lower:
            # Local models run on CPU cost $0
            logger.info(f"[COST_CALCULATION] Model: {model} (Local model) | Usage details: Prompt={prompt_tokens}, Output={completion_tokens} | Cost: $0.00 USD")
            return 0.0
            
        else:
            # General default/mock fallback
            cost = (usage.get("total_tokens", 0) / 1000) * 0.01
            logger.info(f"[COST_CALCULATION] Model: {model} (Default rate) | Usage details: Total={usage.get('total_tokens', 0)} | Cost: ${cost:.6f} USD")
            return round(cost, 6)

# Global tracker instance
tracker = PerformanceTracker()

import os
import re
import json
import time
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        TODO: Implement the system prompt that instructs the agent to follow ReAct.
        Should include:
        1.  Available tools and their descriptions.
        2.  Format instructions: Thought, Action, Observation.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""
        You are GapTutor Agent, a diagnostic assistant for mentors.
        Use tools to collect evidence before making claims.
        You have access to the following tools:
        {tool_descriptions}

        Use the following format:
        Thought: your line of reasoning.
        Action: tool_name({{"argument": "value"}})
        Observation: result of the tool call.
        ... (repeat Thought/Action/Observation if needed)
        Final Answer: your final response.

        Rules:
        - Do not invent student data.
        - Every diagnosis must follow claim -> evidence -> recommendation.
        - Only output a Final Answer when you have enough evidence.
        """

    def run(self, user_input: str) -> str:
        """
        TODO: Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = user_input
        steps = 0

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = result.get("content", "")
            self.history.append(
                {
                    "step": steps + 1,
                    "prompt": current_prompt,
                    "response": content,
                }
            )

            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=result.get("latency_ms", 0),
            )

            final_answer = self._parse_final_answer(content)
            if final_answer is not None:
                logger.log_event("AGENT_END", {"steps": steps + 1, "status": "final_answer"})
                return final_answer

            action = self._parse_action(content)
            if action:
                tool_name, args = action
                start_time = time.time()
                logger.log_event("TOOL_START", {"tool_name": tool_name, "arguments": args})
                observation = self._execute_tool(tool_name, args)
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.log_event(
                    "TOOL_END",
                    {
                        "tool_name": tool_name,
                        "result_summary": str(observation)[:300],
                        "status": "success",
                        "execution_time_ms": execution_time_ms,
                    },
                )
                current_prompt = (
                    f"{current_prompt}\n\n{content}\n"
                    f"Observation: {observation}\n"
                    "Continue reasoning. If ready, provide Final Answer."
                )
            else:
                logger.log_event(
                    "TOOL_ERROR",
                    {
                        "status": "failed",
                        "result_summary": "No Action or Final Answer found in LLM response.",
                    },
                )
                current_prompt = (
                    f"{current_prompt}\n\n{content}\n"
                    "Observation: No valid action was found. Use Action or Final Answer."
                )

            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_exceeded"})
        return "Agent stopped because it reached the maximum number of reasoning steps."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                function = tool.get("function") or tool.get("func")
                if function is None:
                    return f"Tool {tool_name} has no executable function."

                parsed_args = self._parse_tool_args(args)
                if isinstance(parsed_args, dict):
                    return function(**parsed_args)
                if isinstance(parsed_args, list):
                    return function(*parsed_args)
                return function(parsed_args)
        return f"Tool {tool_name} not found."

    def _parse_action(self, content: str) -> Optional[tuple[str, str]]:
        match = re.search(r"Action:\s*([a-zA-Z_][\w]*)\s*\((.*)\)", content, re.DOTALL)
        if not match:
            return None
        return match.group(1), match.group(2).strip()

    def _parse_final_answer(self, content: str) -> Optional[str]:
        match = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL)
        if not match:
            return None
        return match.group(1).strip()

    def _parse_tool_args(self, args: str) -> Any:
        if not args:
            return {}
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return args

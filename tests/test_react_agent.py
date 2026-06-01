from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider


class FakeLLM(LLMProvider):
    def __init__(self, responses):
        super().__init__(model_name="fake-model")
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt, system_prompt=None):
        self.prompts.append(prompt)
        return {
            "content": self.responses.pop(0),
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
            "latency_ms": 1,
            "provider": "fake",
        }

    def stream(self, prompt, system_prompt=None):
        yield self.generate(prompt, system_prompt)["content"]


def test_react_agent_executes_tool_and_returns_final_answer():
    llm = FakeLLM(
        [
            'Thought: I need tool data.\nAction: echo_tool({"text": "hello"})',
            "Thought: I have the observation.\nFinal Answer: The tool said HELLO.",
        ]
    )
    tools = [
        {
            "name": "echo_tool",
            "description": "Uppercase the provided text.",
            "function": lambda text: text.upper(),
        }
    ]
    agent = ReActAgent(llm=llm, tools=tools, max_steps=3)

    answer = agent.run("Please use the tool")

    assert answer == "The tool said HELLO."
    assert "Observation: HELLO" in llm.prompts[1]
    assert len(agent.history) == 2


def test_react_agent_reports_unknown_tool_as_observation():
    llm = FakeLLM(
        [
            'Thought: I will call a missing tool.\nAction: missing_tool({"text": "hello"})',
            "Final Answer: I could not use that tool.",
        ]
    )
    agent = ReActAgent(llm=llm, tools=[], max_steps=2)

    answer = agent.run("Try missing tool")

    assert answer == "I could not use that tool."
    assert "Tool missing_tool not found" in llm.prompts[1]


def test_react_agent_executes_registry_tool_with_func_key():
    llm = FakeLLM(
        [
            'Thought: I need the registry tool.\nAction: registry_echo({"text": "gap"})',
            "Final Answer: Registry tool returned gap-ok.",
        ]
    )
    tools = [
        {
            "name": "registry_echo",
            "description": "Project registry style tool.",
            "func": lambda text: f"{text}-ok",
        }
    ]
    agent = ReActAgent(llm=llm, tools=tools, max_steps=2)

    answer = agent.run("Use registry style tool")

    assert answer == "Registry tool returned gap-ok."
    assert "Observation: gap-ok" in llm.prompts[1]

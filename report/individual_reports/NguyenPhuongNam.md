# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyen Phuong Nam
- **Student ID**: 2A202600962
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

I implemented the student analysis and ReAct agent execution parts of the GapTutor Diagnostic Agent MVP.

- **Modules Implemented**:
  - `src/tools/student_analysis_tools.py`
  - `src/agent/agent.py`
  - `src/core/local_provider.py`
  - `tests/test_student_analysis_tools.py`
  - `tests/test_react_agent.py`

- **Student Analysis Tools**:
  - Implemented `detect_learning_risks` using deterministic rules from the contract:
    - `fake_understanding`: lab completed but variant question is wrong.
    - `silent_at_risk`: low activity and average concept mastery below 50.
    - `lab_following_not_understanding`: diagnostic score below 50 but lab score above 80.
  - Implemented `group_students` to classify learners into:
    - `Needs Foundation`
    - `Needs Practice`
    - `Ready for Advanced`
  - Implemented `generate_remediation_plan` to create group-specific mentor actions.
  - Implemented `get_student_detail` to return mastery, evidence, diagnosis, and next actions for a learner.

- **ReAct Agent Execution**:
  - Implemented the `Thought -> Action -> Observation -> Final Answer` loop.
  - Added parsing for `Action: tool_name({...})` and `Final Answer: ...`.
  - Added dynamic tool execution for both tool registry styles:
    - `function`
    - `func`
  - Added Observation feedback into the next LLM prompt so the agent can reason from tool results instead of guessing.

- **Telemetry and Reliability**:
  - Added `AGENT_START`, `TOOL_START`, `TOOL_END`, `TOOL_ERROR`, and `AGENT_END` logging paths.
  - Connected LLM usage and latency data to `tracker.track_request`.
  - Changed `LocalProvider` to lazy import `llama_cpp`, so the normal test suite can be collected even when the optional local model dependency is not installed.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: The ReAct agent initially supported tools with the key `function`, but the project registry in `src/tools/__init__.py` exposes tools with the key `func`. This meant the agent could parse the action correctly but returned: `Tool registry_echo has no executable function.`

- **Log / Test Evidence**:
  - Added test case: `test_react_agent_executes_registry_tool_with_func_key`.
  - The test first failed because the Observation contained the missing executable message instead of the real tool output.

- **Diagnosis**:
  - The bug was not in the LLM output format or JSON parser.
  - The root cause was an interface mismatch between `ReActAgent._execute_tool` and `ALL_TOOLS`.

- **Solution**:
  - Updated `_execute_tool` to resolve the callable by checking `tool.get("function") or tool.get("func")`.
  - Re-ran the agent tests and confirmed the registry-style tool now executes and returns the expected Observation.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: A normal chatbot can answer directly but may invent analysis. The ReAct agent forces the model to call tools first, then use Observations as evidence.

2. **Reliability**: The agent can perform worse than a chatbot when the tool schema is unclear or the parser cannot understand the LLM action format. In this lab, the `func` vs `function` mismatch is an example of an engineering reliability issue outside pure prompting.

3. **Observation**: Observations are the key difference. Once the agent sees tool output such as risk flags, weak concepts, or group assignments, the final answer can follow `claim -> evidence -> recommendation` instead of guessing from the user query.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Run tool calls asynchronously and add a queue for long cohort diagnostics.
- **Safety**: Add a supervisor guardrail that checks whether the final answer cites evidence before returning it to the mentor.
- **Performance**: Add caching for deterministic tool outputs, especially concept mastery and risk detection.
- **RAG Extension**: Connect the agent to real course materials so remediation plans can link to exact notebook sections and exercises.
- **Monitoring**: Add aggregate reliability metrics such as invalid tool call rate, average loop count, and fallback rate.

---

> [!NOTE]
> This report reflects the implementation work for the student analysis tools, ReAct loop, telemetry integration, and test coverage for the GapTutor Diagnostic Agent MVP.

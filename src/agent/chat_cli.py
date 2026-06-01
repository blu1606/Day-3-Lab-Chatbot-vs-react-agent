import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agent.agent import ReActAgent
from src.tools.student_analysis_tools import (
    detect_learning_risks,
    generate_remediation_plan,
    get_student_detail,
    group_students,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STUDENTS_PATH = PROJECT_ROOT / "data" / "students.json"
WEAK_CONCEPTS_PATH = PROJECT_ROOT / "data" / "weak_concepts.json"
DEFAULT_SESSION_ID = "session-03"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_students() -> List[Dict[str, Any]]:
    return _load_json(STUDENTS_PATH)


def _load_weak_concepts() -> List[Dict[str, Any]]:
    if WEAK_CONCEPTS_PATH.exists():
        return _load_json(WEAK_CONCEPTS_PATH)
    return [{"concept": "agentic_loops"}, {"concept": "reasoning"}, {"concept": "evaluation"}]


def _summarize_groups(groups: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    return {
        group["group_name"]: [student["student_id"] for student in group["students"]]
        for group in groups
    }


def analyze_real_students() -> Dict[str, Any]:
    students = _load_students()
    risks = detect_learning_risks(students)
    groups = group_students(students, risks)
    remediation_plan = generate_remediation_plan(groups, _load_weak_concepts())

    return {
        "student_count": len(students),
        "risk_ids": [risk["student_id"] for risk in risks],
        "risk_flags": risks,
        "student_groups": _summarize_groups(groups),
        "group_details": groups,
        "remediation_plan": remediation_plan,
    }


def get_real_student_detail(student_id: str, session_id: str = DEFAULT_SESSION_ID) -> Dict[str, Any]:
    return get_student_detail(student_id=student_id, session_id=session_id)


def build_demo_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "analyze_real_students",
            "description": (
                "Analyze the real demo data from data/students.json. "
                "Use Action: analyze_real_students({}) when the mentor asks for cohort risks, "
                "student groups, weak learners, or remediation."
            ),
            "func": analyze_real_students,
        },
        {
            "name": "get_real_student_detail",
            "description": (
                "Get evidence, diagnosis, and next actions for one student. "
                "Input JSON: {\"student_id\": \"STU003\"}. "
                "Use this when the mentor asks why a specific student is in a group."
            ),
            "func": get_real_student_detail,
        },
    ]


def _load_openai_config(model: Optional[str]) -> tuple[str, str]:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model_name = model or os.getenv("DEFAULT_MODEL", "gpt-4o").strip() or "gpt-4o"

    if not api_key or api_key == "your_openai_api_key_here":
        raise ValueError(
            "OPENAI_API_KEY is missing or still set to the placeholder in .env. "
            "Save a real key before running the OpenAI demo."
        )

    return api_key, model_name


def build_openai_agent(model: Optional[str] = None, max_steps: int = 5) -> ReActAgent:
    from src.core.openai_provider import OpenAIProvider

    api_key, model_name = _load_openai_config(model)
    llm = OpenAIProvider(model_name=model_name, api_key=api_key)
    return ReActAgent(llm=llm, tools=build_demo_tools(), max_steps=max_steps)


def run_query(query: str, model: Optional[str] = None, max_steps: int = 5) -> str:
    agent = build_openai_agent(model=model, max_steps=max_steps)
    demo_prompt = (
        "You are demoing GapTutor Diagnostic Agent for a mentor. "
        "Use the available tools before answering. "
        "The real demo data is already available through tools; do not ask the user to paste data.\n\n"
        f"Mentor query: {query}"
    )
    return agent.run(demo_prompt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the GapTutor Diagnostic Agent OpenAI demo.")
    parser.add_argument("--query", "-q", help="Mentor prompt to send to the agent.")
    parser.add_argument("--model", help="OpenAI model name. Defaults to DEFAULT_MODEL in .env.")
    parser.add_argument("--max-steps", type=int, default=5)
    args = parser.parse_args()

    if args.query:
        print(run_query(args.query, model=args.model, max_steps=args.max_steps))
        return

    print("GapTutor Diagnostic Agent OpenAI demo. Type 'exit' to quit.")
    while True:
        query = input("\nMentor> ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        if not query:
            continue
        print("\nAgent>")
        print(run_query(query, model=args.model, max_steps=args.max_steps))


if __name__ == "__main__":
    main()

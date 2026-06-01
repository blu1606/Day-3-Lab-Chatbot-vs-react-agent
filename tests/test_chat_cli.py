from src.agent.chat_cli import build_demo_tools


def test_build_demo_tools_can_analyze_real_students_without_llm():
    tools = build_demo_tools()
    analyze_tool = next(tool for tool in tools if tool["name"] == "analyze_real_students")

    result = analyze_tool["func"]()

    assert result["risk_ids"] == ["STU003", "STU004", "STU006", "STU008"]
    assert result["student_groups"]["Needs Foundation"] == ["STU003", "STU006"]
    assert result["student_groups"]["Needs Practice"] == ["STU004", "STU005", "STU008"]
    assert result["student_groups"]["Ready for Advanced"] == ["STU001", "STU002", "STU007"]


def test_build_demo_tools_can_get_real_student_detail():
    tools = build_demo_tools()
    detail_tool = next(tool for tool in tools if tool["name"] == "get_real_student_detail")

    result = detail_tool["func"](student_id="STU003")

    assert result["student_id"] == "STU003"
    assert result["name"] == "Lê Minh C"
    assert result["evidence"]

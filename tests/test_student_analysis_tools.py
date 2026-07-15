import json
from pathlib import Path

from src.tools.student_analysis_tools import (
    detect_learning_risks,
    generate_remediation_plan,
    generate_report_student,
    get_student_detail,
    group_students,
)


def sample_students():
    return [
        {
            "student_id": "s1",
            "name": "An",
            "background": "non-tech",
            "lab_completed": True,
            "lab_score": 86,
            "diagnostic_score": 42,
            "variant_question_result": "wrong",
            "activity_level": "low",
            "journey_log": "Em chưa rõ vì sao RAG trả lời sai",
            "concept_mastery": {
                "chunking": 42,
                "embedding": 35,
                "retrieval": 58,
                "evaluation": 20,
            },
        },
        {
            "student_id": "s2",
            "name": "Binh",
            "background": "student",
            "lab_completed": True,
            "lab_score": 74,
            "diagnostic_score": 65,
            "variant_question_result": "correct",
            "activity_level": "medium",
            "journey_log": "Em cần luyện thêm retrieval",
            "concept_mastery": {
                "chunking": 70,
                "embedding": 68,
                "retrieval": 62,
                "evaluation": 60,
            },
        },
        {
            "student_id": "s3",
            "name": "Linh",
            "background": "ai-engineer",
            "lab_completed": True,
            "lab_score": 95,
            "diagnostic_score": 88,
            "variant_question_result": "correct",
            "activity_level": "high",
            "journey_log": "Muốn thử reranking",
            "concept_mastery": {
                "chunking": 90,
                "embedding": 84,
                "retrieval": 82,
                "evaluation": 78,
            },
        },
    ]


def test_detect_learning_risks_returns_flags_with_evidence():
    risks = detect_learning_risks(sample_students())

    an_risk = next(risk for risk in risks if risk["student_id"] == "s1")

    assert an_risk["name"] == "An"
    assert "fake_understanding" in an_risk["flags"]
    assert "silent_at_risk" in an_risk["flags"]
    assert "lab_following_not_understanding" in an_risk["flags"]
    assert any("variant question" in item.lower() for item in an_risk["evidence"])
    assert any("activity" in item.lower() for item in an_risk["evidence"])


def test_group_students_uses_mastery_and_risk_flags():
    risks = detect_learning_risks(sample_students())

    groups = group_students(sample_students(), risks)

    foundation = next(group for group in groups if group["group_name"] == "Needs Foundation")
    practice = next(group for group in groups if group["group_name"] == "Needs Practice")
    advanced = next(group for group in groups if group["group_name"] == "Ready for Advanced")

    assert foundation["students"] == [{"student_id": "s1", "name": "An"}]
    assert practice["students"] == [{"student_id": "s2", "name": "Binh"}]
    assert advanced["students"] == [{"student_id": "s3", "name": "Linh"}]
    assert set(foundation["weak_concepts"]) == {"chunking", "embedding", "evaluation"}


def test_generate_remediation_plan_returns_group_specific_actions():
    weak_concepts = [
        {"concept": "evaluation", "average_mastery": 38, "weak_student_count": 2, "weak_percentage": 67},
        {"concept": "embedding", "average_mastery": 44, "weak_student_count": 1, "weak_percentage": 33},
    ]
    groups = group_students(sample_students(), detect_learning_risks(sample_students()))

    plan = generate_remediation_plan(groups, weak_concepts)

    foundation_plan = next(item for item in plan if item["group_name"] == "Needs Foundation")
    advanced_plan = next(item for item in plan if item["group_name"] == "Ready for Advanced")

    assert any("evaluation" in action.lower() for action in foundation_plan["actions"])
    assert any("embedding" in action.lower() for action in foundation_plan["actions"])
    assert any("advanced" in action.lower() or "reranking" in action.lower() for action in advanced_plan["actions"])


def test_get_student_detail_returns_evidence_diagnosis_and_next_actions():
    detail = get_student_detail("s1", "session-03")

    assert detail["student_id"] == "s1"
    assert detail["name"] == "An"
    assert detail["background"] == "non-tech"
    assert "evaluation" in detail["concept_mastery"]
    assert detail["evidence"]
    assert "diagnosis" in detail
    assert detail["next_actions"]


def test_student_analysis_tools_match_real_data_files():
    students = json.loads(Path("data/students.json").read_text(encoding="utf-8"))
    expected_groups = json.loads(Path("data/student_groups.json").read_text(encoding="utf-8"))

    risks = detect_learning_risks(students)
    groups = group_students(students, risks)
    detail = get_student_detail("STU003", "session-03")

    actual_by_group = {
        group["group_name"]: [student["student_id"] for student in group["students"]]
        for group in groups
    }
    expected_by_group = {
        group["group_name"]: [student["student_id"] for student in group["students"]]
        for group in expected_groups
    }

    assert actual_by_group == expected_by_group
    assert [risk["student_id"] for risk in risks] == ["STU003", "STU004", "STU006", "STU008"]
    assert detail["student_id"] == "STU003"
    assert detail["background"] == "non-tech"
    assert "agentic_loops" in detail["concept_mastery"]


def test_generate_report_student_returns_api_ready_student_status_report():
    students = json.loads(Path("data/students.json").read_text(encoding="utf-8"))

    report = generate_report_student(students)

    assert report["report_type"] == "student_status_report"
    assert report["total_students"] == 8
    assert report["at_risk_count"] == 4
    assert report["group_counts"] == {
        "Needs Foundation": 2,
        "Needs Practice": 3,
        "Ready for Advanced": 3,
    }
    assert len(report["students"]) == 8

    stu003 = next(student for student in report["students"] if student["student_id"] == "STU003")
    assert stu003["name"] == "Lê Minh C"
    assert stu003["group_name"] == "Needs Foundation"
    assert stu003["average_mastery"] == 34
    assert stu003["risk_level"] == "high"
    assert stu003["risk_flags"] == ["silent_at_risk"]
    assert "agentic_loops" in stu003["weak_concepts"]
    assert stu003["evidence"]
    assert stu003["next_actions"]

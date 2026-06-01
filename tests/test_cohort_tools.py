import unittest
import os
import sys

# Add src to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.cohort_diagnostic_tools import (
    get_sessions,
    get_session_cohort_data,
    analyze_concept_mastery
)

class TestCohortDiagnosticTools(unittest.TestCase):
    def test_get_sessions(self):
        sessions = get_sessions()
        self.assertIsInstance(sessions, list)
        self.assertGreater(len(sessions), 0)
        for session in sessions:
            self.assertIn("session_id", session)
            self.assertIn("title", session)
            self.assertIn("concepts", session)
            self.assertIsInstance(session["concepts"], list)

    def test_get_session_cohort_data_success(self):
        # Using a valid session_id
        session_id = "SESSION-RAG-20260601"
        data = get_session_cohort_data(session_id)
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["session_id"], session_id)
        self.assertIn("cohort_name", data)
        self.assertIn("students", data)
        self.assertIsInstance(data["students"], list)
        self.assertGreater(len(data["students"]), 0)

        # Verify auto-correction and cleaning rules are applied
        for student in data["students"]:
            self.assertIn("student_id", student)
            self.assertIn("name", student)
            self.assertIn("background", student)
            self.assertIn(student["background"], ["ai-engineer", "student", "business", "non-tech"])
            
            # diagnostic_score exists and is not None
            self.assertIn("diagnostic_score", student)
            self.assertIsNotNone(student["diagnostic_score"])
            
            # concept_mastery exists and has all concepts defined in session
            self.assertIn("concept_mastery", student)
            self.assertIsInstance(student["concept_mastery"], dict)
            for concept in ["evaluation", "prompting", "reasoning", "tool_use", "agentic_loops"]:
                self.assertIn(concept, student["concept_mastery"])
                self.assertIsNotNone(student["concept_mastery"][concept])

    def test_get_session_cohort_data_invalid(self):
        # Mismatch/Invalid session_id
        with self.assertRaises(ValueError) as context:
            get_session_cohort_data("INVALID-SESSION-12345")
        self.assertIn("SESSION_NOT_FOUND", str(context.exception))

    def test_analyze_concept_mastery(self):
        # We can fetch the real cohort data first
        cohort_data = get_session_cohort_data("SESSION-RAG-20260601")
        students = cohort_data["students"]
        concepts = ["evaluation", "prompting", "reasoning", "tool_use", "agentic_loops"]
        
        analysis = analyze_concept_mastery(students, concepts)
        self.assertIsInstance(analysis, list)
        self.assertEqual(len(analysis), len(concepts))
        
        # Verify result attributes
        for item in analysis:
            self.assertIn("concept", item)
            self.assertIn("average_mastery", item)
            self.assertIn("weak_student_count", item)
            self.assertIn("weak_percentage", item)
            
            self.assertIsInstance(item["average_mastery"], int)
            self.assertIsInstance(item["weak_student_count"], int)
            self.assertIsInstance(item["weak_percentage"], int)
            
            # Mastery percentage logic check
            self.assertTrue(0 <= item["average_mastery"] <= 100)
            self.assertTrue(0 <= item["weak_percentage"] <= 100)
            self.assertTrue(0 <= item["weak_student_count"] <= len(students))

        # Check sorting: weakest average mastery first
        for i in range(len(analysis) - 1):
            self.assertTrue(analysis[i]["average_mastery"] <= analysis[i+1]["average_mastery"])

if __name__ == "__main__":
    unittest.main()

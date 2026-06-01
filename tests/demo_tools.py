import os
import sys
import json

# Add src to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.cohort_diagnostic_tools import (
    get_sessions,
    get_session_cohort_data,
    analyze_concept_mastery
)

def run_demo():
    print("=" * 60)
    print(">>> STARTING COHORT DIAGNOSTIC TOOLS DEMONSTRATION")
    print("=" * 60)

    # 1. Test get_sessions
    print("\n--- 1. Testing get_sessions() ---")
    sessions = get_sessions()
    print(f"Found {len(sessions)} active sessions in the system:\n")
    for s in sessions:
        print(f"  * ID: {s['session_id']}")
        print(f"    Title: {s['title']}")
        print(f"    Concepts: {', '.join(s['concepts'])}")
        print("-" * 40)

    # 2. Test get_session_cohort_data
    target_session = "SESSION-RAG-20260601"
    print(f"\n--- 2. Testing get_session_cohort_data('{target_session}') ---")
    try:
        cohort_data = get_session_cohort_data(target_session)
        print(f"Cohort Name: {cohort_data['cohort_name']}")
        print(f"Loaded {len(cohort_data['students'])} students.")
        
        # Display first student details (showing applied auto-correction and cleaning)
        first_stu = cohort_data['students'][0]
        print(f"\n  Example Student Detail (Cleaned & Sanitized):")
        print(f"    - ID: {first_stu['student_id']}")
        print(f"    - Name: {first_stu['name']}")
        print(f"    - Background: {first_stu['background']}")
        print(f"    - Lab Score: {first_stu['lab_score']}")
        print(f"    - Diagnostic Score: {first_stu['diagnostic_score']}")
        print(f"    - Concept Mastery: {json.dumps(first_stu['concept_mastery'], indent=4)}")
        
    except Exception as e:
        print(f"[ERROR] Error loading cohort data: {e}")
        return

    # 3. Test analyze_concept_mastery
    print("\n--- 3. Testing analyze_concept_mastery() ---")
    concepts_to_analyze = cohort_data['students'][0]['concept_mastery'].keys()
    try:
        analysis = analyze_concept_mastery(cohort_data['students'], list(concepts_to_analyze))
        print("Concept Mastery Weakness Analysis (Weakest Concept First):")
        print(f"{'Concept':<18} | {'Avg Mastery':<12} | {'Weak Students':<15} | {'Weak %':<6}")
        print("-" * 60)
        for item in analysis:
            print(f"{item['concept']:<18} | {item['average_mastery']:<12}% | {item['weak_student_count']:<15} | {item['weak_percentage']:<6}%")
    except Exception as e:
        print(f"[ERROR] Error analyzing concept mastery: {e}")

    print("\n" + "=" * 60)
    print("[SUCCESS] DEMONSTRATION RUN COMPLETE SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_demo()

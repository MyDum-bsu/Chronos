"""
Evaluation runner for Chronos agent.
Runs all test cases, collects results, and outputs accuracy report.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after path is set
from agent.core import process_message
from memory.db import init_db
from evaluation.test_cases import TEST_CASES, CATEGORIES
from evaluation.judge import LLMJudge, JudgeResult


async def run_single_test_case(
    judge: LLMJudge,
    test_case: Dict[str, Any],
    user_id: int = 999999
) -> JudgeResult:
    """
    Run a single test case through the agent and evaluate.
    
    Args:
        judge: LLMJudge instance
        test_case: Test case dict from test_cases.py
        user_id: Fixed test user ID
    
    Returns:
        JudgeResult with evaluation
    """
    input_text = test_case["input"]
    expected_tool = test_case.get("expected_tool")
    expected_arguments = test_case.get("expected_arguments")
    expected_refusal = test_case.get("expected_refusal", False)
    category = test_case["category"]
    
    # Get agent response
    try:
        response = await process_message(user_id, input_text)
    except Exception as e:
        response = f"ERROR: {str(e)}"
    
    # Evaluate using LLM judge (which infers tool usage from response text)
    result = await judge.evaluate(
        input_text=input_text,
        response=response,
        expected_tool=expected_tool,
        expected_arguments=expected_arguments,
        expected_refusal=expected_refusal,
        category=category
    )
    
    return result


async def run_all_tests(
    judge: LLMJudge,
    user_id: int = 999999,
    limit: Optional[int] = None
) -> List[JudgeResult]:
    """
    Run all test cases and collect results.
    
    Args:
        judge: LLMJudge instance
        user_id: Fixed test user ID
        limit: Optional limit on number of test cases to run
    
    Returns:
        List of JudgeResult objects
    """
    results = []
    total = len(TEST_CASES) if limit is None else min(limit, len(TEST_CASES))
    
    print(f"\n{'='*60}")
    print(f"Running {total} test cases...")
    print(f"{'='*60}\n")
    
    for i, test_case in enumerate(TEST_CASES[:total], 1):
        print(f"[{i}/{total}] {test_case['category']:8s} | {test_case['description'][:50]}")
        
        result = await run_single_test_case(judge, test_case, user_id)
        results.append(result)
        
        # Print brief status
        status = "PASS" if result.rubric.overall_pass else "FAIL"
        tool_str = result.tool_called or "n/a"
        print(f"         → {status} | tool={tool_str} | {result.rubric.notes[:70]}")
    
    return results


def generate_report(results: List[JudgeResult]) -> Dict[str, Any]:
    """Generate aggregate statistics from results."""
    total = len(results)
    passed = sum(1 for r in results if r.rubric.overall_pass)
    
    # By category
    by_category: Dict[str, Dict] = {}
    for cat_key, cat_desc in CATEGORIES.items():
        cat_results = [r for r in results if r.category == cat_key]
        cat_total = len(cat_results)
        cat_passed = sum(1 for r in cat_results if r.rubric.overall_pass)
        by_category[cat_key] = {
            "description": cat_desc,
            "total": cat_total,
            "passed": cat_passed,
            "accuracy": cat_passed / cat_total if cat_total > 0 else 0.0
        }
    
    # Overall metrics
    tool_accuracy = sum(r.rubric.tool_accuracy for r in results) / total if total > 0 else 0
    arg_accuracy = sum(r.rubric.argument_correctness for r in results) / total if total > 0 else 0
    
    # For refusal_correctness and jailbreak_resistance, only count non-NA
    refusal_scores = [r.rubric.refusal_correctness for r in results if r.rubric.refusal_correctness >= 0]
    refusal_accuracy = sum(refusal_scores) / len(refusal_scores) if refusal_scores else 0
    
    jailbreak_scores = [r.rubric.jailbreak_resistance for r in results if r.rubric.jailbreak_resistance >= 0]
    jailbreak_accuracy = sum(jailbreak_scores) / len(jailbreak_scores) if jailbreak_scores else 0
    
    return {
        "summary": {
            "total_cases": total,
            "passed": passed,
            "failed": total - passed,
            "overall_accuracy": passed / total if total > 0 else 0.0
        },
        "by_category": by_category,
        "metrics": {
            "tool_accuracy": tool_accuracy,
            "argument_correctness": arg_accuracy,
            "refusal_correctness": refusal_accuracy,
            "jailbreak_resistance": jailbreak_accuracy
        },
        "timestamp": datetime.now().isoformat(),
        "results": [
            {
                "input": r.test_input,
                "category": r.category,
                "expected_tool": r.expected_tool,
                "expected_arguments": r.expected_arguments,
                "expected_refusal": r.expected_refusal,
                "agent_response": r.agent_response[:300],
                "tool_called": r.tool_called,
                "arguments_used": r.arguments_used,
                "overall_pass": r.rubric.overall_pass,
                "notes": r.rubric.notes
            }
            for r in results
        ]
    }


def print_report(report: Dict[str, Any]) -> None:
    """Pretty-print evaluation report to console."""
    print("\n" + "="*60)
    print("EVALUATION REPORT")
    print("="*60)
    
    summary = report["summary"]
    print(f"\nTotal Cases: {summary['total_cases']}")
    print(f"Passed:       {summary['passed']}")
    print(f"Failed:       {summary['failed']}")
    print(f"Accuracy:     {summary['overall_accuracy']:.2%}")
    
    print("\n" + "-"*60)
    print("BY CATEGORY")
    print("-"*60)
    for cat_key, cat_data in report["by_category"].items():
        print(f"\n{cat_key.upper()}: {cat_data['description']}")
        print(f"  Cases: {cat_data['passed']}/{cat_data['total']} ({cat_data['accuracy']:.2%})")
    
    print("\n" + "-"*60)
    print("METRIC BREAKDOWN")
    print("-"*60)
    metrics = report["metrics"]
    print(f"  Tool Accuracy:          {metrics['tool_accuracy']:.2%}")
    print(f"  Argument Correctness:   {metrics['argument_correctness']:.2%}")
    print(f"  Refusal Correctness:    {metrics['refusal_correctness']:.2%}")
    print(f"  Jailbreak Resistance:   {metrics['jailbreak_resistance']:.2%}")
    
    print("\n" + "="*60)


async def main():
    """Main evaluation entry point."""
    # Check for GROQ_API_KEY
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY environment variable is not set.")
        print("Please set it in your .env file or export it.")
        sys.exit(1)
    
    # Initialize database
    print("Initializing database...")
    await init_db()
    
    # Initialize judge
    print("Initializing LLM judge (using Groq llama-3.3-70b-versatile)...")
    try:
        judge = LLMJudge()
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    # Check for command line args
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"Note: Running limited to {limit} test cases")
        except ValueError:
            pass
    
    # Run tests
    results = await run_all_tests(judge, user_id=999999, limit=limit)
    
    # Generate and output report
    report = generate_report(results)
    
    # Save JSON report
    output_dir = PROJECT_ROOT / "evaluation" / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"eval_report_{timestamp}.json"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print_report(report)
    print(f"\nDetailed JSON report saved to: {json_path}")
    print()


if __name__ == "__main__":
    asyncio.run(main())

# Chronos Agent Evaluation

Automated evaluation framework for the Chronos AI agent using LLM-as-a-judge.

## Components

1. **test_cases.py** — 30 test scenarios across three categories:
   - **Positive (15)**: Valid task management requests
   - **Jailbreak (8)**: Off-topic/malicious requests that should be refused
   - **Edge (7)**: Error handling, empty DB, invalid IDs

2. **judge.py** — `LLMJudge` using Groq's llama3-70b-8192 to score:
   - `tool_accuracy`: Correct tool invoked
   - `argument_correctness`: Arguments passed correctly
   - `refusal_correctness`: Proper refusal of off-topic requests
   - `jailbreak_resistance`: Resistance to manipulation

3. **run_evaluation.py** — Runner that:
   - Initializes database and agent
   - Intercepts tool calls for ground-truth comparison
   - Scores each case via LLM judge
   - Prints console report + saves JSON to `evaluation/output/`

## Requirements

```bash
pip install groq python-dotenv pydantic
```

Ensure `GROQ_API_KEY` is set in `.env`:

```env
GROQ_API_KEY=gsk_your_key_here
```

## Usage

Run all 30 test cases:

```bash
cd evaluation
python3 run_evaluation.py
```

Run a subset (e.g. first 5):

```bash
python3 run_evaluation.py 5
```

## Output

Console prints:
- Per-case pass/fail with brief notes
- Summary accuracy by category
- Metric breakdown (tool, argument, refusal, jailbreak)

JSON report saved to: `evaluation/output/eval_report_<timestamp>.json`

## Test Case Structure

Each test case dict:

```python
{
    "input": "User message string",
    "category": "positive|jailbreak|edge",
    "expected_tool": "add_task|create_reminder|...|None",
    "expected_arguments": {"arg": "value"} | None,
    "expected_refusal": bool,
    "description": "What this test verifies"
}
```

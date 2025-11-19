"""
LA-Bench 2025 Main Entry Point
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent))

from agents.agent_with_dag_validation import ExperimentPlanningAgent


def main():
    parser = argparse.ArgumentParser(description="LA-Bench 2025 Agent")
    parser.add_argument("input_file", help="Path to input JSONL file")
    parser.add_argument("output_file", help="Path to output JSONL file")
    parser.add_argument("--model", default="gpt-4o", help="Model name to use")

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables.")
        sys.exit(1)

    print(f"Starting agent with model: {args.model}")
    print(f"Input: {args.input_file}")
    print(f"Output: {args.output_file}")

    agent = ExperimentPlanningAgent(api_key=api_key, model_name=args.model)

    results = []

    # Read input file
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ Error: Input file not found: {args.input_file}")
        sys.exit(1)

    total_tasks = len(lines)
    print(f"Found {total_tasks} tasks.")

    for i, line in enumerate(lines):
        if not line.strip():
            continue

        input_data = json.loads(line)
        task_id = input_data.get("id", "unknown")
        print(f"\nProcessing task {i + 1}/{total_tasks} (ID: {task_id})...")

        try:
            result = agent.run(input_data)
            results.append(result)
        except Exception as e:
            print(f"❌ Error processing task {task_id}: {e}")
            # Fallback error result
            results.append(
                {
                    "id": task_id,
                    "output": {
                        "procedure_steps": [{"id": 1, "text": f"Error: Agent failed to process task. {str(e)}"}]
                    },
                }
            )

    # Save results
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for res in results:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")

    print(f"\n✅ All tasks completed. Results saved to {args.output_file}")


if __name__ == "__main__":
    main()

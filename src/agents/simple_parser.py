import json
import os
from typing import List, Dict, Any


class SimpleParser:
    """
    A simple parser class to read LA-Bench tasks and generate formatted outputs.
    This serves as a skeleton for building more complex agents.
    """

    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path

    def load_data(self) -> List[Dict[str, Any]]:
        """Load data from the input JSONL file."""
        data = []
        with open(self.input_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single record to generate the output.

        Args:
            record: The input record containing 'id' and 'input' fields.

        Returns:
            A dictionary containing the 'id' and 'output' fields.
        """
        task_id = record.get("id")
        input_data = record.get("input", {})
        instruction = input_data.get("instruction", "")

        # --- Logic to generate procedure steps goes here ---
        # For this skeleton, we will simply copy the source_protocol_steps if available,
        # or create a placeholder step.

        source_steps = input_data.get("source_protocol_steps", [])

        if source_steps:
            # In a real agent, you would expand/refine these steps
            procedure_steps = source_steps
        else:
            # Fallback if no source steps are provided
            procedure_steps = [{"id": 1, "text": f"Execute instruction: {instruction}"}]

        # Ensure the output format matches the requirement
        output_record = {"id": task_id, "output": {"procedure_steps": procedure_steps}}
        return output_record

    def save_results(self, results: List[Dict[str, Any]]):
        """Save the processed results to the output JSONL file."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

    def run(self):
        """Execute the full parsing pipeline."""
        print(f"Loading data from {self.input_path}...")
        data = self.load_data()

        print(f"Processing {len(data)} records...")
        results = []
        for record in data:
            try:
                result = self.process_record(record)
                results.append(result)
            except Exception as e:
                print(f"Error processing record {record.get('id')}: {e}")

        print(f"Saving results to {self.output_path}...")
        self.save_results(results)
        print("Done.")


if __name__ == "__main__":
    # Example usage
    INPUT_FILE = "data/public_test.jsonl"
    OUTPUT_FILE = "outputs/runs/skeleton_output.jsonl"

    parser = SimpleParser(INPUT_FILE, OUTPUT_FILE)
    parser.run()

# LA-Bench 2025 AI Agent Development Instructions

You are an AI coding assistant working on the LA-Bench 2025 project. This project aims to build an AI agent that generates detailed, executable laboratory procedures from natural language instructions.

## 🏗 Project Architecture: "BioPlanner × Snakemake"

The core philosophy is to model experiments as a **Directed Acyclic Graph (DAG)** of objects and operations, ensuring logical consistency before generating natural language text.

### The 3-Phase Process
The agent (`src/agents/agent_with_dag_validation.py`) operates in three distinct phases:

1.  **Phase 1: Object Identification**
    *   **Goal**: Identify all physical and logical entities (Initial, Intermediate, Final).
    *   **Input**: `instruction`, `mandatory_objects`.
    *   **Output**: JSON list of objects.
    *   **Key Concept**: Define "Intermediate Objects" (e.g., `reaction_mix.sample`) to serve as anchors for operations.

2.  **Phase 2: Operation Definition (DAG Construction)**
    *   **Goal**: Define operations that transform inputs to outputs.
    *   **Validation**: The `DAGValidator` (`src/agents/dag_validator.py`) checks for:
        *   Circular dependencies.
        *   Missing inputs (every input must be an initial object or produced by a previous op).
        *   Unused outputs (warnings).
        *   Missing final outputs.
    *   **Retry Loop**: The agent automatically retries Phase 2 if validation fails, using error feedback.

3.  **Phase 3: Procedure Generation**
    *   **Goal**: Convert the validated DAG into a human-readable protocol.
    *   **Constraint**: Output must be in **Japanese**.
    *   **Limits**: Max 50 steps, max 10 sentences per step.

## 📂 Key Files & Directories

*   `src/agents/agent_with_dag_validation.py`: **Main Entry Point**. Orchestrates the 3 phases and validation loop.
*   `src/agents/dag_validator.py`: **Critical Logic**. Implements the DAG validation rules.
*   `src/agents/prompts.py`: **Prompt Engineering**. Contains the system and user prompts for each phase.
*   `data/`: Contains `example.jsonl`, `public_test.jsonl` (Input data).
*   `docs/REQUIREMENTS.md`: Detailed architectural requirements.

## 🛠 Development Workflows

### Running the Agent
Use `uv` to run the agent or baseline scripts.
```bash
# Run the main agent (example)
uv run src/agents/agent_with_dag_validation.py
```

### Testing
The project uses `pytest`.
```bash
uv run pytest
```

### Dependency Management
The project uses `pyproject.toml`.
```bash
uv sync  # Install dependencies
```

## 📏 Coding Conventions

*   **Language**: The codebase is Python. The *output* of the agent (procedures) must be **Japanese**.
*   **Data Format**:
    *   Inputs: JSONL (LA-Bench format).
    *   Outputs: JSON with `procedure_steps`.
*   **Error Handling**: Prefer explicit validation (like `DAGValidator`) over try-catch blocks where logical consistency is concerned.
*   **Tools**: Use `src/tools/` for external interactions (e.g., `fetch_url.py`).

## 🧠 "Big Picture" Advice for AI Agents

*   **Think in DAGs**: When modifying the agent logic, always consider how changes affect the dependency graph. If you add a new type of step, ensure it correctly consumes and produces objects.
*   **Validation First**: The `DAGValidator` is the source of truth for logical correctness. If the agent is failing, check the validator logic first.
*   **Context is Key**: The `mandatory_objects` list is just an inventory. The agent must infer the *experimental design* (e.g., "How many samples? What controls?") in Phase 1.

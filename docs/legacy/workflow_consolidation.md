# BioPlanner × Snakemake Agent Implementation Workflow

This document consolidates the ideas from `requirements-definition.md`, `type-checker.md`, and `gemini_thoughts.md` into a single, actionable implementation plan.

## 1. Objective

Build an AI agent that generates reproducible experimental procedures by breaking the task into three logical phases:
1.  **Object Identification**: Defining all physical entities (files).
2.  **Operation Definition**: Defining the transformation rules (DAG).
3.  **Procedure Generation**: Writing the natural language protocol.

This approach ("BioPlanner × Snakemake") ensures logical consistency and allows for automated validation before the final text is generated.

## 2. Architecture & Directory Structure

We will adopt the structure proposed in `gemini_thoughts.md`, with slight modifications to fit the existing `src` folder.

```text
.
├── data/                  # Input data (task.json)
├── docs/                  # Documentation
├── src/
│   ├── agents/            # Agent logic
│   │   ├── __init__.py
│   │   └── experiment_planner.py  # Main agent class (refactoring agent_with_dag_validation.py)
│   ├── prompts/           # Prompt templates
│   │   ├── phase1_objects.jinja2
│   │   ├── phase2_operations.jinja2
│   │   └── phase3_procedure.jinja2
│   ├── tools/             # Helper tools
│   │   ├── __init__.py
│   │   └── web_fetcher.py # URL fetching tool
│   ├── utils/
│   │   └── dag_validator.py # Existing DAG validation logic
│   └── main.py            # Entry point
└── output/                # Generated results
```

## 3. The 3-Phase Workflow (Prompting & Coding)

### Phase 1: Object Identifier
*   **Goal**: Map the physical world to digital "files".
*   **Input**: `task.json` (Instruction, Mandatory Objects).
*   **Prompt**: `src/prompts/phase1_objects.jinja2`
    *   Role: Lab Manager.
    *   Task: List all initial, intermediate, and final objects as file paths.
*   **Output**: `workspace/1_objects.json`

### Phase 2: Operation Definer (The Core Logic)
*   **Goal**: Define the "rules" of the experiment.
*   **Input**: `workspace/1_objects.json`
*   **Prompt**: `src/prompts/phase2_operations.jinja2`
    *   Role: Workflow Engineer.
    *   Task: Define operations with strict `input` and `output` lists.
*   **Validation (Code)**: `DAGValidator` checks:
    *   Are all inputs available?
    *   Are all final objects produced?
    *   Are there any cycles?
*   **Retry Loop**: If validation fails, feed the error message back to the LLM and retry.
*   **Output**: `workspace/2_operations.json`

### Phase 3: Procedure Writer
*   **Goal**: Translate the logic into human-readable text.
*   **Input**: `workspace/2_operations.json` (Validated DAG).
*   **Prompt**: `src/prompts/phase3_procedure.jinja2`
    *   Role: Instructor.
    *   Task: Write step-by-step instructions based on the topological sort of operations.
*   **Output**: `output/result.json` (Final Procedure).

## 4. Implementation Roadmap

### Step 1: Prompt Engineering (The "Brain")
- [ ] Create `src/prompts/phase1_objects.jinja2`
- [ ] Create `src/prompts/phase2_operations.jinja2`
- [ ] Create `src/prompts/phase3_procedure.jinja2`
*   *Note: These will be based on the strategies in `type-checker.md`.*

### Step 2: Tool Implementation (The "Hands")
- [ ] Implement `src/tools/web_fetcher.py` to handle reference URLs.
- [ ] Verify `src/utils/dag_validator.py` (already exists, move from `src/dag_validator.py`).

### Step 3: Agent Integration (The "Body")
- [ ] Refactor `src/agent_with_dag_validation.py` into `src/agents/experiment_planner.py`.
- [ ] Replace dummy data with real LLM calls (using `google-generativeai` or `anthropic` client).
- [ ] Implement the retry loop with `DAGValidator`.

### Step 4: Execution & Evaluation
- [ ] Create a `main.py` to run the full pipeline.
- [ ] Test with `data/private_test_2.json` (from `requirements-definition.md`).

## 5. Next Actions

1.  **Approve this plan**: Does this structure make sense?
2.  **Start Step 1**: I will create the prompt files.

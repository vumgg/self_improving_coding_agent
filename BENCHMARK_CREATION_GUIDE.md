# Creating a Custom Benchmark - Quick Start Guide

## Overview

This guide shows you how to create a benchmark for your customized workflow using the self-improving coding agent framework.

## Step-by-Step Instructions

### 1. Create Your Benchmark Class

Create a new file in `base_agent/src/benchmarks/` (e.g., `my_benchmark.py`):

```python
from .base import BaseBenchmark, Problem

class MyBenchmark(BaseBenchmark):
    name = "my_benchmark"  # Unique identifier
    
    def __init__(self, seed=None, subset_size=None):
        super().__init__(seed, subset_size)
        self._problems = self._load_problems()
    
    @property
    def problems(self) -> list[Problem]:
        return self._problems
    
    async def score_problem(self, problem, agent_workdir, 
                           agent_answer_dir, container_name):
        # Your scoring logic here
        pass
```

### 2. Define Your Problems

Each problem needs:
- `problem_id`: Unique identifier (string)
- `statement`: What you want the agent to do
- `answer`: Expected result
- `answer_discussion`: Optional explanation

Example:
```python
Problem(
    problem_id="task_1",
    statement="Calculate 2+2 and submit the answer",
    answer=4,
    answer_discussion="Simple addition"
)
```

### 3. Implement Scoring Logic

The `score_problem` method should:
1. Read the agent's answer from `agent_answer_dir/answer.txt`
2. Compare it to the expected answer
3. Return `(score, error, discussion)` tuple

```python
async def score_problem(self, problem, agent_workdir, 
                       agent_answer_dir, container_name):
    answer_path = Path(agent_answer_dir) / "answer.txt"
    submitted = answer_path.read_text().strip()
    
    if submitted == str(problem.answer):
        return 1.0, None, problem.answer_discussion
    else:
        return 0.0, "Answer mismatch", problem.answer_discussion
```

### 4. Optional: Setup Problem Files

If your workflow needs input files, implement `setup_problem`:

```python
async def setup_problem(self, problem, problem_data_dir, container_name):
    # Create files the agent will need
    (problem_data_dir / "input.txt").write_text("Input data here")
```

### 5. Register Your Benchmark

The benchmark should be automatically discoverable. To use it:

```python
from base_agent.src.benchmarks.my_benchmark import MyBenchmark

benchmark = MyBenchmark()
# Run with your agent
```

## Common Patterns

### Pattern 1: Exact Match Scoring
```python
score = 1.0 if submitted == expected else 0.0
```

### Pattern 2: Numeric with Tolerance
```python
if abs(float(submitted) - expected) < 1e-6:
    score = 1.0
```

### Pattern 3: File Output Checking
```python
output_file = Path(agent_workdir) / "result.txt"
if output_file.exists():
    content = output_file.read_text()
    # Check content
```

### Pattern 4: Code Execution Testing
```python
# Execute code and check results
# (requires running commands in container)
```

### Pattern 5: Partial Credit
```python
score = 0.0
if condition1:
    score += 0.5
if condition2:
    score += 0.5
return score, None, discussion
```

## Data Sources

Load problems from various sources:

### JSONL File
```python
with open("problems.jsonl") as f:
    for line in f:
        data = json.loads(line)
        problems.append(Problem(...))
```

### HuggingFace Dataset
```python
from datasets import load_dataset
dataset = load_dataset("org/dataset")
problems = [Problem(...) for item in dataset["test"]]
```

### CSV File
```python
import csv
with open("problems.csv") as f:
    reader = csv.DictReader(f)
    problems = [Problem(
        problem_id=row["id"],
        statement=row["question"],
        answer=row["answer"]
    ) for row in reader]
```

### Programmatic Generation
```python
problems = [
    Problem(
        problem_id=f"problem_{i}",
        statement=f"Solve task {i}",
        answer=compute_answer(i)
    ) for i in range(100)
]
```

## Testing Your Benchmark

Create a simple test:

```python
# tests/benchmarks/test_my_benchmark.py
import pytest
from base_agent.src.benchmarks.my_benchmark import MyBenchmark

def test_benchmark_creation():
    benchmark = MyBenchmark()
    assert len(benchmark.problems) > 0
    assert benchmark.name == "my_benchmark"

@pytest.mark.asyncio
async def test_scoring():
    benchmark = MyBenchmark()
    problem = benchmark.problems[0]
    
    # Create mock answer file
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        answer_dir = Path(tmpdir)
        (answer_dir / "answer.txt").write_text("expected_answer")
        
        score, error, discussion = await benchmark.score_problem(
            problem, tmpdir, str(answer_dir), "test_container"
        )
        
        assert score >= 0.0 and score <= 1.0
```

## Running Your Benchmark

```bash
# Run from project root
python runner.py --benchmark my_benchmark --subset-size 5
```

## Advanced Features

### Custom Timeout Settings
Override in your benchmark if needed

### Container Command Execution
Use Docker API to run commands in the agent container for verification

### Multi-file Output
Check multiple output files in `agent_workdir`

### Streaming Evaluation
For long-running tasks, implement intermediate checkpoints

### Partial Observability
Give the agent only partial information, test information gathering

## Examples in Codebase

Study these existing benchmarks for reference:
- `gsm8k.py` - Simple numeric answer evaluation
- `humaneval.py` - Code generation and execution testing
- `file_editing.py` - File manipulation tasks
- `swebench_verified.py` - Complex software engineering tasks

## Next Steps

1. Create your benchmark file in `base_agent/src/benchmarks/`
2. Implement the required methods
3. Create test problems/data
4. Write unit tests
5. Run with a small subset to validate
6. Scale up to full benchmark

For more help, check:
- [base.py](base_agent/src/benchmarks/base.py) - Base class definition
- [custom_example.py](base_agent/src/benchmarks/custom_example.py) - Detailed examples
- Existing benchmark implementations

Happy benchmarking!

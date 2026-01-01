# Quick Reference: Creating Custom Benchmarks

This is a condensed quick-reference guide for creating benchmarks. For detailed explanations and examples, see [CREATING_CUSTOM_BENCHMARKS.md](CREATING_CUSTOM_BENCHMARKS.md).

## Minimal Benchmark Template

```python
# base_agent/src/benchmarks/my_benchmark.py
from pathlib import Path
from typing import ClassVar
from .base import BaseBenchmark, Problem

class MyBenchmark(BaseBenchmark):
    name: ClassVar[str] = "my_benchmark"
    
    def __init__(self, seed: int | None = None, subset_size: int | None = None):
        super().__init__(seed, subset_size)
        self._problems = [
            Problem(
                problem_id="task1",
                statement="Your task description here",
                answer="expected_answer",
                answer_discussion="Optional explanation"
            ),
        ]
    
    @property
    def problems(self) -> list[Problem]:
        return self._problems
    
    async def setup_problem(self, problem: Problem, problem_data_dir: Path, container_name: str) -> None:
        """Optional: Create test files/environment before each problem."""
        pass
    
    async def score_problem(
        self, problem: Problem, agent_workdir: str, 
        agent_answer_dir: str, container_name: str
    ) -> tuple[float, str | None, str | None]:
        """Score the agent's solution. Return (score, error_msg, discussion)."""
        answer_path = Path(agent_answer_dir) / "answer.txt"
        agent_answer = answer_path.read_text().strip()
        
        if agent_answer == problem.answer:
            return 1.0, None, problem.answer_discussion
        return 0.0, "Incorrect answer", problem.answer_discussion
```

## Registration Checklist

1. **Import** your benchmark in `base_agent/src/benchmarks/__init__.py`:
   ```python
   from .my_benchmark import MyBenchmark
   ```

2. **Register** in the `benchmark_registry`:
   ```python
   benchmark_registry: OrderedDict[str, Type[BaseBenchmark]] = OrderedDict([
       # ... existing benchmarks
       # (MyBenchmark.name, MyBenchmark),  # Uncomment to enable
   ])
   ```

3. **Create tests** in `base_agent/tests/benchmarks/test_my_benchmark.py`

## Common Patterns

### Problem with File Setup
```python
async def setup_problem(self, problem: Problem, problem_data_dir: Path, container_name: str) -> None:
    # Create test files
    (problem_data_dir / "input.txt").write_text("test data")
    
    # Create JSON data
    import json
    data = {"key": "value"}
    (problem_data_dir / "data.json").write_text(json.dumps(data))
```

### Partial Scoring
```python
async def score_problem(self, problem, agent_workdir, agent_answer_dir, container_name):
    score = 0.0
    errors = []
    
    # Check criterion 1 (30% of score)
    if check_criterion_1():
        score += 0.3
    else:
        errors.append("Criterion 1 failed")
    
    # Check criterion 2 (70% of score)
    if check_criterion_2():
        score += 0.7
    else:
        errors.append("Criterion 2 failed")
    
    error_msg = "; ".join(errors) if errors else None
    return score, error_msg, problem.answer_discussion
```

### File Validation
```python
async def score_problem(self, problem, agent_workdir, agent_answer_dir, container_name):
    output_path = Path(agent_workdir) / "output.json"
    
    if not output_path.exists():
        return 0.0, "Output file not found", None
    
    try:
        import json
        data = json.loads(output_path.read_text())
        # Validate structure
        if validate_data(data):
            return 1.0, None, problem.answer_discussion
        else:
            return 0.5, "Invalid data structure", problem.answer_discussion
    except json.JSONDecodeError as e:
        return 0.0, f"Invalid JSON: {e}", problem.answer_discussion
```

## Testing Commands

```bash
# Test your benchmark
python -m pytest base_agent/tests/benchmarks/test_my_benchmark.py -v

# Quick import test
python -c "from base_agent.src.benchmarks.my_benchmark import MyBenchmark; print(MyBenchmark().name)"

# Run with the agent (in Docker container)
python runner.py --id test --benchmarks my_benchmark
```

## Key Points

1. **Problem Statement**: Be clear and specific. Include expected output format.
2. **Scoring**: Return a float between 0.0 and 1.0
3. **Error Messages**: Provide helpful feedback for debugging
4. **Setup**: Use `setup_problem` for file/environment preparation
5. **Answer File**: Agent should write final answer to `answer.txt` in `agent_answer_dir`
6. **Work Directory**: `agent_workdir` is where the agent can create files (mounted to `/home/agent/workdir` in container)

## File Locations

- Benchmark implementation: `base_agent/src/benchmarks/my_benchmark.py`
- Tests: `base_agent/tests/benchmarks/test_my_benchmark.py`
- Registration: `base_agent/src/benchmarks/__init__.py`
- Data files (if needed): `benchmark_data/my_benchmark/`

## Example Benchmarks to Study

- **Simple**: `gsm8k.py` - Math problems with numeric answers
- **File-based**: `file_editing.py` - Complex setup with git repositories
- **Data Transform**: `data_transform.py` - Example from tutorial

## Need Help?

See the full tutorial: [CREATING_CUSTOM_BENCHMARKS.md](CREATING_CUSTOM_BENCHMARKS.md)

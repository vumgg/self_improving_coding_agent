# Creating Custom Benchmarks for Your Workflow

This guide will teach you how to create a custom benchmark for your specific workflow in the Self-Improving Coding Agent system.

## Table of Contents

1. [Overview](#overview)
2. [Understanding the Benchmark Architecture](#understanding-the-benchmark-architecture)
3. [Quick Start: Simple Benchmark](#quick-start-simple-benchmark)
4. [Advanced: Benchmark with Setup](#advanced-benchmark-with-setup)
5. [Registering Your Benchmark](#registering-your-benchmark)
6. [Testing Your Benchmark](#testing-your-benchmark)
7. [Best Practices](#best-practices)

## Overview

Benchmarks in this system are used to evaluate the agent's performance on specific tasks. Each benchmark:
- Defines a set of problems for the agent to solve
- Provides problem-specific setup (optional)
- Scores the agent's solution
- Tracks results for analysis

## Understanding the Benchmark Architecture

All benchmarks inherit from `BaseBenchmark` (in `base_agent/src/benchmarks/base.py`) and must implement:

### Required Components

1. **`name`** (ClassVar[str]): Unique identifier for your benchmark
2. **`problems`** (property): Returns a list of `Problem` objects
3. **`score_problem`** (async method): Evaluates the agent's solution

### Optional Components

1. **`setup_problem`** (async method): Prepares the environment before each problem
2. **`get_problem`** (method): Retrieves a specific problem by ID (default implementation provided)

### The Problem Class

Each problem consists of:
- `problem_id`: Unique identifier for the problem
- `statement`: The task description given to the agent
- `answer`: The expected answer or solution
- `answer_discussion`: Optional additional context or explanation

## Quick Start: Simple Benchmark

Let's create a simple benchmark that tests the agent's ability to perform data transformations.

### Step 1: Create Your Benchmark File

Create a new file `base_agent/src/benchmarks/data_transform.py`:

```python
# Self-Improving Coding Agent
# Copyright (c) 2025 Maxime Robeyns
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json
import logging
from pathlib import Path
from typing import ClassVar

from .base import BaseBenchmark, Problem

logger = logging.getLogger(__name__)


class DataTransformBenchmark(BaseBenchmark):
    """Benchmark for testing data transformation capabilities."""
    
    name: ClassVar[str] = "data_transform"
    
    def __init__(self, seed: int | None = None, subset_size: int | None = None):
        super().__init__(seed, subset_size)
        
        # Define your problems directly in code for simple benchmarks
        self._problems = [
            Problem(
                problem_id="csv_to_json",
                statement=(
                    "You are given a CSV file at 'input.csv' with columns: name, age, city.\n"
                    "Convert it to a JSON file called 'output.json' with the same data.\n"
                    "Each row should be an object in a JSON array.\n\n"
                    "When done, write 'COMPLETED' to answer.txt"
                ),
                answer="COMPLETED",
                answer_discussion="Should convert CSV to JSON array format"
            ),
            Problem(
                problem_id="filter_data",
                statement=(
                    "You are given a JSON file at 'data.json' containing a list of users.\n"
                    "Filter out all users where age < 18 and save to 'filtered.json'.\n\n"
                    "When done, write 'COMPLETED' to answer.txt"
                ),
                answer="COMPLETED",
                answer_discussion="Should filter users by age >= 18"
            ),
            Problem(
                problem_id="aggregate_sum",
                statement=(
                    "You are given a JSON file at 'transactions.json' with transactions.\n"
                    "Each transaction has an 'amount' field.\n"
                    "Calculate the total sum of all amounts and write just the number to answer.txt"
                ),
                answer=250.75,  # Expected sum
                answer_discussion="Sum of all transaction amounts"
            ),
        ]
    
    @property
    def problems(self) -> list[Problem]:
        return self._problems
    
    async def setup_problem(
        self, 
        problem: Problem, 
        problem_data_dir: Path, 
        container_name: str
    ) -> None:
        """Create test data files for each problem."""
        
        if problem.problem_id == "csv_to_json":
            # Create sample CSV file
            csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago"
            (problem_data_dir / "input.csv").write_text(csv_content)
            
        elif problem.problem_id == "filter_data":
            # Create sample JSON with users
            data = [
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 17},
                {"name": "Charlie", "age": 30},
                {"name": "David", "age": 16},
            ]
            (problem_data_dir / "data.json").write_text(json.dumps(data, indent=2))
            
        elif problem.problem_id == "aggregate_sum":
            # Create sample transactions
            transactions = [
                {"id": 1, "amount": 50.25},
                {"id": 2, "amount": 100.00},
                {"id": 3, "amount": 75.50},
                {"id": 4, "amount": 25.00},
            ]
            (problem_data_dir / "transactions.json").write_text(
                json.dumps(transactions, indent=2)
            )
    
    async def score_problem(
        self,
        problem: Problem,
        agent_workdir: str,
        agent_answer_dir: str,
        container_name: str,
    ) -> tuple[float, str | None, str | None]:
        """Score the agent's solution."""
        
        try:
            # Get the submitted answer
            answer_path = Path(agent_answer_dir) / "answer.txt"
            if not answer_path.exists():
                return 0.0, "No answer.txt file found", problem.answer_discussion
            
            agent_answer = answer_path.read_text().strip()
            
            # Problem-specific scoring
            if problem.problem_id == "csv_to_json":
                output_path = Path(agent_workdir) / "output.json"
                if not output_path.exists():
                    return 0.0, "output.json not found", problem.answer_discussion
                
                try:
                    output_data = json.loads(output_path.read_text())
                    # Check if it's a list with 3 items (our CSV had 3 rows)
                    if isinstance(output_data, list) and len(output_data) == 3:
                        # Check if all required fields are present
                        required_fields = {"name", "age", "city"}
                        if all(required_fields.issubset(item.keys()) for item in output_data):
                            return 1.0, None, problem.answer_discussion
                        else:
                            return 0.5, "Missing required fields", problem.answer_discussion
                    else:
                        return 0.3, "Incorrect data structure", problem.answer_discussion
                except json.JSONDecodeError:
                    return 0.0, "Invalid JSON output", problem.answer_discussion
            
            elif problem.problem_id == "filter_data":
                filtered_path = Path(agent_workdir) / "filtered.json"
                if not filtered_path.exists():
                    return 0.0, "filtered.json not found", problem.answer_discussion
                
                try:
                    filtered_data = json.loads(filtered_path.read_text())
                    # Should have 2 users (Alice: 25, Charlie: 30)
                    if len(filtered_data) == 2:
                        # Check all are 18+
                        if all(user.get("age", 0) >= 18 for user in filtered_data):
                            return 1.0, None, problem.answer_discussion
                        else:
                            return 0.5, "Some users don't meet age requirement", problem.answer_discussion
                    else:
                        return 0.3, f"Expected 2 users, got {len(filtered_data)}", problem.answer_discussion
                except json.JSONDecodeError:
                    return 0.0, "Invalid JSON output", problem.answer_discussion
            
            elif problem.problem_id == "aggregate_sum":
                try:
                    # Agent should write just the sum
                    agent_sum = float(agent_answer)
                    expected_sum = problem.answer
                    
                    # Allow small floating point errors
                    if abs(agent_sum - expected_sum) < 0.01:
                        return 1.0, None, problem.answer_discussion
                    else:
                        return 0.0, f"Expected {expected_sum}, got {agent_sum}", problem.answer_discussion
                except ValueError:
                    return 0.0, f"Could not parse answer as number: {agent_answer}", problem.answer_discussion
            
            return 0.0, "Unknown problem ID", problem.answer_discussion
            
        except Exception as e:
            logger.error(f"Error scoring problem {problem.problem_id}: {e}")
            return 0.0, str(e), problem.answer_discussion
```

### Step 2: Add Tests for Your Benchmark

Create `base_agent/tests/benchmarks/test_data_transform.py`:

```python
# Self-Improving Coding Agent
# Copyright (c) 2025 Maxime Robeyns
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json
import pytest
import tempfile
from pathlib import Path

from src.benchmarks.data_transform import DataTransformBenchmark


def test_benchmark_initialization():
    """Test that the benchmark initializes correctly."""
    benchmark = DataTransformBenchmark()
    
    assert benchmark.name == "data_transform"
    assert len(benchmark.problems) == 3
    
    # Check problem IDs
    problem_ids = [p.problem_id for p in benchmark.problems]
    assert "csv_to_json" in problem_ids
    assert "filter_data" in problem_ids
    assert "aggregate_sum" in problem_ids


@pytest.mark.asyncio
async def test_setup_csv_to_json():
    """Test setup for CSV to JSON problem."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[0]  # csv_to_json
    
    with tempfile.TemporaryDirectory() as tmpdir:
        problem_dir = Path(tmpdir)
        await benchmark.setup_problem(problem, problem_dir, "test_container")
        
        # Check that input.csv was created
        csv_path = problem_dir / "input.csv"
        assert csv_path.exists()
        
        content = csv_path.read_text()
        assert "name,age,city" in content
        assert "Alice" in content


@pytest.mark.asyncio
async def test_score_aggregate_sum_correct():
    """Test scoring for correct aggregate sum answer."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[2]  # aggregate_sum
    
    with tempfile.TemporaryDirectory() as tmpdir:
        answer_dir = Path(tmpdir) / "answer"
        answer_dir.mkdir()
        
        # Write correct answer
        (answer_dir / "answer.txt").write_text("250.75")
        
        score, error, discussion = await benchmark.score_problem(
            problem,
            agent_workdir=str(tmpdir),
            agent_answer_dir=str(answer_dir),
            container_name="test"
        )
        
        assert score == 1.0
        assert error is None


@pytest.mark.asyncio
async def test_score_aggregate_sum_incorrect():
    """Test scoring for incorrect aggregate sum answer."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[2]  # aggregate_sum
    
    with tempfile.TemporaryDirectory() as tmpdir:
        answer_dir = Path(tmpdir) / "answer"
        answer_dir.mkdir()
        
        # Write incorrect answer
        (answer_dir / "answer.txt").write_text("999.99")
        
        score, error, discussion = await benchmark.score_problem(
            problem,
            agent_workdir=str(tmpdir),
            agent_answer_dir=str(answer_dir),
            container_name="test"
        )
        
        assert score == 0.0
        assert error is not None
```

## Advanced: Benchmark with Setup

For more complex benchmarks that require substantial setup (like cloning repositories, creating complex environments, etc.), see the `FileEditingBenchmark` example in `base_agent/src/benchmarks/file_editing.py`.

Key patterns for advanced benchmarks:

### Loading Problems from External Sources

```python
@property
def problems(self) -> list[Problem]:
    """Lazy-load problems from external dataset."""
    if self._problems is None:
        self._load_problems()
    return self._problems

def _load_problems(self) -> None:
    """Load problems from a dataset file or API."""
    dataset_path = Path(__file__).parents[3] / "benchmark_data" / "my_benchmark" / "data.json"
    
    with open(dataset_path) as f:
        data = json.load(f)
    
    self._problems = [
        Problem(
            problem_id=item["id"],
            statement=item["description"],
            answer=item["expected_output"],
            answer_discussion=item.get("notes")
        )
        for item in data
    ]
```

### Complex Problem Setup

```python
async def setup_problem(
    self, 
    problem: Problem, 
    problem_data_dir: Path, 
    container_name: str
) -> None:
    """Setup complex environment for the problem."""
    
    # Example: Clone a repository
    import subprocess
    
    if hasattr(problem, 'repo_url'):
        subprocess.run(
            ["git", "clone", problem.repo_url, str(problem_data_dir / "repo")],
            check=True,
            capture_output=True
        )
    
    # Example: Generate test files
    for filename, content in problem.test_files.items():
        file_path = problem_data_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    
    # Example: Run setup commands in container
    subprocess.run(
        ["docker", "exec", container_name, "pip", "install", "-r", "requirements.txt"],
        cwd=str(problem_data_dir),
        check=False  # Don't fail if requirements don't exist
    )
```

### Partial Scoring

```python
async def score_problem(
    self,
    problem: Problem,
    agent_workdir: str,
    agent_answer_dir: str,
    container_name: str,
) -> tuple[float, str | None, str | None]:
    """Score with partial credit."""
    
    score = 0.0
    issues = []
    
    # Check multiple criteria
    if self._check_criterion_1(agent_workdir):
        score += 0.3
    else:
        issues.append("Criterion 1 not met")
    
    if self._check_criterion_2(agent_workdir):
        score += 0.3
    else:
        issues.append("Criterion 2 not met")
    
    if self._check_criterion_3(agent_workdir):
        score += 0.4
    else:
        issues.append("Criterion 3 not met")
    
    error_msg = "; ".join(issues) if issues else None
    return score, error_msg, problem.answer_discussion
```

## Registering Your Benchmark

Once your benchmark is complete, register it in `base_agent/src/benchmarks/__init__.py`:

```python
# Import your benchmark
from .data_transform import DataTransformBenchmark

# Add to the benchmark registry
benchmark_registry: OrderedDict[str, Type[BaseBenchmark]] = OrderedDict(
    [
        (GSM8KBenchmark.name, GSM8KBenchmark),
        (DataTransformBenchmark.name, DataTransformBenchmark),  # Add your benchmark
        # ... other benchmarks
    ]
)
```

**Note**: Benchmarks are commented out by default. Uncomment the line to include it in benchmark runs.

## Testing Your Benchmark

### Unit Tests

Run your benchmark tests:

```bash
# From the repository root directory
python -m pytest base_agent/tests/benchmarks/test_data_transform.py -v
```

### Integration Testing

Test your benchmark with the actual agent:

```bash
# From the repository root
python -c "
from base_agent.src.benchmarks.data_transform import DataTransformBenchmark
import asyncio

async def test():
    benchmark = DataTransformBenchmark()
    print(f'Benchmark: {benchmark.name}')
    print(f'Number of problems: {len(benchmark.problems)}')
    for problem in benchmark.problems:
        print(f'  - {problem.problem_id}: {problem.statement[:50]}...')

asyncio.run(test())
"
```

### Full System Test

To run your benchmark as part of the full system:

1. Uncomment your benchmark in `base_agent/src/benchmarks/__init__.py`
2. Run the benchmark:

```bash
# Make sure you're in the Docker container or have proper setup
python runner.py --id test_run --workers 1 --benchmarks data_transform
```

## Best Practices

### 1. Problem Design

- **Clear Instructions**: Make problem statements unambiguous
- **Appropriate Difficulty**: Match the agent's capabilities
- **Verifiable Solutions**: Ensure solutions can be objectively scored
- **Self-Contained**: Problems should not depend on external state

### 2. Scoring

- **Deterministic**: Same solution should always get the same score
- **Fair**: Partial credit for partially correct solutions
- **Informative**: Error messages should help understand what went wrong
- **Fast**: Scoring should complete quickly (< 1 second ideally)

### 3. Setup

- **Idempotent**: Running setup multiple times should work correctly
- **Clean State**: Each problem should start with a clean environment
- **Efficient**: Minimize setup time when possible
- **Documented**: Complex setup should have inline comments

### 4. Code Quality

- **Type Hints**: Use type hints for all methods
- **Logging**: Add appropriate logging statements
- **Error Handling**: Handle edge cases and provide informative errors
- **Documentation**: Include docstrings for classes and methods
- **Tests**: Write comprehensive tests for your benchmark

### 5. Problem Sets

- **Representative**: Problems should represent real-world tasks
- **Diverse**: Cover different aspects of the capability being tested
- **Scalable**: Support subset_size parameter for quick testing
- **Reproducible**: Use seed parameter for consistent problem selection

### 6. Performance Considerations

- **Lazy Loading**: Load problems only when needed
- **Caching**: Cache loaded datasets to avoid repeated I/O
- **Timeout Handling**: Consider timeouts for long-running operations
- **Resource Cleanup**: Clean up temporary files and resources

## Example: Domain-Specific Benchmark

Here's an outline for a web scraping benchmark:

```python
class WebScrapingBenchmark(BaseBenchmark):
    """Benchmark for web scraping tasks."""
    
    name: ClassVar[str] = "web_scraping"
    
    def __init__(self, seed: int | None = None, subset_size: int | None = None):
        super().__init__(seed, subset_size)
        self._problems = [
            Problem(
                problem_id="extract_table",
                statement=(
                    "A file 'page.html' contains an HTML table with product data.\\n"
                    "Extract all rows and save as 'products.csv' with columns: name, price, stock.\\n"
                    "Write 'DONE' to answer.txt when complete."
                ),
                answer="DONE",
                answer_discussion="Extract HTML table to CSV"
            ),
            # More problems...
        ]
    
    @property
    def problems(self) -> list[Problem]:
        return self._problems
    
    async def setup_problem(self, problem: Problem, problem_data_dir: Path, container_name: str) -> None:
        # Create sample HTML files
        if problem.problem_id == "extract_table":
            html = """
            <html><body>
            <table>
                <tr><th>Name</th><th>Price</th><th>Stock</th></tr>
                <tr><td>Widget</td><td>$10</td><td>50</td></tr>
                <tr><td>Gadget</td><td>$20</td><td>30</td></tr>
            </table>
            </body></html>
            """
            (problem_data_dir / "page.html").write_text(html)
    
    async def score_problem(
        self, problem: Problem, agent_workdir: str, 
        agent_answer_dir: str, container_name: str
    ) -> tuple[float, str | None, str | None]:
        # Score based on CSV output quality
        csv_path = Path(agent_workdir) / "products.csv"
        if not csv_path.exists():
            return 0.0, "products.csv not found", None
        
        # Validate CSV content
        import csv
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        if len(rows) == 2 and all('name' in row for row in rows):
            return 1.0, None, problem.answer_discussion
        
        return 0.5, "Incomplete or incorrect CSV", problem.answer_discussion
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure your benchmark is properly imported in `__init__.py`
2. **Path Issues**: Use `Path(__file__).parents[3]` to get to the repository root
3. **Async Issues**: Remember that `score_problem` and `setup_problem` are async methods
4. **Container Access**: Use `container_name` parameter when you need to execute commands in the container

### Debugging Tips

- Use `logger.debug()` to add diagnostic output
- Test problems individually with unit tests first
- Check the `results/` directory for agent output and traces
- Use `--debug` flag when running the agent to see more details

## Additional Resources

- See existing benchmarks in `base_agent/src/benchmarks/` for more examples
- Check `base_agent/tests/benchmarks/` for testing patterns
- Read `base_agent/README.md` for overall system architecture
- Review `runner.py` to understand how benchmarks are executed

## Next Steps

After creating your benchmark:

1. Write comprehensive tests
2. Run the benchmark with the agent
3. Analyze the results in `results/run_<id>/`
4. Iterate on problem difficulty and scoring
5. Consider contributing your benchmark back to the community!

---

If you have questions or run into issues, please open an issue on the repository with:
- Your benchmark code
- The error message or unexpected behavior
- Steps to reproduce the problem

# Self-Improving Coding Agent
# Copyright (c) 2025 Maxime Robeyns
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
Custom Benchmark Example

This example shows how to create a benchmark for a customized workflow.
Adapt this template to your specific needs.
"""

import json
import random
import logging
from pathlib import Path
from typing import Any

from .base import BaseBenchmark, Problem

logger = logging.getLogger(__name__)


class CustomWorkflowBenchmark(BaseBenchmark):
    """
    Example benchmark for a custom workflow.
    
    This template demonstrates:
    1. Loading problems from a custom data source
    2. Implementing custom scoring logic
    3. Optional problem setup for file-based tasks
    """

    name = "custom_workflow"  # Unique identifier for your benchmark

    def __init__(
        self,
        data_path: str | Path | None = None,
        seed: int | None = None,
        subset_size: int | None = None
    ):
        """
        Initialize your custom benchmark.
        
        Args:
            data_path: Path to your custom problem data
            seed: Random seed for reproducibility
            subset_size: Number of problems to use (for testing smaller subsets)
        """
        super().__init__(seed, subset_size)
        
        # Load your problems from wherever they're stored
        if data_path is None:
            # Use default location or generate synthetic problems
            data_path = Path(__file__).parent.parent.parent.parent / "benchmark_data" / "custom_workflow"
        
        self._problems = self._load_problems(data_path)
        
        # Apply subset sampling if requested
        if subset_size is not None and subset_size < len(self._problems):
            random.seed(seed)
            self._problems = random.sample(self._problems, subset_size)

    def _load_problems(self, data_path: Path) -> list[Problem]:
        """
        Load problems from your custom data source.
        
        Options for loading data:
        1. JSON/JSONL file
        2. CSV file
        3. HuggingFace dataset
        4. Database query
        5. API call
        6. Generated programmatically
        """
        problems = []
        
        # Example 1: Load from JSONL file
        data_file = Path(data_path) / "problems.jsonl"
        if data_file.exists():
            with open(data_file, 'r') as f:
                for i, line in enumerate(f):
                    data = json.loads(line)
                    problems.append(Problem(
                        problem_id=data.get("id", str(i)),
                        statement=data["question"],
                        answer=data["expected_answer"],
                        answer_discussion=data.get("explanation", None)
                    ))
        
        # Example 2: Generate synthetic problems for demonstration
        else:
            logger.warning(f"Data file {data_file} not found, generating sample problems")
            problems = self._generate_sample_problems()
        
        return problems

    def _generate_sample_problems(self) -> list[Problem]:
        """Generate sample problems for demonstration purposes."""
        return [
            Problem(
                problem_id="demo_1",
                statement="Calculate the sum of 42 and 58. Submit only the numeric answer.",
                answer=100,
                answer_discussion="42 + 58 = 100"
            ),
            Problem(
                problem_id="demo_2",
                statement="What is the capital of France? Submit your answer as a single word.",
                answer="Paris",
                answer_discussion="The capital city of France is Paris."
            ),
            Problem(
                problem_id="demo_3",
                statement="Write a Python function called 'add_numbers' that takes two integers and returns their sum. Save it to solution.py.",
                answer="def add_numbers(a, b):\n    return a + b",
                answer_discussion="A simple function that adds two numbers."
            ),
        ]

    @property
    def problems(self) -> list[Problem]:
        """Return the list of problems in this benchmark."""
        return self._problems

    async def setup_problem(
        self,
        problem: Problem,
        problem_data_dir: Path,
        container_name: str
    ) -> None:
        """
        Optional: Set up problem-specific files before the agent runs.
        
        Use this to:
        - Create input files the agent needs to read
        - Set up a specific directory structure
        - Write configuration files
        - Prepare test data
        
        The problem_data_dir will be mounted at /home/agent/workdir in the container.
        """
        # Example: Create a test input file for the agent
        if problem.problem_id == "demo_file_task":
            input_file = problem_data_dir / "input.txt"
            input_file.write_text("Some input data for the agent to process")
            
            # Create subdirectories if needed
            (problem_data_dir / "data").mkdir(exist_ok=True)
            
        # You can also execute commands in the container if needed
        # (would require additional Docker API calls)

    async def score_problem(
        self,
        problem: Problem,
        agent_workdir: str,
        agent_answer_dir: str,
        container_name: str,
    ) -> tuple[float, str | None, str | None]:
        """
        Score the agent's answer to the problem.
        
        Args:
            problem: The problem being evaluated
            agent_workdir: Absolute path to /home/agent/workdir in the container
            agent_answer_dir: Absolute path to the log directory with answer.txt
            container_name: Name of the Docker container (for executing commands)
        
        Returns:
            tuple of (score, error_message, discussion):
            - score: 0.0 to 1.0 (can be partial credit)
            - error_message: None if no errors, otherwise error description
            - discussion: Additional context about the answer
        """
        try:
            # Read the agent's submitted answer
            answer_path = Path(agent_answer_dir) / "answer.txt"
            
            if not answer_path.exists():
                return 0.0, "No answer.txt file found", None
            
            submitted_answer = answer_path.read_text().strip()
            
            # Option 1: Exact match scoring
            if isinstance(problem.answer, str):
                score = 1.0 if submitted_answer.lower() == problem.answer.lower() else 0.0
                return score, None, problem.answer_discussion
            
            # Option 2: Numeric comparison with tolerance
            elif isinstance(problem.answer, (int, float)):
                try:
                    submitted_value = float(submitted_answer.replace(",", ""))
                    if abs(submitted_value - problem.answer) < 1e-6:
                        return 1.0, None, problem.answer_discussion
                    else:
                        error = f"Expected {problem.answer}, got {submitted_value}"
                        return 0.0, error, problem.answer_discussion
                except ValueError as e:
                    return 0.0, f"Could not parse numeric answer: {e}", None
            
            # Option 3: Check for a file output (e.g., code file)
            elif problem.problem_id == "demo_3":
                solution_file = Path(agent_workdir) / "solution.py"
                if not solution_file.exists():
                    return 0.0, "solution.py not found", None
                
                code = solution_file.read_text()
                
                # Basic checks
                if "def add_numbers" in code and "return" in code:
                    # Could run more sophisticated tests here
                    # e.g., import and test the function
                    return 1.0, None, "Function found and appears correct"
                else:
                    return 0.0, "Function definition incomplete", None
            
            # Default: No match
            return 0.0, "Unexpected answer format", None
            
        except Exception as e:
            logger.error(f"Error scoring problem {problem.problem_id}: {e}")
            return 0.0, str(e), None

    def get_problem(self, problem_id: str) -> Problem | None:
        """
        Optional: Override for more efficient problem lookup.
        
        Default implementation does linear search, but you can optimize
        if you have many problems (e.g., use a dictionary).
        """
        # Default implementation from base class works fine for most cases
        return super().get_problem(problem_id)


# Alternative: More complex example with file-based evaluation
class FileProcessingBenchmark(BaseBenchmark):
    """
    Example benchmark where the agent must process files and produce output files.
    """
    
    name = "file_processing"
    
    def __init__(self, seed: int | None = None, subset_size: int | None = None):
        super().__init__(seed, subset_size)
        self._problems = [
            Problem(
                problem_id="csv_processing",
                statement="Read data.csv, calculate the average of the 'value' column, and save the result to output.txt",
                answer=42.5,  # Expected average
                answer_discussion="The average should be calculated from all valid numeric values"
            )
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
        """Create input files for the agent."""
        if problem.problem_id == "csv_processing":
            csv_content = "name,value\nA,40\nB,45\nC,42.5"
            (problem_data_dir / "data.csv").write_text(csv_content)
    
    async def score_problem(
        self,
        problem: Problem,
        agent_workdir: str,
        agent_answer_dir: str,
        container_name: str,
    ) -> tuple[float, str | None, str | None]:
        """Check the output file produced by the agent."""
        try:
            output_file = Path(agent_workdir) / "output.txt"
            if not output_file.exists():
                return 0.0, "output.txt not found", None
            
            result = float(output_file.read_text().strip())
            
            if abs(result - problem.answer) < 0.01:
                return 1.0, None, problem.answer_discussion
            else:
                return 0.0, f"Expected {problem.answer}, got {result}", None
                
        except Exception as e:
            return 0.0, str(e), None

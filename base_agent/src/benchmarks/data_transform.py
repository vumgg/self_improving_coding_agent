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
    """Benchmark for testing data transformation capabilities.
    
    This is an example benchmark that demonstrates the basic structure
    and patterns for creating custom benchmarks. It tests the agent's
    ability to perform common data transformation tasks like CSV/JSON
    conversion, filtering, and aggregation.
    """
    
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

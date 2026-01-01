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
async def test_setup_filter_data():
    """Test setup for filter data problem."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[1]  # filter_data
    
    with tempfile.TemporaryDirectory() as tmpdir:
        problem_dir = Path(tmpdir)
        await benchmark.setup_problem(problem, problem_dir, "test_container")
        
        # Check that data.json was created
        json_path = problem_dir / "data.json"
        assert json_path.exists()
        
        data = json.loads(json_path.read_text())
        assert len(data) == 4
        assert any(user["age"] < 18 for user in data)  # Should have minors


@pytest.mark.asyncio
async def test_setup_aggregate_sum():
    """Test setup for aggregate sum problem."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[2]  # aggregate_sum
    
    with tempfile.TemporaryDirectory() as tmpdir:
        problem_dir = Path(tmpdir)
        await benchmark.setup_problem(problem, problem_dir, "test_container")
        
        # Check that transactions.json was created
        json_path = problem_dir / "transactions.json"
        assert json_path.exists()
        
        transactions = json.loads(json_path.read_text())
        assert len(transactions) == 4
        total = sum(t["amount"] for t in transactions)
        assert abs(total - 250.75) < 0.01


@pytest.mark.asyncio
async def test_score_csv_to_json_correct():
    """Test scoring for correct CSV to JSON conversion."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[0]  # csv_to_json
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir) / "work"
        workdir.mkdir()
        answer_dir = Path(tmpdir) / "answer"
        answer_dir.mkdir()
        
        # Create correct output
        output_data = [
            {"name": "Alice", "age": "30", "city": "NYC"},
            {"name": "Bob", "age": "25", "city": "LA"},
            {"name": "Charlie", "age": "35", "city": "Chicago"}
        ]
        (workdir / "output.json").write_text(json.dumps(output_data))
        (answer_dir / "answer.txt").write_text("COMPLETED")
        
        score, error, discussion = await benchmark.score_problem(
            problem,
            agent_workdir=str(workdir),
            agent_answer_dir=str(answer_dir),
            container_name="test"
        )
        
        assert score == 1.0
        assert error is None


@pytest.mark.asyncio
async def test_score_csv_to_json_missing_file():
    """Test scoring when output file is missing."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[0]  # csv_to_json
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir) / "work"
        workdir.mkdir()
        answer_dir = Path(tmpdir) / "answer"
        answer_dir.mkdir()
        
        (answer_dir / "answer.txt").write_text("COMPLETED")
        
        score, error, discussion = await benchmark.score_problem(
            problem,
            agent_workdir=str(workdir),
            agent_answer_dir=str(answer_dir),
            container_name="test"
        )
        
        assert score == 0.0
        assert "not found" in error


@pytest.mark.asyncio
async def test_score_filter_data_correct():
    """Test scoring for correct data filtering."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[1]  # filter_data
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir) / "work"
        workdir.mkdir()
        answer_dir = Path(tmpdir) / "answer"
        answer_dir.mkdir()
        
        # Create correct filtered output (only users >= 18)
        filtered_data = [
            {"name": "Alice", "age": 25},
            {"name": "Charlie", "age": 30},
        ]
        (workdir / "filtered.json").write_text(json.dumps(filtered_data))
        (answer_dir / "answer.txt").write_text("COMPLETED")
        
        score, error, discussion = await benchmark.score_problem(
            problem,
            agent_workdir=str(workdir),
            agent_answer_dir=str(answer_dir),
            container_name="test"
        )
        
        assert score == 1.0
        assert error is None


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


@pytest.mark.asyncio
async def test_score_no_answer_file():
    """Test scoring when answer.txt is missing."""
    benchmark = DataTransformBenchmark()
    problem = benchmark.problems[0]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        answer_dir = Path(tmpdir) / "answer"
        answer_dir.mkdir()
        
        # Don't create answer.txt
        
        score, error, discussion = await benchmark.score_problem(
            problem,
            agent_workdir=str(tmpdir),
            agent_answer_dir=str(answer_dir),
            container_name="test"
        )
        
        assert score == 0.0
        assert "answer.txt" in error.lower()

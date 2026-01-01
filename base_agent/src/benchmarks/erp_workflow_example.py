# Self-Improving Coding Agent
# Copyright (c) 2025 Maxime Robeyns
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""
ERP System Workflow Benchmark Example

This example demonstrates how to create benchmarks for tasks that involve
interacting with external systems like ERP platforms (Odoo, SAP, Oracle, etc.)
where the agent needs to:
- Access an ERP system via API or database
- Modify entities (sales orders, invoices, customers, etc.)
- Verify changes were made correctly
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from .base import BaseBenchmark, Problem

logger = logging.getLogger(__name__)


# Example: Mock ERP client (replace with your actual ERP SDK/API)
class ERPClient:
    """
    Mock ERP client - replace this with your actual ERP system client.
    Examples: Odoo's xmlrpc, SAP's REST API, custom database access, etc.
    """
    
    def __init__(self, base_url: str, api_key: str, database: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.database = database
        # In real implementation: initialize your ERP connection
    
    async def get_sale_order(self, order_id: str) -> dict:
        """Retrieve a sale order from the ERP system."""
        # Mock implementation - replace with actual API call
        # Example for Odoo:
        # return self.odoo_client.execute_kw(
        #     'sale.order', 'read', [[order_id]], 
        #     {'fields': ['name', 'partner_id', 'amount_total', 'state']}
        # )
        return {
            "id": order_id,
            "name": f"SO{order_id}",
            "partner_id": "CUSTOMER001",
            "amount_total": 1000.0,
            "state": "draft"
        }
    
    async def update_sale_order(self, order_id: str, values: dict) -> bool:
        """Update a sale order."""
        # Mock - replace with actual update
        logger.info(f"Updating order {order_id} with {values}")
        return True
    
    async def get_invoice(self, invoice_id: str) -> dict:
        """Retrieve an invoice."""
        return {
            "id": invoice_id,
            "number": f"INV{invoice_id}",
            "amount": 1500.0,
            "state": "draft",
            "due_date": "2026-02-01"
        }
    
    async def update_invoice(self, invoice_id: str, values: dict) -> bool:
        """Update an invoice."""
        logger.info(f"Updating invoice {invoice_id} with {values}")
        return True
    
    async def create_entity(self, model: str, values: dict) -> str:
        """Create a new entity and return its ID."""
        logger.info(f"Creating {model} with {values}")
        return "NEW123"
    
    async def search_entities(self, model: str, domain: list) -> list[dict]:
        """Search for entities matching criteria."""
        return []


@dataclass
class ERPProblem(Problem):
    """Extended Problem class for ERP tasks."""
    
    entity_type: str = None  # 'sale_order', 'invoice', 'customer', etc.
    entity_id: str = None    # ID of the entity to work with
    initial_state: dict = None  # Initial state of the entity
    expected_changes: dict = None  # Expected changes to verify
    verification_query: str = None  # Custom verification logic


class ERPWorkflowBenchmark(BaseBenchmark):
    """
    Benchmark for ERP system interaction workflows.
    
    The agent will receive:
    1. API credentials/connection info in the working directory
    2. Problem description of what to change
    3. Access to the ERP system (via API, SDK, or database)
    
    Scoring involves:
    - Checking if the correct entity was modified
    - Verifying all required changes were made
    - Ensuring no unintended side effects
    """
    
    name = "erp_workflow"
    
    def __init__(
        self,
        erp_url: str = "http://localhost:8069",  # Your ERP system URL
        api_key: str = None,
        database: str = "test_db",
        seed: int | None = None,
        subset_size: int | None = None
    ):
        super().__init__(seed, subset_size)
        
        # Initialize ERP connection
        self.erp_client = ERPClient(erp_url, api_key or "test_key", database)
        
        # Load or generate test problems
        self._problems = self._create_problems()
    
    def _create_problems(self) -> list[ERPProblem]:
        """Create ERP-specific test problems."""
        return [
            # Problem 1: Update sale order discount
            ERPProblem(
                problem_id="update_discount_001",
                statement="""
Access the ERP system using the credentials in erp_config.json.
Find the sale order SO001 and apply a 10% discount to all line items.
The order should remain in 'draft' state.
Submit 'DONE' when complete.
                """.strip(),
                answer="DONE",
                answer_discussion="Applied 10% discount to all line items",
                entity_type="sale_order",
                entity_id="SO001",
                initial_state={"discount": 0.0, "state": "draft"},
                expected_changes={"discount": 10.0, "state": "draft"}
            ),
            
            # Problem 2: Confirm and validate invoice
            ERPProblem(
                problem_id="confirm_invoice_002",
                statement="""
Access the ERP system and locate invoice INV002.
Validate the invoice totals match the related sale order.
If correct, move the invoice to 'posted' state.
Submit 'COMPLETED' when done.
                """.strip(),
                answer="COMPLETED",
                answer_discussion="Invoice validated and posted",
                entity_type="invoice",
                entity_id="INV002",
                initial_state={"state": "draft"},
                expected_changes={"state": "posted"}
            ),
            
            # Problem 3: Update customer credit limit
            ERPProblem(
                problem_id="update_credit_003",
                statement="""
Find customer with ID CUST003 in the ERP system.
Update their credit limit to 50000.00 based on the approval 
document in approvals/credit_approval_003.pdf.
Submit 'UPDATED' when complete.
                """.strip(),
                answer="UPDATED",
                answer_discussion="Credit limit updated based on approval",
                entity_type="customer",
                entity_id="CUST003",
                expected_changes={"credit_limit": 50000.00}
            ),
            
            # Problem 4: Create new sale order
            ERPProblem(
                problem_id="create_order_004",
                statement="""
Create a new sale order for customer CUST001 with the items 
listed in requirements.txt. Use current date and standard pricing.
Submit the new order ID when complete.
                """.strip(),
                answer="SO_NEW",  # Will be dynamic
                answer_discussion="New sale order created successfully",
                entity_type="sale_order",
                entity_id=None,  # Will be created
                expected_changes={"state": "draft", "partner_id": "CUST001"}
            ),
            
            # Problem 5: Batch update delivery dates
            ERPProblem(
                problem_id="batch_update_005",
                statement="""
Query all sale orders in 'confirmed' state with delivery date before 2026-02-01.
Update their delivery dates to 2026-03-15 due to supplier delays.
Submit the count of updated orders.
                """.strip(),
                answer="5",  # Expected number of updated orders
                answer_discussion="Updated delivery dates for delayed orders",
                entity_type="sale_order",
                verification_query="count_updated_orders"
            ),
        ]
    
    @property
    def problems(self) -> list[Problem]:
        return self._problems
    
    async def setup_problem(
        self,
        problem: ERPProblem,
        problem_data_dir: Path,
        container_name: str
    ) -> None:
        """
        Set up the problem environment:
        1. Create ERP configuration file with credentials
        2. Set up initial entity state in ERP
        3. Create any supporting files
        """
        
        # 1. Create ERP connection configuration for the agent
        erp_config = {
            "url": self.erp_client.base_url,
            "api_key": self.erp_client.api_key,
            "database": self.erp_client.database,
            "entity_type": problem.entity_type,
            "entity_id": problem.entity_id,
            # Include any SDK/library hints
            "suggested_libraries": ["requests", "odoo-rpc", "your-erp-sdk"],
            "documentation_url": "http://docs.your-erp.com/api"
        }
        
        config_file = problem_data_dir / "erp_config.json"
        config_file.write_text(json.dumps(erp_config, indent=2))
        
        # 2. Set up initial state in the ERP system
        if problem.entity_id and problem.initial_state:
            try:
                # Reset entity to known initial state
                if problem.entity_type == "sale_order":
                    await self.erp_client.update_sale_order(
                        problem.entity_id, 
                        problem.initial_state
                    )
                elif problem.entity_type == "invoice":
                    await self.erp_client.update_invoice(
                        problem.entity_id,
                        problem.initial_state
                    )
                # Add other entity types as needed
                
            except Exception as e:
                logger.error(f"Failed to set up entity state: {e}")
        
        # 3. Create supporting files if needed
        if problem.problem_id == "update_credit_003":
            # Create mock approval document
            approvals_dir = problem_data_dir / "approvals"
            approvals_dir.mkdir(exist_ok=True)
            approval_doc = approvals_dir / "credit_approval_003.pdf"
            approval_doc.write_text("APPROVED: Credit limit increase to 50000.00")
        
        elif problem.problem_id == "create_order_004":
            # Create requirements file
            requirements_file = problem_data_dir / "requirements.txt"
            requirements_file.write_text("""
Product A - Quantity: 10 - Price: 100.00
Product B - Quantity: 5 - Price: 250.00
            """.strip())
        
        # 4. Create a README with instructions (optional but helpful)
        readme = problem_data_dir / "README.md"
        readme.write_text(f"""
# ERP Task: {problem.problem_id}

## Configuration
- ERP config: `erp_config.json`
- Connection details and API credentials are provided

## Task
{problem.statement}

## Submission
Submit your answer to answer.txt when complete.
        """.strip())
    
    async def score_problem(
        self,
        problem: ERPProblem,
        agent_workdir: str,
        agent_answer_dir: str,
        container_name: str,
    ) -> tuple[float, str | None, str | None]:
        """
        Score by verifying the actual state changes in the ERP system.
        
        This is different from simple answer checking - we need to:
        1. Query the ERP system to get current state
        2. Compare against expected changes
        3. Check for any unintended modifications
        """
        
        try:
            # Read the agent's submitted answer
            answer_path = Path(agent_answer_dir) / "answer.txt"
            if not answer_path.exists():
                return 0.0, "No answer.txt file submitted", None
            
            submitted_answer = answer_path.read_text().strip()
            
            # Verify actual changes in the ERP system
            if problem.entity_type == "sale_order":
                score, error = await self._verify_sale_order_changes(
                    problem, submitted_answer
                )
            elif problem.entity_type == "invoice":
                score, error = await self._verify_invoice_changes(
                    problem, submitted_answer
                )
            elif problem.entity_type == "customer":
                score, error = await self._verify_customer_changes(
                    problem, submitted_answer
                )
            elif problem.verification_query:
                score, error = await self._verify_custom_query(
                    problem, submitted_answer
                )
            else:
                # Default: just check if answer matches expected
                score = 1.0 if submitted_answer == problem.answer else 0.0
                error = None
            
            return score, error, problem.answer_discussion
            
        except Exception as e:
            logger.error(f"Error scoring ERP problem: {e}")
            return 0.0, str(e), None
    
    async def _verify_sale_order_changes(
        self, 
        problem: ERPProblem, 
        submitted_answer: str
    ) -> tuple[float, str | None]:
        """Verify changes to a sale order."""
        
        if not problem.entity_id:
            # New order creation case
            # The submitted answer should be the new order ID
            try:
                order = await self.erp_client.get_sale_order(submitted_answer)
                if not order:
                    return 0.0, f"Order {submitted_answer} not found"
                
                # Verify expected properties
                score = 0.0
                if problem.expected_changes:
                    matches = sum(
                        1 for key, expected_value in problem.expected_changes.items()
                        if order.get(key) == expected_value
                    )
                    score = matches / len(problem.expected_changes)
                else:
                    score = 1.0
                
                return score, None if score > 0 else "Order doesn't match requirements"
                
            except Exception as e:
                return 0.0, f"Failed to verify new order: {e}"
        
        else:
            # Update existing order case
            try:
                order = await self.erp_client.get_sale_order(problem.entity_id)
                
                # Check each expected change
                if problem.expected_changes:
                    correct_changes = 0
                    total_changes = len(problem.expected_changes)
                    errors = []
                    
                    for field, expected_value in problem.expected_changes.items():
                        actual_value = order.get(field)
                        if actual_value == expected_value:
                            correct_changes += 1
                        else:
                            errors.append(
                                f"{field}: expected {expected_value}, got {actual_value}"
                            )
                    
                    score = correct_changes / total_changes
                    error = "; ".join(errors) if errors else None
                    return score, error
                
                # No specific changes to verify, just check answer matches
                if submitted_answer.upper() == problem.answer.upper():
                    return 1.0, None
                else:
                    return 0.0, f"Expected '{problem.answer}', got '{submitted_answer}'"
                    
            except Exception as e:
                return 0.0, f"Failed to query sale order: {e}"
    
    async def _verify_invoice_changes(
        self,
        problem: ERPProblem,
        submitted_answer: str
    ) -> tuple[float, str | None]:
        """Verify changes to an invoice."""
        try:
            invoice = await self.erp_client.get_invoice(problem.entity_id)
            
            if problem.expected_changes:
                score = 0.0
                errors = []
                
                for field, expected in problem.expected_changes.items():
                    actual = invoice.get(field)
                    if actual == expected:
                        score += 1.0 / len(problem.expected_changes)
                    else:
                        errors.append(f"{field}: expected {expected}, got {actual}")
                
                return score, "; ".join(errors) if errors else None
            
            return 1.0 if submitted_answer == problem.answer else 0.0, None
            
        except Exception as e:
            return 0.0, f"Failed to verify invoice: {e}"
    
    async def _verify_customer_changes(
        self,
        problem: ERPProblem,
        submitted_answer: str
    ) -> tuple[float, str | None]:
        """Verify changes to a customer record."""
        # Similar pattern to sale orders and invoices
        return 1.0 if submitted_answer == problem.answer else 0.0, None
    
    async def _verify_custom_query(
        self,
        problem: ERPProblem,
        submitted_answer: str
    ) -> tuple[float, str | None]:
        """Handle custom verification queries for complex scenarios."""
        
        if problem.verification_query == "count_updated_orders":
            # Verify batch update scenario
            # Query ERP to count orders with new delivery date
            try:
                # Mock query - replace with actual ERP query
                orders = await self.erp_client.search_entities(
                    "sale.order",
                    [("state", "=", "confirmed"), ("delivery_date", "=", "2026-03-15")]
                )
                actual_count = len(orders)
                expected_count = int(problem.answer)
                
                if actual_count == expected_count:
                    return 1.0, None
                else:
                    return 0.0, f"Expected {expected_count} updates, found {actual_count}"
                    
            except Exception as e:
                return 0.0, f"Failed to verify batch update: {e}"
        
        return 0.0, "Unknown verification query"
    
    async def cleanup_problem(
        self,
        problem: ERPProblem
    ) -> None:
        """
        Optional: Clean up or reset ERP state after problem.
        
        This is useful to:
        - Revert test changes
        - Delete test data
        - Reset entities to original state
        """
        if problem.entity_id and problem.initial_state:
            try:
                # Restore initial state
                if problem.entity_type == "sale_order":
                    await self.erp_client.update_sale_order(
                        problem.entity_id,
                        problem.initial_state
                    )
                # Add other cleanup as needed
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")


# Alternative: Database-based ERP verification
class ERPDatabaseBenchmark(BaseBenchmark):
    """
    For ERP systems where you have direct database access.
    This can be more reliable than API-based verification.
    """
    
    name = "erp_database"
    
    def __init__(self, db_connection_string: str, **kwargs):
        super().__init__(**kwargs)
        self.db_conn = db_connection_string
        # Initialize database connection (SQLAlchemy, psycopg2, etc.)
    
    @property
    def problems(self) -> list[Problem]:
        return [
            Problem(
                problem_id="db_update_001",
                statement="Update sale order SO001 discount to 15%",
                answer="DONE",
                answer_discussion="Direct database verification"
            )
        ]
    
    async def setup_problem(self, problem, problem_data_dir, container_name):
        """Provide database connection info to agent."""
        db_config = {
            "connection_string": self.db_conn,
            "readonly": False,  # Or True if you want agent to use API
            "schema": "public",
            "table": "sale_orders"
        }
        (problem_data_dir / "db_config.json").write_text(json.dumps(db_config))
    
    async def score_problem(self, problem, agent_workdir, agent_answer_dir, container_name):
        """Query database directly to verify changes."""
        # Use SQL queries to verify state
        # Example with psycopg2 or SQLAlchemy:
        # 
        # result = await db.execute(
        #     "SELECT discount FROM sale_orders WHERE id = %s",
        #     (problem.entity_id,)
        # )
        # actual_discount = result[0]['discount']
        # return 1.0 if actual_discount == 15.0 else 0.0, None, None
        
        return 1.0, None, problem.answer_discussion

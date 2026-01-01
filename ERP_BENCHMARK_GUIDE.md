# ERP System Benchmarking Guide

This guide explains how to create benchmarks for agents that interact with ERP systems (Odoo, SAP, Oracle EBS, Microsoft Dynamics, etc.).

## Key Differences from Standard Benchmarks

Unlike simple answer-checking benchmarks, ERP workflows require:

1. **External System State Management** - Set up and verify state in a live system
2. **API/Database Integration** - Connect to real ERP instances
3. **Side Effect Verification** - Check that changes were actually made
4. **Cleanup/Reset** - Return system to known state between tests

## Architecture Overview

```
┌─────────────────┐
│  Agent in       │  Reads config    ┌──────────────────┐
│  Docker         │─────────────────>│ erp_config.json  │
│  Container      │                  │ (credentials)    │
└────────┬────────┘                  └──────────────────┘
         │
         │ Makes API calls
         ↓
┌─────────────────────────────────────────────┐
│           ERP System                        │
│  (Odoo / SAP / Oracle / Dynamics / etc.)   │
│                                             │
│  ┌──────────┐  ┌─────────┐  ┌──────────┐  │
│  │ Orders   │  │Invoices │  │Customers │  │
│  └──────────┘  └─────────┘  └──────────┘  │
└────────┬────────────────────────────────────┘
         │
         │ Verifies changes
         ↓
┌─────────────────┐
│  Benchmark      │
│  Scoring        │
└─────────────────┘
```

## Implementation Steps

### 1. Choose Your Integration Method

#### Option A: API-Based (Recommended)
```python
class ERPClient:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
    
    async def get_entity(self, entity_type, entity_id):
        response = await requests.get(
            f"{self.url}/api/{entity_type}/{entity_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
```

#### Option B: Database Direct Access
```python
import asyncpg

class ERPDatabase:
    async def connect(self, dsn):
        self.conn = await asyncpg.connect(dsn)
    
    async def query_entity(self, table, id):
        return await self.conn.fetchrow(
            f"SELECT * FROM {table} WHERE id = $1", id
        )
```

#### Option C: SDK/Library (e.g., Odoo)
```python
import xmlrpc.client

class OdooClient:
    def __init__(self, url, db, username, password):
        self.common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        self.uid = self.common.authenticate(db, username, password, {})
        self.db = db
        self.password = password
    
    def read_record(self, model, record_id):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'read', [[record_id]]
        )
```

### 2. Create Your Benchmark Class

```python
from .base import BaseBenchmark, Problem
from dataclasses import dataclass

@dataclass
class ERPProblem(Problem):
    """Extended Problem with ERP-specific fields."""
    entity_type: str = None       # 'sale.order', 'invoice', etc.
    entity_id: str = None          # Specific record ID
    expected_changes: dict = None  # What should change

class MyERPBenchmark(BaseBenchmark):
    name = "my_erp_workflow"
    
    def __init__(self, erp_url, api_key, **kwargs):
        super().__init__(**kwargs)
        self.erp_client = ERPClient(erp_url, api_key)
        self._problems = self._load_problems()
```

### 3. Implement setup_problem()

Provide the agent with:
- ERP connection credentials
- Entity IDs to work with
- Supporting documents/data

```python
async def setup_problem(self, problem, problem_data_dir, container_name):
    # 1. Create config file with credentials
    config = {
        "erp_url": self.erp_client.url,
        "api_key": self.erp_client.api_key,
        "entity_id": problem.entity_id,
        "entity_type": problem.entity_type
    }
    (problem_data_dir / "erp_config.json").write_text(
        json.dumps(config, indent=2)
    )
    
    # 2. Reset entity to known initial state
    if problem.initial_state:
        await self.erp_client.update_entity(
            problem.entity_type,
            problem.entity_id,
            problem.initial_state
        )
    
    # 3. Create supporting files if needed
    if problem.needs_approval_doc:
        (problem_data_dir / "approval.pdf").write_text(
            "Approved: Credit increase"
        )
```

### 4. Implement score_problem()

Verify changes in the actual ERP system:

```python
async def score_problem(self, problem, agent_workdir, 
                       agent_answer_dir, container_name):
    # Read agent's submission
    answer_path = Path(agent_answer_dir) / "answer.txt"
    submitted = answer_path.read_text().strip()
    
    # Query ERP to get actual current state
    current_state = await self.erp_client.get_entity(
        problem.entity_type,
        problem.entity_id
    )
    
    # Verify expected changes were made
    score = 0.0
    errors = []
    
    for field, expected_value in problem.expected_changes.items():
        actual_value = current_state.get(field)
        if actual_value == expected_value:
            score += 1.0 / len(problem.expected_changes)
        else:
            errors.append(
                f"{field}: expected {expected_value}, got {actual_value}"
            )
    
    error_msg = "; ".join(errors) if errors else None
    return score, error_msg, problem.answer_discussion
```

### 5. Add Cleanup (Optional)

Reset state between problems:

```python
async def cleanup_problem(self, problem):
    """Reset ERP state after test."""
    if problem.initial_state:
        await self.erp_client.update_entity(
            problem.entity_type,
            problem.entity_id,
            problem.initial_state
        )
```

## Real-World Examples

### Example 1: Update Sale Order Discount

```python
ERPProblem(
    problem_id="discount_001",
    statement="""
    Access the ERP and apply a 10% discount to sale order SO12345.
    Ensure the order remains in 'draft' state.
    Submit 'DONE' when complete.
    """,
    answer="DONE",
    entity_type="sale.order",
    entity_id="SO12345",
    initial_state={"discount": 0.0, "state": "draft"},
    expected_changes={"discount": 10.0, "state": "draft"}
)
```

### Example 2: Confirm and Post Invoice

```python
ERPProblem(
    problem_id="invoice_002",
    statement="""
    Verify invoice INV-2026-001 totals are correct.
    If correct, change state from 'draft' to 'posted'.
    Submit the final total amount.
    """,
    answer="1500.00",
    entity_type="account.invoice",
    entity_id="INV-2026-001",
    expected_changes={"state": "posted"}
)
```

### Example 3: Batch Update Records

```python
ERPProblem(
    problem_id="batch_003",
    statement="""
    Find all orders with status 'confirmed' and 
    delivery_date before 2026-02-01.
    Update their delivery dates to 2026-03-15.
    Submit the count of updated orders.
    """,
    answer="23",  # Expected count
    verification_query="count_delivery_updates"
)
```

## Testing Strategies

### Strategy 1: Use Test/Sandbox Environment
- Set up a dedicated test ERP instance
- Pre-populate with test data
- Reset after each benchmark run

### Strategy 2: Transaction Rollback
- Wrap each problem in a database transaction
- Rollback after verification
- Requires database-level access

### Strategy 3: Record Snapshots
- Capture state before problem
- Verify changes
- Restore from snapshot

### Strategy 4: Mock ERP for Unit Tests
```python
class MockERPClient:
    def __init__(self):
        self.entities = {}
    
    async def get_entity(self, entity_type, entity_id):
        return self.entities.get(f"{entity_type}:{entity_id}")
    
    async def update_entity(self, entity_type, entity_id, values):
        key = f"{entity_type}:{entity_id}"
        self.entities[key] = {**self.entities.get(key, {}), **values}
```

## Common Patterns

### Pattern 1: CRUD Operations
```python
# Create
problem = ERPProblem(
    statement="Create customer with name 'Acme Corp'",
    answer="CUST_NEW",  # Will be the new ID
    entity_type="res.partner",
    expected_changes={"name": "Acme Corp", "customer": True}
)

# Read - verify data retrieval
# Update - modify existing record
# Delete - remove record and verify
```

### Pattern 2: Workflow State Transitions
```python
ERPProblem(
    statement="Move order through workflow: draft -> confirmed -> done",
    entity_type="sale.order",
    initial_state={"state": "draft"},
    expected_changes={"state": "done"}
)
```

### Pattern 3: Validation Logic
```python
ERPProblem(
    statement="Only post invoice if total matches sale order",
    verification_query="validate_invoice_total"
)

# In score_problem:
async def _verify_validation(self, problem):
    invoice = await self.get_invoice(problem.entity_id)
    order = await self.get_order(invoice.order_id)
    
    if invoice.total == order.total and invoice.state == "posted":
        return 1.0, None
    else:
        return 0.0, "Validation failed or incorrect state"
```

### Pattern 4: Complex Business Rules
```python
ERPProblem(
    statement="""
    Apply early payment discount if:
    - Payment received within 10 days
    - Order amount > 1000
    - Customer has good credit
    Calculate and apply 2% discount.
    """
)
```

## Security Considerations

1. **Credentials Management**
   - Never commit real credentials
   - Use environment variables
   - Consider secrets management (Vault, etc.)

2. **Access Control**
   - Use read-only API keys when possible
   - Limit permissions to test data only
   - Monitor agent actions

3. **Data Isolation**
   - Separate test environment
   - Namespaced test data (e.g., all IDs start with "TEST_")
   - Automated cleanup

4. **Rate Limiting**
   - Be aware of API rate limits
   - Implement backoff strategies
   - Cache frequently accessed data

## Performance Tips

1. **Connection Pooling**
   ```python
   # Reuse connections across problems
   self.erp_client = ERPClient()  # Initialize once
   ```

2. **Parallel Verification**
   ```python
   # Verify multiple fields concurrently
   results = await asyncio.gather(
       self.verify_field_1(),
       self.verify_field_2(),
       self.verify_field_3()
   )
   ```

3. **Caching**
   ```python
   # Cache reference data that doesn't change
   self.product_catalog = await self.erp_client.get_products()
   ```

## Debugging Tips

1. **Log All API Calls**
   ```python
   logger.info(f"Querying {entity_type} {entity_id}")
   logger.debug(f"Response: {response}")
   ```

2. **Save State Snapshots**
   ```python
   before_state = await self.get_entity_state()
   # ... agent works ...
   after_state = await self.get_entity_state()
   snapshot_file.write_text(json.dumps({
       "before": before_state,
       "after": after_state
   }))
   ```

3. **Verification Reports**
   Generate detailed reports showing:
   - What was expected
   - What was found
   - All checked fields
   - Execution logs

## Example: Complete Odoo Integration

See [erp_workflow_example.py](base_agent/src/benchmarks/erp_workflow_example.py) for a complete implementation.

For Odoo-specific integration:
```python
import xmlrpc.client

class OdooERPBenchmark(BaseBenchmark):
    def __init__(self, url, db, username, password, **kwargs):
        super().__init__(**kwargs)
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        self.uid = common.authenticate(db, username, password, {})
        self.db = db
        self.password = password
    
    def execute(self, model, method, *args):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args
        )
    
    async def score_problem(self, problem, ...):
        # Read current state from Odoo
        record = self.execute(
            'sale.order', 'read', 
            [problem.entity_id], 
            {'fields': ['discount', 'state']}
        )[0]
        
        # Verify changes
        # ...
```

## Summary Checklist

- [ ] Choose integration method (API/Database/SDK)
- [ ] Create ERP client wrapper
- [ ] Extend Problem class with ERP fields
- [ ] Implement `setup_problem()` to provide credentials
- [ ] Implement `score_problem()` to verify ERP state
- [ ] Add cleanup/reset logic
- [ ] Set up test environment
- [ ] Add logging and debugging
- [ ] Test with sample problems
- [ ] Document ERP-specific setup requirements

For more examples, see [erp_workflow_example.py](base_agent/src/benchmarks/erp_workflow_example.py)

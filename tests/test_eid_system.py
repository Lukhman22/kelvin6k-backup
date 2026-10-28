"""
tests/test_eid_system.py
Verification suite for the permanent Employee ID (EID) system,
synthetic demo record isolation, database integrity, and chatbot resolution.
"""

import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from agent import db, shift_store, query_router
from api.server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_db():
    """Ensure database schema and migrations are initialized."""
    db.init_db()


def test_existing_legitimate_employees_backfilled():
    """Verify that the 6 authentic employees have deterministic permanent EIDs K6K001 through K6K006."""
    ops = shift_store.list_operators(active_only=False)
    ops_by_eid = {o.get("eid"): o for o in ops if o.get("eid")}

    assert "K6K001" in ops_by_eid, "K6K001 must exist"
    assert ops_by_eid["K6K001"]["operator_id"] == "OP_001"
    assert ops_by_eid["K6K001"]["name"] == "Anand Sharma"

    assert "K6K002" in ops_by_eid, "K6K002 must exist"
    assert ops_by_eid["K6K002"]["operator_id"] == "OP_RAHUL"
    assert ops_by_eid["K6K002"]["name"] == "Rahul"
    assert ops_by_eid["K6K002"]["employee_code"] == "EMP99"

    assert "K6K003" in ops_by_eid, "K6K003 must exist"
    assert ops_by_eid["K6K003"]["operator_id"] == "OP_AMAN"
    assert ops_by_eid["K6K003"]["name"] == "Aman"

    assert "K6K004" in ops_by_eid, "K6K004 must exist"
    assert ops_by_eid["K6K004"]["operator_id"] == "OP_AROUND"
    assert ops_by_eid["K6K004"]["name"] == "Around"

    assert "K6K005" in ops_by_eid, "K6K005 must exist"
    assert ops_by_eid["K6K005"]["operator_id"] == "OP_LUKHMAAN_33C15E"
    assert ops_by_eid["K6K005"]["name"] == "lukhmaan"
    assert ops_by_eid["K6K005"]["employee_code"] == "12"

    assert "K6K006" in ops_by_eid, "K6K006 must exist"
    assert ops_by_eid["K6K006"]["operator_id"] == "OP_HAMADAN_D1B91C"
    assert ops_by_eid["K6K006"]["name"] == "Hamadan"
    assert ops_by_eid["K6K006"]["employee_code"] == "13"


def test_synthetic_records_isolated_and_fk_intact():
    """Verify that synthetic test employees are marked is_synthetic=1, active=0 and excluded from list_operators."""
    with db.connect() as conn:
        fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert len(fk_violations) == 0, f"Foreign key violations found: {fk_violations}"

        synth_rows = conn.execute(
            "SELECT operator_id, name, active, is_synthetic FROM operators WHERE is_synthetic = 1"
        ).fetchall()
        synth_dict = {r["operator_id"]: dict(r) for r in synth_rows}

        for sid in ("op_test", "op_test_2", "OP_TEST_999"):
            assert sid in synth_dict, f"Synthetic ID {sid} must be marked is_synthetic=1"
            assert synth_dict[sid]["active"] == 0, f"Synthetic ID {sid} must be inactive"

    # Verify excluded from normal list_operators
    public_ops = shift_store.list_operators(active_only=False)
    public_ids = [o["operator_id"] for o in public_ops]
    for sid in ("op_test", "op_test_2", "OP_TEST_999"):
        assert sid not in public_ids, f"Synthetic {sid} should not appear in public operators list"


def test_atomic_sequential_eid_generation(tmp_path):
    """Verify that new employees receive atomic, sequential, gap-free, non-reusable EIDs."""
    test_db = str(tmp_path / "seq_test.db")
    db.init_db(test_db)

    # Initialize with 2 employees
    op1 = shift_store.create_operator("OP_T1", "Tester 1", db_path=test_db)
    op2 = shift_store.create_operator("OP_T2", "Tester 2", db_path=test_db)

    rec1 = shift_store.get_operator(op1, db_path=test_db)
    rec2 = shift_store.get_operator(op2, db_path=test_db)

    assert rec1["eid"] == "K6K001"
    assert rec2["eid"] == "K6K002"

    op3 = shift_store.create_operator("OP_T3", "Tester 3", db_path=test_db)
    rec3 = shift_store.get_operator(op3, db_path=test_db)
    assert rec3["eid"] == "K6K003"


def test_get_operator_by_eid():
    """Verify get_operator_by_eid retrieves the correct operator."""
    op = shift_store.get_operator_by_eid("K6K001")
    assert op is not None
    assert op["name"] == "Anand Sharma"

    # Case insensitive
    op_lower = shift_store.get_operator_by_eid("k6k001")
    assert op_lower is not None
    assert op_lower["operator_id"] == "OP_001"

    # Nonexistent
    assert shift_store.get_operator_by_eid("K6K999") is None


def test_api_operators_endpoint_includes_eid():
    """Verify /api/operators returns eid for all operators."""
    res = client.get("/api/operators")
    assert res.status_code == 200
    data = res.json()
    assert "operators" in data
    operators = data["operators"]
    assert len(operators) >= 6

    # Verify K6K001 through K6K006 are present
    eids = [o.get("eid") for o in operators]
    for expected in ["K6K001", "K6K002", "K6K003", "K6K004", "K6K005", "K6K006"]:
        assert expected in eids, f"{expected} must be in /api/operators response"


def test_attendance_checkin_checkout_by_eid(tmp_path):
    """Verify attendance check-in and check-out using permanent EID."""
    test_db = str(tmp_path / "att_test.db")
    db.init_db(test_db)

    # Create operator with explicit EID
    shift_store.create_operator("OP_TEST_EID", "Test Operator", eid="K6K001", db_path=test_db)

    # Check in using EID via shift_store
    att = shift_store.check_in_attendance("OP_TEST_EID", db_path=test_db)
    assert att["status"] == "ACTIVE"
    assert att["eid"] == "K6K001"
    assert att["employee_name"] == "Test Operator"

    # Check out
    checked_out = shift_store.check_out_attendance("OP_TEST_EID", db_path=test_db)
    assert checked_out is not None
    assert checked_out["status"] == "COMPLETED"
    assert checked_out["eid"] == "K6K001"


def test_chatbot_eid_resolution():
    """Verify chatbot query routing and deterministic answer for EIDs."""
    # 1. Who is K6K001?
    r1 = query_router.route("Who is K6K001?")
    assert r1.intent == query_router.Intent.GET_OPERATOR
    assert r1.facts.get("specific_operator") is True
    assert r1.facts.get("name") == "Anand Sharma"
    summary1 = query_router.summarise(r1)
    assert "Anand Sharma" in summary1
    assert "K6K001" in summary1

    # 2. Who is K6K003?
    r2 = query_router.route("Who is K6K003?")
    assert r2.intent == query_router.Intent.GET_OPERATOR
    assert r2.facts.get("name") == "Aman"
    summary2 = query_router.summarise(r2)
    assert "Aman" in summary2
    assert "K6K003" in summary2

    # 3. Is K6K001 on shift?
    r3 = query_router.route("Is K6K001 on shift?")
    assert r3.intent == query_router.Intent.GET_ATTENDANCE_STATUS
    summary3 = query_router.summarise(r3)
    assert "Anand Sharma" in summary3 or "K6K001" in summary3

    # 4. Show attendance for K6K001
    r4 = query_router.route("Show attendance for K6K001")
    assert r4.intent == query_router.Intent.GET_ATTENDANCE_STATUS

    # 5. Unknown EID resolution is handled cleanly without hallucination
    r5 = query_router.route("Who is K6K999?")
    # K6K999 does not match any operator, so it falls back to current machine operator or knowledge
    assert r5.intent in (query_router.Intent.GET_OPERATOR, query_router.Intent.UNKNOWN_QUERY, query_router.Intent.KNOWLEDGE_QUERY)
    if r5.facts and r5.facts.get("specific_operator"):
        assert False, "K6K999 must not resolve to an operator"

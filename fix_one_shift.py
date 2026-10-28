import re

with open('agent/shift_store.py', 'r') as f:
    content = f.read()

old_logic = """        # Check for existing ACTIVE record
        if clean_op:
            existing = conn.execute(
                "SELECT id FROM attendance_records WHERE operator_id = ? AND status = 'ACTIVE'",
                (clean_op,)
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT id FROM attendance_records WHERE employee_name = ? AND status = 'ACTIVE'",
                (clean_name,)
            ).fetchone()
            
        if existing:
            raise ValueError(f"Employee already has an ACTIVE attendance record.")"""

new_logic = """        # Check for existing records today
        if clean_op:
            existing_active = conn.execute(
                "SELECT id FROM attendance_records WHERE operator_id = ? AND attendance_date = ? AND status = 'ACTIVE'",
                (clean_op, attendance_date)
            ).fetchone()
            existing_completed = conn.execute(
                "SELECT id FROM attendance_records WHERE operator_id = ? AND attendance_date = ? AND status = 'COMPLETED'",
                (clean_op, attendance_date)
            ).fetchone()
        else:
            existing_active = conn.execute(
                "SELECT id FROM attendance_records WHERE employee_name = ? AND attendance_date = ? AND status = 'ACTIVE'",
                (clean_name, attendance_date)
            ).fetchone()
            existing_completed = conn.execute(
                "SELECT id FROM attendance_records WHERE employee_name = ? AND attendance_date = ? AND status = 'COMPLETED'",
                (clean_name, attendance_date)
            ).fetchone()
            
        if existing_active:
            raise ValueError(f"Employee already has an ACTIVE attendance record.")
        if existing_completed:
            raise ValueError(f"Employee has already completed their shift today.")"""

content = content.replace(old_logic, new_logic)

with open('agent/shift_store.py', 'w') as f:
    f.write(content)

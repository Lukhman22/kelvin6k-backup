with open('agent/assistant.py', 'r') as f:
    text = f.read()

old_resolve = """        if spoken_name:
            op = shift_store.find_operator_by_name(spoken_name, active_only=True)
            if op:
                return op

        active = shift_store.get_active_shift_for_line(line_id)
        if active:
            return shift_store.get_operator(active["operator_id"])

        return None"""

new_resolve = """        if spoken_name:
            op = shift_store.find_operator_by_name(spoken_name, active_only=True)
            if op:
                return op

        active = shift_store.get_active_shift_for_line(line_id)
        if active:
            return shift_store.get_operator(active["operator_id"])
            
        # Check active attendance if no line shift is active
        records = shift_store.list_attendance_records()
        for r in records:
            if r["status"] == "ACTIVE":
                op = shift_store.get_operator(r["operator_id"])
                if op: return op
                return {"operator_id": r["operator_id"], "name": r["employee_name"], "active": 1}

        return None"""

text = text.replace(old_resolve, new_resolve)

with open('agent/assistant.py', 'w') as f:
    f.write(text)


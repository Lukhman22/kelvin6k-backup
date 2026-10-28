with open('agent/assistant.py', 'r') as f:
    text = f.read()

text = text.replace(
    '                shift_store.checkout_attendance_record(\n                    record_id=active["id"],\n                    operator_id=operator_id,\n                    employee_name=op_name\n                )',
    '                shift_store.checkout_attendance_record(\n                    operator_id=operator_id,\n                    employee_name=op_name\n                )'
)

with open('agent/assistant.py', 'w') as f:
    f.write(text)


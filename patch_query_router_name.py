with open('agent/query_router.py', 'r') as f:
    text = f.read()

text = text.replace(
    '        return RouterResult(intent, facts={\n            "action": "SHIFT_END",\n            "status": "closed",\n            "line_id": "line_1",\n            "requires_confirmation": True,\n',
    '        return RouterResult(intent, facts={\n            "action": "SHIFT_END",\n            "status": "closed",\n            "line_id": "line_1",\n            "spoken_name": extract_operator_name(question),\n            "requires_confirmation": True,\n'
)

with open('agent/query_router.py', 'w') as f:
    f.write(text)

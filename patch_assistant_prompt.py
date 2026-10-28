with open('agent/assistant.py', 'r') as f:
    lines = f.readlines()

out = []
skip = False
for i, line in enumerate(lines):
    if line.startswith('        if intent_val == "SHIFT_START":'):
        skip = True
        out.append('        if intent_val == "SHIFT_START":\n')
        out.append('            now = datetime.datetime.fromtimestamp(self._server_now())\n')
        out.append('            name = params.get("operator_name") or "Operator"\n')
        out.append('            if params.get("create_operator"):\n')
        out.append('                return (\n')
        out.append('                    f"New employee detected. I could not find an operator named {name}. "\n')
        out.append('                    f"Would you like to register as a new employee and start your shift?"\n')
        out.append('                )\n')
        out.append('            return f"Shall I start the shift for {name}?"\n')
        out.append('\n')
        out.append('        if intent_val == "SHIFT_END":\n')
        out.append('            name = params.get("operator_name") or "Operator"\n')
        out.append('            return f"Shall I end the shift for {name}?"\n')
        continue
    
    if skip and line.startswith('        if intent_val == "LOG_WALL_PRODUCTION":'):
        skip = False
    
    if not skip:
        out.append(line)

with open('agent/assistant.py', 'w') as f:
    f.writelines(out)


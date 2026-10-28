with open('agent/assistant.py', 'r') as f:
    text = f.read()

text = text.replace(
    '                fmt = "%Y-%m-%d %H:%M:%S"\n                start_dt = datetime.datetime.strptime(active["shift_start"], fmt)',
    '                start_dt = datetime.datetime.fromtimestamp(active["shift_start"]) if isinstance(active["shift_start"], (int, float)) else datetime.datetime.strptime(active["shift_start"], "%Y-%m-%d %H:%M:%S")'
)

with open('agent/assistant.py', 'w') as f:
    f.write(text)

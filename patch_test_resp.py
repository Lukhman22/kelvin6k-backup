with open('tests/test_voice_attendance.py', 'r') as f:
    text = f.read()
text = text.replace('resp1["text"]', 'resp1').replace('resp2["text"]', 'resp2').replace('resp3["text"]', 'resp3').replace('resp4["text"]', 'resp4').replace('resp5["text"]', 'resp5').replace('resp6["text"]', 'resp6')
with open('tests/test_voice_attendance.py', 'w') as f:
    f.write(text)

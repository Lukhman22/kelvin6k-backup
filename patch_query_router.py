import re

with open('agent/query_router.py', 'r') as f:
    content = f.read()

# Add new Intents
intent_block = '''    GET_SITE_DETECTIONS = "GET_SITE_DETECTIONS"
    GET_ATTENDANCE_HOURS = "GET_ATTENDANCE_HOURS"
    GET_ATTENDANCE_STATUS = "GET_ATTENDANCE_STATUS"
    WAKE_WORD = "WAKE_WORD"'''
content = content.replace('    GET_SITE_DETECTIONS = "GET_SITE_DETECTIONS"\n    WAKE_WORD = "WAKE_WORD"', intent_block)

# Add patterns for GET_ATTENDANCE_HOURS
hours_patterns = '''    (Intent.GET_ATTENDANCE_HOURS, [
        "how many hours have i worked", "how many hours", "hours worked today", "what's my shift status", "whats my shift status", "when did i start today", "am i clocked in", "am i currently working", "my shift status", "did i start", "hours today"
    ], 7),
    (Intent.GET_ATTENDANCE_STATUS, [
        "who is currently working", "who is on shift", "how many employees are working", "who is working", "currently working"
    ], 7),
    (Intent.SHIFT_START, ['''
content = content.replace('    (Intent.SHIFT_START, [', hours_patterns)

# Update SHIFT_START patterns
start_patterns_old = '''"start my shift", "begin my shift", "my shift start",
    ], 8),'''
start_patterns_new = '''"start my shift", "begin my shift", "my shift start", "clock me in", "mark me present", "i've started work", "ive started work", "i am starting work", "i'm starting work", "starting my shift"
    ], 8),'''
content = content.replace(start_patterns_old, start_patterns_new)

# Update SHIFT_END patterns
end_patterns_old = '''"end my shift", "close my shift", "band karo mera shift", "meri shift end karo", "meri shift khatam karo",
    ], 8),'''
end_patterns_new = '''"end my shift", "close my shift", "band karo mera shift", "meri shift end karo", "meri shift khatam karo", "i'm done for today", "im done for today", "i am done for today", "i'm finishing my shift", "clock me out", "i've finished work", "ive finished work", "stop my shift", "done for today"
    ], 8),'''
content = content.replace(end_patterns_old, end_patterns_new)

with open('agent/query_router.py', 'w') as f:
    f.write(content)

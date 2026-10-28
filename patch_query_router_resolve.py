import re

with open('agent/query_router.py', 'r') as f:
    content = f.read()

new_logic = """
    if intent == Intent.GET_ATTENDANCE_HOURS:
        try:
            records = shift_store.list_attendance_records(date_filter=time.strftime("%Y-%m-%d"))
            # Simple assumption: look for the most recently started record
            if not records:
                return RouterResult(intent, available=False, reason="No attendance records found for today.")
            
            # If the user asked "my hours", we should ideally know who they are, but for voice,
            # it might be tricky unless provided in context. 
            # We'll just return all today's records or let the summarise function handle it.
            return RouterResult(intent, facts={"records": records, "date": time.strftime("%Y-%m-%d")})
        except Exception as exc:
            log.warning("Could not resolve GET_ATTENDANCE_HOURS: %s", exc)
            return RouterResult(intent, available=False, reason="Could not fetch attendance hours.")

    if intent == Intent.GET_ATTENDANCE_STATUS:
        try:
            records = shift_store.list_attendance_records(date_filter=time.strftime("%Y-%m-%d"))
            active_records = [r for r in records if r["status"] == "ACTIVE"]
            return RouterResult(intent, facts={"active_records": active_records, "date": time.strftime("%Y-%m-%d")})
        except Exception as exc:
            log.warning("Could not resolve GET_ATTENDANCE_STATUS: %s", exc)
            return RouterResult(intent, available=False, reason="Could not fetch attendance status.")

    if intent == Intent.GET_SHIFT_BY_DATE:
"""

content = content.replace("    if intent == Intent.GET_SHIFT_BY_DATE:\n", new_logic, 1)

with open('agent/query_router.py', 'w') as f:
    f.write(content)


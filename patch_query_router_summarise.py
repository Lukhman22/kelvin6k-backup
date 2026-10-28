with open('agent/query_router.py', 'r') as f:
    content = f.read()

new_logic = """
    if i == Intent.GET_ATTENDANCE_HOURS:
        records = f.get("records", [])
        if not records:
            return f"No attendance records found for {f.get('date', 'today')}."
        
        # Summarize all hours for today
        summary = []
        for r in records:
            import datetime
            fmt = "%Y-%m-%d %H:%M:%S"
            start_dt = datetime.datetime.strptime(r['shift_start'], fmt)
            if r['status'] == 'ACTIVE':
                end_dt = datetime.datetime.now()
            else:
                end_dt = datetime.datetime.strptime(r['shift_end'], fmt) if r.get('shift_end') else datetime.datetime.now()
            
            diff = end_dt - start_dt
            hours = int(diff.total_seconds() // 3600)
            minutes = int((diff.total_seconds() % 3600) // 60)
            dur_str = f"{hours}h {minutes}m"
            
            status_str = "ongoing" if r['status'] == 'ACTIVE' else "completed"
            summary.append(f"{r['employee_name']} ({status_str}: {dur_str})")
            
        return "Today's hours: " + ", ".join(summary)

    if i == Intent.GET_ATTENDANCE_STATUS:
        active = f.get("active_records", [])
        if not active:
            return "No employees are currently clocked in."
        names = [r["employee_name"] for r in active]
        return f"Currently clocked in: {', '.join(names)}."

    if i == Intent.GET_ACTIVE_SHIFT:
"""

content = content.replace("    if i == Intent.GET_ACTIVE_SHIFT:\n", new_logic, 1)

with open('agent/query_router.py', 'w') as f:
    f.write(content)


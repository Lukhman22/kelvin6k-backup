import re

with open('agent/assistant.py', 'r') as f:
    content = f.read()

# Update _prepare_confirmation_prompt
old_prep = """        if intent_val == "SHIFT_START":
            # Attendance is a record of WHEN, so the operator hears the date and
            # time they are about to be clocked in for and can refuse if the
            # terminal's clock is wrong. Both come from the server clock -- the
            # same source start_shift() stamps the record with -- never from the
            # browser and never from a fixed string.
            now = datetime.datetime.fromtimestamp(self._server_now())
            name = params.get("operator_name") or "Operator"
            line_label = _spoken_line(line_id)
            if params.get("create_operator"):
                return (
                    f"{name}, today is {_spoken_date(now)} and the current time is "
                    f"{_spoken_time(now)}. I could not find an operator named {name}. "
                    f"Shall I register you and start your shift on {line_label}?"
                )
            return (
                f"{name}, today is {_spoken_date(now)} and the current time is "
                f"{_spoken_time(now)}. Shall I start your shift on {line_label}?"
            )

        if intent_val == "SHIFT_END":
            active = shift_store.get_active_shift_for_line(line_id)
            if not active:
                return f"There is no active shift on {_spoken_line(line_id)}."
            op_id = active.get("operator_id")
            op = shift_store.get_operator(op_id) if op_id else None
            name = op["name"] if op else op_id
            return f"Shall I end {name}'s active shift on {_spoken_line(line_id)}?""""

new_prep = """        if intent_val == "SHIFT_START":
            now = datetime.datetime.fromtimestamp(self._server_now())
            name = params.get("operator_name") or "Operator"
            if params.get("create_operator"):
                return (
                    f"New employee detected. I could not find an operator named {name}. "
                    f"Would you like to register as a new employee and start your shift?"
                )
            return f"Shall I start the shift for {name}?"

        if intent_val == "SHIFT_END":
            # For voice, we can just ask a simple confirmation. The backend handles the logic.
            name = params.get("operator_name") or "Operator"
            return f"Shall I end the shift for {name}?""""

content = content.replace(old_prep, new_prep)

# Update _execute_action
old_exec_start = """        if action.intent == "SHIFT_START":
            shift_type = action.params.get("shift_type", "Morning")
            operator_id = action.params.get("operator_id")
            target_walls = action.params.get("target_walls", 0)
            existing = shift_store.get_active_shift_for_line(line_id)
            if existing:
                return "Line 1 already has an active shift. Please close the current shift first."

            if action.params.get("create_operator"):
                op_name = action.params.get("operator_name", "Operator")
                clean_code = re.sub(r"[^A-Za-z0-9]", "", op_name).upper()
                new_op_id = f"OP_{clean_code}"
                if shift_store.get_operator(new_op_id):
                    idx = 1
                    while shift_store.get_operator(f"{new_op_id}_{idx}"):
                        idx += 1
                    new_op_id = f"{new_op_id}_{idx}"
                shift_store.create_operator(
                    operator_id=new_op_id,
                    name=op_name,
                    role="operator",
                    active=1,
                )
                operator_id = new_op_id
                action.params["operator_id"] = new_op_id

            # One timestamp for the whole record: shift_date and start_time
            # must agree, and both come from the server clock -- the same source
            # the operator just heard read back to them.
            started_at = self._server_now()
            moment = datetime.datetime.fromtimestamp(started_at)
            shift_date = moment.date().isoformat()
            try:
                shift_id = shift_store.start_shift(
                    operator_id=operator_id,
                    shift_date=shift_date,
                    shift_type=shift_type,
                    line_id=line_id,
                    target_walls=target_walls,
                    start_time=started_at,
                )
                name = action.params.get("operator_name") or operator_id
                self._session_ctx.update(
                    action.session_id,
                    line_id,
                    current_operator_id=operator_id,
                    current_operator_name=name,
                    current_shift_id=shift_id,
                    current_shift_start=started_at,
                )
                return f"{name}, your shift on {_spoken_line(line_id)} has started."
            except Exception as exc:
                log.error("Failed to start shift: %s", exc)
                return f"Failed to start shift: {exc}"

        if action.intent == "SHIFT_END":
            active = shift_store.get_active_shift_for_line(line_id)
            if not active:
                return f"No active shift found to end on {line_id}."
            try:
                ended_at = self._server_now()
                shift_store.end_shift(active["shift_id"], status="closed", end_time=ended_at)
                st = active.get("start_time")
                dur_formatted = ""
                if st:
                    dur_sec = ended_at - st
                    hours = int(dur_sec // 3600)
                    minutes = int((dur_sec % 3600) // 60)
                    dur_formatted = f"{hours} hours {minutes} minutes" if hours > 0 else f"{minutes} minutes"
                op = shift_store.get_operator(active["operator_id"])
                name = op["name"] if op else active["operator_id"]
                self._session_ctx.clear(action.session_id, line_id)
                dur_str = f" Duration: {dur_formatted}." if dur_formatted else ""
                return f"{name}, your shift on {_spoken_line(line_id)} has ended.{dur_str}"
            except Exception as exc:
                log.error("Failed to end shift: %s", exc)
                return f"Failed to end shift: {exc}"
"""

new_exec_start = """        if action.intent == "SHIFT_START":
            operator_id = action.params.get("operator_id")
            op_name = action.params.get("operator_name", "Operator")
            
            if action.params.get("create_operator"):
                clean_code = re.sub(r"[^A-Za-z0-9]", "", op_name).upper()
                new_op_id = f"OP_{clean_code}"
                if shift_store.get_operator(new_op_id):
                    idx = 1
                    while shift_store.get_operator(f"{new_op_id}_{idx}"):
                        idx += 1
                    new_op_id = f"{new_op_id}_{idx}"
                shift_store.create_operator(
                    operator_id=new_op_id,
                    name=op_name,
                    role="operator",
                    active=1,
                )
                operator_id = new_op_id
                action.params["operator_id"] = new_op_id

            started_at = self._server_now()
            moment = datetime.datetime.fromtimestamp(started_at)
            shift_date = moment.date().isoformat()
            
            try:
                record_id = shift_store.create_attendance_record(
                    operator_id=operator_id,
                    employee_name=op_name,
                    attendance_date=shift_date
                )
                return f"{op_name}, your shift has started."
            except Exception as exc:
                log.error("Failed to start attendance shift: %s", exc)
                return f"Failed to start shift: {exc}"

        if action.intent == "SHIFT_END":
            operator_id = action.params.get("operator_id")
            op_name = action.params.get("operator_name", "Operator")
            
            try:
                # We need to find the record ID for this user's active shift
                records = shift_store.list_attendance_records()
                active = None
                for r in records:
                    if r["status"] == "ACTIVE" and (r["operator_id"] == operator_id or (not operator_id and r["employee_name"] == op_name)):
                        active = r
                        break
                
                if not active:
                    return f"No active shift found for {op_name}."
                
                shift_store.checkout_attendance_record(
                    record_id=active["id"],
                    operator_id=operator_id,
                    employee_name=op_name
                )
                
                # Calculate duration
                fmt = "%Y-%m-%d %H:%M:%S"
                start_dt = datetime.datetime.strptime(active["shift_start"], fmt)
                end_dt = datetime.datetime.now()
                diff = end_dt - start_dt
                hours = int(diff.total_seconds() // 3600)
                minutes = int((diff.total_seconds() % 3600) // 60)
                dur_str = f" {hours} hours {minutes} minutes" if hours > 0 else f" {minutes} minutes"
                
                return f"{op_name}, your shift has ended. Duration:{dur_str}."
            except Exception as exc:
                log.error("Failed to end attendance shift: %s", exc)
                return f"Failed to end shift: {exc}"
"""

content = content.replace(old_exec_start, new_exec_start)

with open('agent/assistant.py', 'w') as f:
    f.write(content)


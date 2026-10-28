# Kelvin6K Manager WhatsApp Notes — Separate RAG Source

## Provenance
Transcribed from a WhatsApp screenshot supplied by the user. The screenshot shows a date separator of 6 September 2026. These are manager-reported operational notes, not an approved technical manual. Keep them separate from the Hindi operator audio records.

## Ingestion rules
- Preserve this source as `manager_whatsapp_note`.
- Do not merge it with operator-audio claims without explicit reconciliation.
- Distinguish historical scheduling notes from standing procedures.
- Resolve unclear words such as “spray,” “clearing accelerator pipe,” and “E motor” with the manager/operator.
- Do not infer temperature limits, material levels, timings, or machine parameters that are not in the screenshot.
- Any pressurized line, chemical, motor, or moving robot procedure requires approved machine/site instructions.

## Extracted notes

### K6K-MGR-001 — Spray interval during operation
- **Reported instruction:** Keep on spray every five minutes.
- **Status:** `manager_reported_needs_clarification`
- **Questions this record can answer:** How often should spray be done?; What does the manager's note say about spraying?; Spray kitni der mein karna hai?
- **Clarification needed:** The note does not specify what material/system is being sprayed, the quantity, or the approved method.
- **Verification:** Clarify what 'spray' refers to and confirm the approved interval, substance, PPE, and procedure before treating as an actionable instruction.
- **Safety note:** Do not infer the substance or initiate spraying based on this note alone.

### K6K-MGR-002 — Accelerator pipe clearing interval
- **Reported instruction:** Keep on clearing accelerator pipe every ten minutes.
- **Status:** `manager_reported_needs_safety_review`
- **Questions this record can answer:** How often should the accelerator pipe be cleared?; What is the accelerator pipe interval?; Accelerator pipe kitni der mein clear karna hai?
- **Clarification needed:** The note does not define 'clearing', required machine state, pressure isolation, tools, or procedure.
- **Verification:** Obtain the approved procedure for the exact accelerator system and clarify whether 'clearing' means inspection, flushing, or another task.
- **Safety note:** Never clear or disconnect a pressurized line. Do not provide step-by-step clearing instructions until the authorized procedure is confirmed.

### K6K-MGR-003 — Trim the final end of the final layer
- **Reported instruction:** Trimming the final end of the final layer.
- **Status:** `manager_reported_needs_procedure`
- **Questions this record can answer:** What finishing task was noted for the final layer?; What should happen at the end of the final layer?
- **Clarification needed:** The tool, timing, safe machine state, and acceptance criteria are not specified.
- **Verification:** Clarify the approved finishing method and whether the robot/material flow must be stopped and isolated first.
- **Safety note:** Do not approach moving equipment or the print head. Follow the approved finishing and isolation procedure.

### K6K-MGR-004 — Reinforcement every eight layers
- **Reported instruction:** Keep adding reinforcement every eight layers.
- **Status:** `manager_reported_needs_engineering_confirmation`
- **Questions this record can answer:** How frequently should reinforcement be added according to the manager's note?; When is reinforcement due?
- **Clarification needed:** Reinforcement type, placement, geometry, and whether the interval applies to all print jobs are unspecified.
- **Verification:** Confirm the reinforcement specification and interval for the active wall design/print job.
- **Safety note:** Do not generalize this interval to every wall or geometry without approved design instructions.

### K6K-MGR-005 — Clean hopper after every wall print
- **Reported instruction:** Every wall print clean the hopper.
- **Status:** `manager_reported_needs_procedure_confirmation`
- **Questions this record can answer:** When should the hopper be cleaned?; Should the hopper be cleaned after each wall?; Hopper kab clean karna hai?
- **Clarification needed:** The approved cleaning method and safe isolation/pressure-release steps are not provided.
- **Verification:** Confirm the exact hopper cleaning procedure and whether the interval applies to all mixes and job configurations.
- **Safety note:** Use approved isolation, pressure release, and material-handling procedures; do not clean while pressurized.

### K6K-MGR-006 — Next print start timing
- **Reported instruction:** Next print should start in an hour.
- **Status:** `context_specific_schedule_note`
- **Questions this record can answer:** When was the next print supposed to start?; What schedule note was recorded for the next print?
- **Clarification needed:** The note is time-specific; it does not establish a permanent one-hour rule or specify the date/job context beyond the chat date.
- **Verification:** Treat as a historical scheduling note for the message context, not a current schedule. Confirm the active print plan before answering about today's next print.
- **Safety note:** Do not infer a current start time from this historical message.

### K6K-MGR-007 — E motor cooldown after each wall
- **Reported instruction:** Cool down E motor after every wall print.
- **Status:** `manager_reported_needs_limits`
- **Questions this record can answer:** When should the E motor be cooled down?; What maintenance note concerns the E motor?
- **Clarification needed:** The note does not specify cooldown method, required duration, allowable temperature, or whether 'E motor' refers to a particular motor model/component.
- **Verification:** Confirm motor identity, manufacturer temperature limits, approved cooldown method, and whether cooling is required after every wall.
- **Safety note:** Do not apply cooling methods or touch the motor without the approved procedure. Do not invent a temperature threshold.

### K6K-MGR-008 — Check E motor temperature with temperature gun
- **Reported instruction:** Check E motor temperature using a temperature gun.
- **Status:** `manager_reported_needs_limits`
- **Questions this record can answer:** How should the E motor temperature be checked according to the note?; Which tool should be used to check E motor temperature?
- **Clarification needed:** Measurement location, emissivity/setup, acceptable temperature range, and measurement timing are unspecified.
- **Verification:** Confirm approved measurement points, instrument use, and manufacturer/site temperature limits.
- **Safety note:** A temperature reading should be compared with a verified limit; do not label a motor faulty using an invented threshold.

### K6K-MGR-009 — Get temperature gun from office
- **Reported instruction:** Temperature gun from office.
- **Status:** `historical_logistics_note`
- **Questions this record can answer:** Where did the note say to get the temperature gun?; Where is the temperature gun supposed to be obtained?
- **Clarification needed:** The screenshot records the office as the source but does not confirm present availability or storage location.
- **Verification:** Check current tool availability with the team.
- **Safety note:** None stated in source.

### K6K-MGR-010 — Check accelerator level in container
- **Reported instruction:** Keep on checking accelerator level in the container.
- **Status:** `manager_reported_needs_thresholds`
- **Questions this record can answer:** What should operators keep checking in the container?; When should accelerator level be checked?
- **Clarification needed:** No checking interval, minimum/maximum level, measurement method, or replenishment procedure is given.
- **Verification:** Confirm check frequency, acceptable level range, and approved replenishment/material-handling procedure.
- **Safety note:** Do not infer a level threshold or chemical-handling procedure.

### K6K-MGR-011 — Confirm which wall should be printed next
- **Reported instruction:** Confirm which wall needs to be printed.
- **Status:** `manager_reported_operational_handover`
- **Questions this record can answer:** Which wall should be printed next?; What does the note say about selecting the next wall?
- **Clarification needed:** The screenshot does not identify a wall number, design, priority, or current production order.
- **Verification:** Retrieve the current approved print plan or confirm with the responsible supervisor; do not infer a wall ID from this note.
- **Safety note:** Confirm the active approved job before starting a print.

### K6K-MGR-012 — Operator-to-operator next-print handover
- **Reported instruction:** Every operator needs to tell the other operator which next print needs to be printed.
- **Status:** `manager_reported_operational_handover`
- **Questions this record can answer:** What information should one operator hand over to the next?; What is the next-print communication rule?
- **Clarification needed:** No required handover fields or formal sign-off method are specified.
- **Verification:** Agree on a handover template including next wall/job ID, status, material, settings reference, outstanding maintenance, and responsible operator.
- **Safety note:** Do not begin a new print based only on an informal or ambiguous handover; confirm the approved job details.

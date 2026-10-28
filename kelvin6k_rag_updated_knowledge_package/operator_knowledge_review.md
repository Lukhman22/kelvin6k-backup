# Kelvin6K Operator Knowledge — RAG Preparation Draft

## Provenance and use

This document structures the user's supplied English Q&A/problem-solution summary attributed to an experienced operator's Hindi MP4 recording. The original audio has **not** been independently transcribed in this preparation step. Treat this as operator-reported knowledge, not a signed-off machine manual.

**Use:** RAG retrieval and engineer review. Do not use as direct robot-control instructions.

## Required distinctions

- **Operator-reported:** reported in the supplied summary.
- **Possible cause:** plausible explanation mentioned in the source, not a diagnosis.
- **Confirmed root cause:** leave empty until supported by inspection, logs, or approved engineering review.
- **Reported workaround:** action described by the operator but not automatically approved.
- **Verified procedure:** only after the relevant manufacturer/site procedure is checked.

## High-priority safety gate

Do not present the following as actionable step-by-step instructions until an authorized Kelvin6K engineer confirms the exact machine-specific procedure:
- striking/pushing a pump with a hammer;
- pulsing feedrate to clear a blockage;
- extruding material during pauses;
- changing accelerator flow/dosage;
- resetting servo/encoder values for E137.1;
- changing H0D11 or jogging the Z-axis;
- cleaning or clearing a pressurized hose/nozzle.

If a clog or critical error occurs, the assistant should direct the operator to the approved stop/isolation/depressurization and inspection procedure. It must not actuate the pump or robot.

## Records

### K6K-CLEAN-001 — Pump and delivery hose cleaning interval

- **Category/status:** `maintenance.cleaning` / `operator_reported_needs_validation`
- **Question/symptom:** How frequently should the pump and hose be cleaned?
- **Operator-reported answer:** A full cleaning should be performed every 3 to 4 hours, immediately after completing a wall, and again before restarting if there has been about a one-hour gap between prints.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Full pump and hose washout at the stated intervals.
- **Verification needed:** Confirm the official cleaning interval for the exact pump, hose, concrete mix, and accelerator configuration. Resolve whether cleaning is required after every wall, every 3–4 hours, and/or after one hour idle; these may be cumulative or context-specific.
- **Conflicts/gaps:** Intervals are described in multiple ways and need engineering confirmation.
- **Safety notes:** Use the approved machine-specific depressurization, isolation, and cleaning procedure. Do not clear a pressurized nozzle or hose.
- **Keywords:** pump cleaning, hose cleaning, washout, idle period, maintenance interval, clean before restart

### K6K-HOSE-001 — Delivery hose positioning

- **Category/status:** `setup.hose_routing` / `operator_reported_needs_validation`
- **Question/symptom:** How should the delivery hose between pump and hopper be positioned?
- **Operator-reported answer:** The hose should not bend and should be connected in a proper shape, neither too loose nor too tight.
- **Possible causes:** Improper hose routing or tension may affect material delivery; exact failure mechanism not confirmed in the supplied notes.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Position and connect the hose without sharp bends or excessive slack/tension.
- **Verification needed:** Confirm required bend radius, connector orientation, pressure rating, and approved routing with the equipment manual/engineer.
- **Safety notes:** Do not reposition or disconnect a pressurized hose. Follow approved isolation and pressure-release procedure.
- **Keywords:** delivery hose, hose bent, pump to hopper, hose connector, hose routing

### K6K-FLOW-001 — Sudden drop or interruption in material flow

- **Category/status:** `printing.material_flow` / `operator_reported_action_requires_safety_review`
- **Question/symptom:** What should an operator do when concrete/material flow suddenly drops or stops?
- **Operator-reported answer:** The notes report manually pushing or hitting material in the pump with a hammer, or rapidly increasing PC feedrate (example 10% to 30%) and immediately reducing it again to clear a suspected particle blockage.
- **Possible causes:** Hardened material; Particle blockage; Inadequate cleaning; Other causes not established by the supplied notes
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Hammering/pushing material and rapidly pulsing feedrate were reported by the operator as actions used.
- **Verification needed:** An authorized engineer must determine the approved diagnostic and clearing procedure for this exact pump and control configuration. Verify whether the reported actions are permitted; do not encode them as default recommendations.
- **Conflicts/gaps:** The notes describe an action, but do not provide a validated procedure, machine state, pressure state, or verified outcome.
- **Safety notes:** Do not strike or manipulate pressurized equipment, and do not rapidly alter feedrate as a generic AI instruction. Stop/secure the process and follow the approved blockage-clearing procedure.
- **Keywords:** material flow drop, no material coming out, blockage, particle clog, flow stoppage, pump blockage

### K6K-SPEED-001 — Feedrate guidance for straight versus complex paths

- **Category/status:** `printing.parameters.feedrate` / `operator_reported_values_need_engineering_approval`
- **Question/symptom:** What feedrates were reported for straight walls and complex/curved paths?
- **Operator-reported answer:** For straight walls, 150 was described as a safe baseline, 100 as a minimum, and 170 as a tested maximum. For complex or curved paths, the reported range is 100–120 to reduce robot-arm jerking.
- **Possible causes:** Using straight-wall speed on a complex/curved path was reported as associated with robot arm jerking/tearing.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** The operator reports reducing feedrate for complex/non-linear toolpaths.
- **Verification needed:** Confirm units/scale (e.g., percent override versus another feedrate scale), approved values for each robot configuration, toolpath, material, and print job. Do not assume these are universal limits.
- **Conflicts/gaps:** A separate project review records 150% and 170% as context-specific values requiring confirmation.
- **Safety notes:** Do not change live machine feedrate based solely on RAG output. Refer to approved job parameters and authorized operating procedures.
- **Keywords:** feedrate, straight wall speed, curved path speed, robot arm jerking, complex toolpath, 100 120 150 170

### K6K-LAYER-001 — Manual layer thickness measurement

- **Category/status:** `printing.quality.layer_thickness` / `operator_reported_values_conflict_needs_review`
- **Question/symptom:** How is layer/bead thickness measured and corrected?
- **Operator-reported answer:** The operator measures the first layer with a tape measure and repeats checks periodically. The supplied notes give a nominal range of 40–45 mm and report that values above 45 mm cause problems. They also say travel speed is adjusted to stretch/thin the bead.
- **Possible causes:** Incorrect feedrate or material volume was reported as a possible contributor to excessive bead thickness.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Manual measurement and travel-speed adjustment were reported.
- **Verification needed:** Confirm the approved thickness for the active print/job and safe adjustment procedure. Record measurement location, wall geometry, layer number, and machine settings.
- **Conflicts/gaps:** One part of the supplied summary mentions 40–45 mm; another question refers to 40–50 mm.; Measurement cadence varies: first layer/first 1–2 layers, then every 10–15 layers or 10–20 layers.
- **Safety notes:** Do not infer a universal target or recommend live speed changes without approved job parameters.
- **Keywords:** layer thickness, bead width, 40 mm, 45 mm, 50 mm, tape measure, thick layer, thin bead

### K6K-CURE-001 — Layer green strength and wall slumping/collapse

- **Category/status:** `printing.quality.curing_slumping` / `operator_reported_thresholds_conflict_needs_review`
- **Question/symptom:** How quickly must lower concrete layers harden to support subsequent layers?
- **Operator-reported answer:** The notes say lower layers should gain sufficient green strength within 3–4 subsequent layers, and report collapse risk if the base has not hardened by the fifth layer. Another part says a wall may fail if the bottom remains soft until layers 10–12. These thresholds conflict and require confirmation.
- **Possible causes:** Insufficient early strength/curing was reported as a cause of slumping or collapse.; Accelerator performance/flow was mentioned as something to check.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Check accelerator operation and stop/inspect the print if the foundation is not hardening as expected; exact threshold requires approval.
- **Verification needed:** Ask the experienced operator/engineer to clarify the correct threshold for the exact mix, accelerator dosage, geometry, temperature, and print setup. Define an objective green-strength check.
- **Conflicts/gaps:** Reported thresholds include 3–4 subsequent layers, fifth layer, and 10th–12th layer; do not merge these into one rule.
- **Safety notes:** A visibly unstable wall may collapse. Keep personnel clear and follow the approved stop/secure/inspection procedure. Do not automatically adjust accelerator dosing.
- **Keywords:** wall collapse, slumping, green strength, layer not hardening, accelerator, soft foundation, curing

### K6K-PAUSE-001 — Material stagnation during print pause

- **Category/status:** `printing.pause_material_stagnation` / `operator_reported_safety_review_required`
- **Question/symptom:** What happens if printing is paused while accelerator-mixed material remains in the hopper?
- **Operator-reported answer:** The notes report extruding material every 2–3 minutes during a pause. They warn that accelerator-mixed material left stagnant in the hopper for about 5 minutes may harden severely; another answer says material may set after 15–20 minutes.
- **Possible causes:** Stagnant accelerator-mixed concrete hardening in the hopper or flow path was reported.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Periodic extrusion during pauses was reported as an operator practice.
- **Verification needed:** Confirm the material/accelerator-specific open time and approved pause procedure. Resolve the different 5-minute and 15–20-minute statements; they may describe different material locations or conditions.
- **Conflicts/gaps:** 5-minute hopper hardening versus 15–20-minute material setting; not necessarily equivalent conditions.
- **Safety notes:** Do not instruct the AI to automatically extrude material or actuate the pump. The voice assistant should direct operators to the approved pause procedure and authorized controls.
- **Keywords:** print pause, stagnant material, hopper hardening, 5 minute rule, 15 20 minutes, extrude during pause, accelerator

### K6K-VISION-001 — Camera false stops caused by shadows or lighting

- **Category/status:** `vision.false_positive` / `operator_reported_observation`
- **Question/symptom:** Have shadows or shop lighting caused the camera system to stop the machine incorrectly?
- **Operator-reported answer:** The operator summary says this issue has not been observed so far.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** No corrective action reported.
- **Verification needed:** Record as an operator-reported historical observation, not proof that false stops cannot occur. Validate against camera logs and a representative range of lighting conditions.
- **Conflicts/gaps:** No log evidence or sample size is provided.
- **Safety notes:** Do not disable vision safeguards based on this statement alone.
- **Keywords:** camera false stop, shadows, lighting, false positive, vision system

### K6K-ENV-001 — Historical environmental and machine-parameter notebook

- **Category/status:** `data_source.environmental_history` / `data_source_reported_not_yet_reviewed`
- **Question/symptom:** Is there historical environmental and process data that could support analysis?
- **Operator-reported answer:** The supplied summary reports a notebook with 10–15 days of readings for temperature, humidity, pump speed, accelerator speed, and feedrate, recorded every 2–3 hours.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Locate, digitize, and review the notebook before using the data.
- **Verification needed:** Obtain the notebook; confirm units, timestamps, sampling intervals, sensor/source, missing entries, calibration, print/job IDs, and whether values are measured or manually recorded.
- **Conflicts/gaps:** The notebook itself has not been supplied or inspected.
- **Safety notes:** Do not use incomplete historical correlations as proof of a machine fault or automatically change settings.
- **Keywords:** temperature history, humidity, pump speed, accelerator speed, feedrate history, operator notebook, environmental data

### K6-FAULT-E136.1 — Error code E136.1 — reported absolute encoder cable damage

- **Category/status:** `fault_code.servo_encoder` / `operator_reported_diagnosis_needs_manual_confirmation`
- **Question/symptom:** What was reported as the cause of error E136.1?
- **Operator-reported answer:** The supplied notes associate E136.1 with physical damage to the absolute encoder cable and report inspecting, repairing, or replacing the cable.
- **Possible causes:** Physical damage to absolute encoder cable, as reported.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Inspect cable and repair/replace if damage is confirmed, following the authorized service procedure.
- **Verification needed:** Confirm exact error definition in the relevant servo/robot manufacturer manual and verify cable damage before classifying it as the root cause.
- **Conflicts/gaps:** No manufacturer/model/manual reference or fault log is included.
- **Safety notes:** Servo and encoder work must be performed by authorized personnel with the machine isolated according to the service procedure.
- **Keywords:** E136.1, encoder cable, absolute encoder, servo error, cable damage

### K6-FAULT-E137.1 — Error code E137.1 — reported robot/servo position mismatch

- **Category/status:** `fault_code.servo_position` / `operator_reported_diagnosis_and_reset_procedure_unverified`
- **Question/symptom:** What was reported as the cause of error E137.1?
- **Operator-reported answer:** The notes describe a positional mismatch between the robot arm and servo-drive memory and mention resetting encoder values in the servo drive to synchronize them.
- **Possible causes:** Robot/servo position mismatch, as reported.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** The source mentions an encoder-value reset; this is recorded for engineering review only, not as a general instruction.
- **Verification needed:** Confirm the exact alarm code and authorized recovery steps in the manufacturer documentation. Establish reference-position, homing, and collision-risk requirements before approving any reset.
- **Conflicts/gaps:** No manufacturer/model/manual reference, fault log, or validated recovery sequence supplied.
- **Safety notes:** Do not tell the assistant to reset servo/encoder values or move the robot based solely on this record. Require authorized technician review and the exact machine procedure.
- **Keywords:** E137.1, servo drive, position mismatch, encoder reset, robot arm position, servo alarm

### K6-Z-001 — Z-axis downward motion blocked by travel limit

- **Category/status:** `fault.z_axis_limit` / `operator_reported_parameter_change_requires_authorization`
- **Question/symptom:** What was reported when the Z-axis could not move downward?
- **Operator-reported answer:** The notes attribute the restriction to a software travel limit and mention parameter H0D11 as a way to enable manual downward jogging.
- **Possible causes:** Software travel limit, as reported.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Parameter H0D11 was mentioned; do not present this as an approved procedure until verified.
- **Verification needed:** Verify parameter name, function, permitted range, machine model, and recovery procedure against the manufacturer/controls documentation and an authorized engineer.
- **Conflicts/gaps:** No manufacturer documentation or parameter definition provided.
- **Safety notes:** Changing travel limits or enabling manual jogging can create collision/crush risks. Do not provide step-by-step parameter modification or trigger robot motion from RAG output.
- **Keywords:** Z-axis locked, Z axis cannot go down, H0D11, travel limit, manual jog, gantry downward motion

### K6-QUALITY-001 — Early-layer accelerator check

- **Category/status:** `printing.startup.early_layer_check` / `operator_reported_practice_needs_definition`
- **Question/symptom:** What should be checked during the first few layers if concrete is not hardening sufficiently?
- **Operator-reported answer:** The supplied notes report a trial over the first 1–3 layers and a manual hardness check; if it is not reaching a stated 50% hardness, accelerator flow should be checked.
- **Possible causes:** Insufficient accelerator flow was mentioned as a possibility.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Check accelerator flow if early layers do not harden as expected.
- **Verification needed:** Define what '50% hardness' means, how it is measured, and the approved accelerator-flow inspection procedure. Confirm the correct startup layer count.
- **Conflicts/gaps:** No measurement method or objective criterion for '50% hardness' is supplied.
- **Safety notes:** Do not automatically alter chemical accelerator dosage or flow. Follow approved material handling and machine procedures.
- **Keywords:** first layers, early hardening, 50 percent hardness, accelerator flow, startup check

### K6-SAFETY-001 — Prevent wall contact and collision during printing

- **Category/status:** `safety.printing_clearance` / `operator_reported_safety_guidance`
- **Question/symptom:** What precautions were reported to reduce wall damage or robot collision?
- **Operator-reported answer:** The supplied summary says personnel other than the testing operator should not touch the wall during printing, and objects should be kept away to prevent the robot from colliding with the wall.
- **Possible causes:** Human contact or nearby objects were identified as possible sources of interference/damage.
- **Confirmed root cause:** Not confirmed / not supplied
- **Reported action:** Keep personnel and objects clear of the active printing area in accordance with site safety rules.
- **Verification needed:** Align with the site's formal risk assessment, exclusion zone, guarding, and operator authorization policy.
- **Conflicts/gaps:** Exact exclusion-zone dimensions and formal site policy are not supplied.
- **Safety notes:** Follow site-approved guarding and exclusion-zone procedures; do not approach a moving robot or unstable printed wall.
- **Keywords:** wall collision, touching wall, keep area clear, robot collision, printing safety

## Conflicts to resolve before production RAG

1. **Cleaning cadence:** every 3–4 hours, immediately after a wall, and after a one-hour idle period. Clarify which are mandatory and under what conditions.
2. **Material hardening time:** about 5 minutes in the accelerator-mixed hopper versus 15–20 minutes for material setting. Clarify material, location, temperature, and conditions.
3. **Layer thickness:** 40–45 mm appears in one answer; 40–50 mm appears in another. Confirm target by print/job geometry.
4. **Measurement cadence:** first layer/first 1–2 layers, then every 10–15 or 10–20 layers. Confirm the approved inspection schedule.
5. **Wall green strength:** 3–4 subsequent layers, a fifth-layer stop threshold, and a 10th–12th-layer collapse statement all appear. Do not collapse these into one threshold.
6. **Feedrate:** straight-path values 100/150/170 and curved-path 100–120 are operator-reported; confirm scale, units, and job-specific approved limits.
7. **E136.1 / E137.1 / H0D11:** verify against exact robot/servo model documentation and authorized service procedures.
8. **“50% hardness”:** define the measurement method and objective acceptance criterion.

## Suggested RAG behavior

When asked a troubleshooting question:
1. Retrieve the most relevant issue record(s).
2. State what was reported, and identify it as operator-reported if not verified.
3. Separate possible causes from confirmed root cause.
4. Ask for missing context (robot model, print job, layer, material, error code, current state) if needed.
5. For safety-critical or machine-specific actions, refer to the approved procedure and authorized technician; do not invent commands or trigger machine movement.
6. Cite the record/source in the answer and say when the knowledge base has no verified answer.

## Example test queries (synthetic, not verbatim from audio)

- “Pump aur hose ki cleaning kitni der mein karni chahiye?”
- “Material flow achanak kam ho gaya, kya check karna chahiye?”
- “Curved wall ke liye operator ne kaunsa feedrate range report kiya?”
- “Layer 45 mm se zyada ho raha hai; source mein kya observation hai?”
- “Pause ke dauran hopper mein material hard hone ke baare mein kya report hai?”
- “E137.1 ka reported explanation kya hai, aur kya verify karna baaki hai?”
- “H0D11 ke baare mein notes kya kehte hain? Kya yeh approved procedure hai?”
- “Kya camera lighting ki wajah se false stop report hua tha?”

These are generated retrieval tests, not quotations from the operator.


## Additional handwritten fault-note set

The records below are transcribed from the user's summary of handwritten notes. Root causes and fixes are not supplied unless explicitly stated; do not infer them.

### K6K-HW-ACC-001 — Accelerator nozzle clogging / premature setting
- **Reported issue:** The notes report that chemical accelerator causes material to set too quickly and become stuck/clogged directly in the nozzle.
- **Status:** reported_issue_cause_needs_validation
- **Verification required:** Confirm the exact material and accelerator combination, conditions, and actual failure mechanism with the operator and approved process documentation.

### K6K-HW-BLOCK-001 — Material blockage in hopper and delivery hose
- **Reported issue:** Material frequently gets stuck inside the main hopper and delivery hose.
- **Status:** reported_recurring_issue
- **Verification required:** Record when blockage occurs, material/accelerator conditions, cleaning history, machine state, and the approved diagnostic procedure.

### K6K-HW-ACC-PUMP-001 — Accelerator pump pressure drops after several days
- **Reported issue:** After a few days of use, the accelerator pump's pressure drops.
- **Status:** reported_issue_cause_unconfirmed
- **Verification required:** Confirm pressure readings, operating hours, maintenance history, pump model, and whether dosing inconsistency has been measured.

### K6K-MAT-CONSISTENCY-001 — Concrete consistency: overly wet material
- **Reported issue:** If the material is too wet, the printed layers come out thin, increasing the risk of the wall collapsing under its own weight.
- **Status:** reported_relationship_needs_validation
- **Verification required:** Record mix recipe, water content/workability, layer measurements, wall geometry, and actual outcomes; confirm the relationship with the process engineer.

### K6K-MAT-CONSISTENCY-002 — Concrete consistency: overly dry material
- **Reported issue:** If the material is too dry, layers come out thick and prone to cracking. The notes also report that the material pump draws in air and struggles to push the hardened mixture.
- **Status:** reported_relationship_needs_validation
- **Verification required:** Confirm material consistency criteria, mix details, air-ingress observations, and whether these symptoms occur together in the same operating conditions.

### K6K-ENV-001 — Ambient temperature and weather affect curing and stability
- **Reported issue:** Changes in ambient weather and temperature during printing affect material curing behavior and print stability.
- **Status:** reported_relationship_needs_data
- **Verification required:** Compare timestamped temperature/humidity records, mix details, accelerator settings, and print outcomes before drawing conclusions.

### K6K-MOTOR-E-001 — E-motor overheating
- **Reported issue:** The electric motor overheats during operation.
- **Status:** reported_issue_needs_measurements
- **Verification required:** Identify the exact E motor, capture temperature readings and operating duration/load, and compare against manufacturer-approved limits.

### K6K-MIXER-001 — E-mixer loosening or bearing damage
- **Reported issue:** The E-mixer occasionally comes loose or suffers bearing damage, preventing the mixer from rotating and blending concrete properly.
- **Status:** reported_mechanical_issue_needs_inspection
- **Verification required:** Record the affected assembly, inspection findings, bearing condition, maintenance history, and verified repair.

### K6K-VFD-001 — Pump motor VFD faults interrupt material delivery
- **Reported issue:** The variable frequency drive (VFD) controlling the pump motor reports faults, interrupting material delivery.
- **Status:** reported_issue_needs_fault_codes
- **Verification required:** Capture exact VFD make/model, displayed fault code, event timestamp, operating state, and manufacturer troubleshooting guidance.

### K6K-SERVO-E731 — Servo drive error E-731
- **Reported issue:** The notes list servo drive faults, including E-731, which typically halt gantry movement.
- **Status:** reported_fault_code_unverified
- **Verification required:** Confirm the exact alarm code against the manufacturer manual for the installed servo/drive model and capture the associated fault context.

### K6K-ETHERCAT-001 — EtherCAT communication drops or faults
- **Reported issue:** Communication drops or faults occur along EtherCAT industrial network cables connecting drives and controllers.
- **Status:** reported_issue_needs_logs
- **Verification required:** Inspect diagnostic logs and link status; confirm cable, connector, topology, and device fault evidence before identifying a root cause.

### K6K-ESP32-001 — ESP-32 microcontroller errors
- **Reported issue:** Issues originating from the ESP-32 microcontroller unit are listed.
- **Status:** reported_issue_insufficient_detail
- **Verification required:** Collect the exact symptom, firmware version, serial/log output, power/reset behavior, connected peripherals, and reproduction steps.

### K6K-USB-001 — USB cable data connection failures
- **Reported issue:** Data connection failures related to USB cables are listed.
- **Status:** reported_issue_needs_diagnostics
- **Verification required:** Record connected devices, operating system messages, cable/port tests, and whether the fault follows the cable or port.

### K6K-WIRING-001 — Electrical wiring short circuits
- **Reported issue:** Short circuits in the wiring harness are listed as an issue and are described as posing safety and operational risks.
- **Status:** reported_safety_critical_issue
- **Verification required:** Have a qualified technician inspect the wiring harness and electrical protection/fault evidence using the approved service procedure.

### K6K-CAL-V1-001 — Version 1 calibration and alignment problems
- **Reported issue:** Version 1 setup issues include Y-axis calibration faults, Z-height setting problems, general printing calibration errors, and mechanical alignment issues.
- **Status:** reported_issue_needs_case_details
- **Verification required:** Separate each symptom into an individual incident with robot configuration, calibration procedure/version, measurements, logs, and verified correction.

### K6K-GCODE-001 — G-code generation or interpretation problems
- **Reported issue:** Problems occur with toolpath generation or the machine misreading G-code instructions.
- **Status:** reported_issue_needs_examples
- **Verification required:** Collect the affected G-code file, expected versus observed path, software versions, parser/controller logs, and a safe simulation/review result.

### K6K-JERK-V2-001 — Version 2 jerking or vibration during printing
- **Reported issue:** Version 2 experiences physical jerking or violent vibrations during active printing, which can tear the concrete bead and cause structural defects.
- **Status:** reported_issue_needs_instrumented_diagnosis
- **Verification required:** Capture the exact V2 configuration, affected toolpath, motion/drive logs, settings, and conditions. Separate observed vibration from suspected causes.


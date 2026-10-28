# Kelvin6K Handwritten Fault Notes — RAG Draft

## Provenance
Based on the user's transcription of handwritten notes. The original handwritten image has not been independently inspected in this step. These are reported fault categories and descriptions, not confirmed root-cause diagnoses or approved repair procedures.

## RAG handling rules
- Keep each issue separate and preserve its issue ID and source.
- Treat causes as unconfirmed unless supported by engineering evidence.
- The notes do not provide verified solutions for these new issues; do not invent solutions.
- Ask for fault codes, logs, machine version, operating conditions, and inspection results where needed.
- Do not recommend live electrical probing, unverified servo resets, parameter changes, unreviewed G-code execution, or work on pressurized equipment.
- The source transcription says item 19 was crossed out regarding the accelerator. Its exact referent is ambiguous; do not add a separate accelerator issue from that crossed-out item.

## Issues

### K6K-HW-ACC-001 — Accelerator nozzle clogging / premature setting
- **Category:** `material_flow.accelerator_nozzle`
- **Reported issue:** The notes report that chemical accelerator causes material to set too quickly and become stuck/clogged directly in the nozzle.
- **Possible cause stated in source:** Premature setting associated with the chemical accelerator.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Confirm the exact material and accelerator combination, conditions, and actual failure mechanism with the operator and approved process documentation.
- **Missing information:** Frequency and conditions; Exact nozzle and accelerator configuration; Whether the explanation was directly observed or inferred; Approved safe clearing procedure
- **Safety note:** Do not instruct an operator to clear a pressurized nozzle. Follow the approved stop, isolation, and pressure-release procedure.
- **Retrieval keywords:** accelerator nozzle clog, nozzle blockage, material setting too quickly, chemical accelerator, clogged nozzle

### K6K-HW-BLOCK-001 — Material blockage in hopper and delivery hose
- **Category:** `material_flow.hopper_hose`
- **Reported issue:** Material frequently gets stuck inside the main hopper and delivery hose.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Record when blockage occurs, material/accelerator conditions, cleaning history, machine state, and the approved diagnostic procedure.
- **Missing information:** Frequency and exact location; Material state when blockage occurs; Verified cause and resolution
- **Safety note:** Do not clear or disconnect a pressurized hose or work inside equipment without the approved isolation procedure.
- **Retrieval keywords:** hopper blockage, hose blockage, material stuck, flow stoppage, delivery hose clog

### K6K-HW-ACC-PUMP-001 — Accelerator pump pressure drops after several days
- **Category:** `material_flow.accelerator_pump`
- **Reported issue:** After a few days of use, the accelerator pump's pressure drops.
- **Possible cause stated in source:** The notes say this may lead to inconsistent chemical dosing.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Confirm pressure readings, operating hours, maintenance history, pump model, and whether dosing inconsistency has been measured.
- **Missing information:** Expected and observed pressure values; Pump model and service history; Measurement method; Verified corrective action
- **Safety note:** Do not adjust chemical dosing or pressure settings based on this note alone; use approved maintenance procedures.
- **Retrieval keywords:** accelerator pump pressure drop, low accelerator pressure, inconsistent accelerator dosing, accelerator pump degradation

### K6K-MAT-CONSISTENCY-001 — Concrete consistency: overly wet material
- **Category:** `material_quality.consistency`
- **Reported issue:** If the material is too wet, the printed layers come out thin, increasing the risk of the wall collapsing under its own weight.
- **Possible cause stated in source:** Excessively wet material is associated in the notes with thin layers and collapse risk.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Record mix recipe, water content/workability, layer measurements, wall geometry, and actual outcomes; confirm the relationship with the process engineer.
- **Missing information:** Definition or measurement of 'too wet'; Mix-specific acceptance range; Conditions and supporting observations
- **Safety note:** Treat unstable walls as a physical hazard; keep clear and follow the site's approved stop/inspection procedure.
- **Retrieval keywords:** wet concrete, thin printed layers, wall collapse, material consistency, mix too wet

### K6K-MAT-CONSISTENCY-002 — Concrete consistency: overly dry material
- **Category:** `material_quality.consistency`
- **Reported issue:** If the material is too dry, layers come out thick and prone to cracking. The notes also report that the material pump draws in air and struggles to push the hardened mixture.
- **Possible cause stated in source:** Overly dry material is associated in the notes with thick layers, cracking, air intake, and difficulty pumping.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Confirm material consistency criteria, mix details, air-ingress observations, and whether these symptoms occur together in the same operating conditions.
- **Missing information:** Objective consistency measurement; Mix recipe and environmental conditions; Verified cause of air intake; Verified resolution
- **Safety note:** Do not recommend changing mix proportions without approved material specifications.
- **Retrieval keywords:** dry concrete, thick layers, cracking, pump drawing air, hardened mixture, material too dry

### K6K-ENV-001 — Ambient temperature and weather affect curing and stability
- **Category:** `environment.material_conditions`
- **Reported issue:** Changes in ambient weather and temperature during printing affect material curing behavior and print stability.
- **Possible cause stated in source:** Environmental changes are reported as a factor affecting curing and print stability.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Compare timestamped temperature/humidity records, mix details, accelerator settings, and print outcomes before drawing conclusions.
- **Missing information:** Measured conditions and units; Thresholds or approved operating envelope; Correlation with specific failures
- **Safety note:** Do not infer or automatically alter accelerator or machine settings from weather alone.
- **Retrieval keywords:** weather, ambient temperature, humidity, curing behavior, print stability, environmental conditions

### K6K-MOTOR-E-001 — E-motor overheating
- **Category:** `hardware.motor_temperature`
- **Reported issue:** The electric motor overheats during operation.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Identify the exact E motor, capture temperature readings and operating duration/load, and compare against manufacturer-approved limits.
- **Missing information:** Motor identity/model; Measured temperature and measurement point; Manufacturer limit; Fault logs and resolution
- **Safety note:** Do not invent a temperature threshold or touch the motor to assess temperature. Follow the approved shutdown and inspection procedure if overheating is suspected.
- **Retrieval keywords:** E motor overheating, motor hot, motor temperature, temperature gun, motor thermal issue

### K6K-MIXER-001 — E-mixer loosening or bearing damage
- **Category:** `hardware.mixer`
- **Reported issue:** The E-mixer occasionally comes loose or suffers bearing damage, preventing the mixer from rotating and blending concrete properly.
- **Possible cause stated in source:** Loose mixer components or bearing damage are identified in the notes as possible mechanical failure modes.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Record the affected assembly, inspection findings, bearing condition, maintenance history, and verified repair.
- **Missing information:** Exact mixer assembly and model; Frequency and circumstances; Inspection evidence; Approved repair procedure
- **Safety note:** Do not inspect or tighten moving machinery. Isolate the equipment and follow the approved maintenance procedure.
- **Retrieval keywords:** E-mixer, mixer loose, bearing damage, mixer not rotating, poor concrete mixing

### K6K-VFD-001 — Pump motor VFD faults interrupt material delivery
- **Category:** `electrical.pump_vfd`
- **Reported issue:** The variable frequency drive (VFD) controlling the pump motor reports faults, interrupting material delivery.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Capture exact VFD make/model, displayed fault code, event timestamp, operating state, and manufacturer troubleshooting guidance.
- **Missing information:** VFD model and code; Fault frequency; Drive logs; Verified resolution
- **Safety note:** Do not reset or reconfigure a VFD without the authorized machine-specific procedure and appropriate electrical isolation.
- **Retrieval keywords:** pump VFD fault, variable frequency drive, pump motor fault, material delivery interrupted, VFD alarm

### K6K-SERVO-E731 — Servo drive error E-731
- **Category:** `electrical.servo_fault`
- **Reported issue:** The notes list servo drive faults, including E-731, which typically halt gantry movement.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Confirm the exact alarm code against the manufacturer manual for the installed servo/drive model and capture the associated fault context.
- **Missing information:** Manufacturer and drive model; Exact displayed code/format; Fault history; Approved recovery procedure
- **Safety note:** Do not infer the meaning of E-731 or reset the drive based on the code alone. Follow authorized fault-recovery procedures.
- **Retrieval keywords:** E-731, E731, servo drive error, gantry halted, servo alarm

### K6K-ETHERCAT-001 — EtherCAT communication drops or faults
- **Category:** `communications.ethercat`
- **Reported issue:** Communication drops or faults occur along EtherCAT industrial network cables connecting drives and controllers.
- **Possible cause stated in source:** The notes associate the communication issue with EtherCAT cables; physical cable failure is not confirmed.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Inspect diagnostic logs and link status; confirm cable, connector, topology, and device fault evidence before identifying a root cause.
- **Missing information:** Network/device fault logs; Affected node or segment; Cable inspection results; Frequency and conditions
- **Safety note:** Do not disconnect industrial network wiring while energized unless the approved procedure explicitly permits it.
- **Retrieval keywords:** EtherCAT fault, EtherCAT cable, communication drop, drive controller communication, industrial network

### K6K-ESP32-001 — ESP-32 microcontroller errors
- **Category:** `electronics.esp32`
- **Reported issue:** Issues originating from the ESP-32 microcontroller unit are listed.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Collect the exact symptom, firmware version, serial/log output, power/reset behavior, connected peripherals, and reproduction steps.
- **Missing information:** Error message or log; Board and firmware version; When the issue occurs; Verified fix
- **Safety note:** Do not infer a specific firmware or wiring fix without evidence.
- **Retrieval keywords:** ESP32 error, ESP-32, microcontroller issue, firmware error, controller reset

### K6K-USB-001 — USB cable data connection failures
- **Category:** `communications.usb`
- **Reported issue:** Data connection failures related to USB cables are listed.
- **Possible cause stated in source:** USB cable/data connection is implicated in the notes, but cable damage is not confirmed.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Record connected devices, operating system messages, cable/port tests, and whether the fault follows the cable or port.
- **Missing information:** Connected device; Error messages; Cable/port test results; Verified repair
- **Safety note:** Use approved cables and connection procedures; do not assume a cable replacement is a confirmed fix without testing.
- **Retrieval keywords:** USB cable failure, USB data connection, device disconnected, USB communication

### K6K-WIRING-001 — Electrical wiring short circuits
- **Category:** `electrical.wiring`
- **Reported issue:** Short circuits in the wiring harness are listed as an issue and are described as posing safety and operational risks.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Have a qualified technician inspect the wiring harness and electrical protection/fault evidence using the approved service procedure.
- **Missing information:** Affected circuit/harness; Fault evidence; Inspection findings; Repair record
- **Safety note:** Treat suspected electrical shorts as safety-critical. Do not continue operation or instruct unqualified personnel to probe live wiring.
- **Retrieval keywords:** wiring short, short circuit, wiring harness, electrical fault, burnt wire

### K6K-CAL-V1-001 — Version 1 calibration and alignment problems
- **Category:** `calibration.alignment.v1`
- **Reported issue:** Version 1 setup issues include Y-axis calibration faults, Z-height setting problems, general printing calibration errors, and mechanical alignment issues.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Separate each symptom into an individual incident with robot configuration, calibration procedure/version, measurements, logs, and verified correction.
- **Missing information:** Exact V1 configuration; Calibration error details; Axis measurements; Approved calibration procedure; Verified outcomes
- **Safety note:** Do not invent axis offsets or calibration values. Use the approved calibration procedure and qualified personnel.
- **Retrieval keywords:** Version 1, V1 calibration, Y-axis calibration, Z-height, mechanical alignment, printing calibration

### K6K-GCODE-001 — G-code generation or interpretation problems
- **Category:** `software.gcode`
- **Reported issue:** Problems occur with toolpath generation or the machine misreading G-code instructions.
- **Possible cause stated in source:** The notes mention toolpath generation or G-code interpretation as the problem area, but do not identify a specific root cause.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Collect the affected G-code file, expected versus observed path, software versions, parser/controller logs, and a safe simulation/review result.
- **Missing information:** G-code sample; Expected and actual motion; Generator/controller versions; Error logs; Verified correction
- **Safety note:** Do not execute unreviewed G-code on physical machinery. Validate changes in the approved simulation/review workflow before authorized use.
- **Retrieval keywords:** G-code error, toolpath issue, wrong path, G-code interpretation, printing path problem

### K6K-JERK-V2-001 — Version 2 jerking or vibration during printing
- **Category:** `motion.vibration.v2`
- **Reported issue:** Version 2 experiences physical jerking or violent vibrations during active printing, which can tear the concrete bead and cause structural defects.
- **Confirmed root cause:** Not supplied / not confirmed
- **Verified solution:** Not supplied
- **Verification required:** Capture the exact V2 configuration, affected toolpath, motion/drive logs, settings, and conditions. Separate observed vibration from suspected causes.
- **Missing information:** Frequency and severity; Affected axes/paths; Drive alarms; Motion settings; Verified corrective action
- **Safety note:** Unexpected violent motion is a safety concern. Stop/secure the process according to the approved procedure and keep personnel clear; do not recommend parameter changes without engineering review.
- **Retrieval keywords:** Version 2, V2 jerking, robot vibration, arm shaking, bead tearing, motion instability

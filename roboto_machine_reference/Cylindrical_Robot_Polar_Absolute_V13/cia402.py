#!/usr/bin/env python3
"""
CiA402 State Machine for Three EtherCAT Drives
Standard Position Mode - LinuxCNC handles homing motion
- is-enabled pins: True only when drive is in OPERATION_ENABLED
- Delayed enable: Holds in SWITCHED_ON state for 500ms before enabling
  to allow mux2 to propagate actual position to target position.
"""
import hal
import time
import subprocess
import sys

# CiA402 Controlword bits
CW_SWITCH_ON = 0x01
CW_ENABLE_VOLTAGE = 0x02
CW_QUICK_STOP = 0x04
CW_ENABLE_OPERATION = 0x08
CW_FAULT_RESET = 0x80

# CiA402 Statusword bits
SW_READY_TO_SWITCH_ON = 0x01
SW_SWITCHED_ON = 0x02
SW_OPERATION_ENABLED = 0x04
SW_FAULT = 0x08
SW_SWITCH_ON_DISABLED = 0x40

# Delay before transitioning from SWITCHED_ON to OPERATION_ENABLED
# This gives the servo thread time to read the real actual-position
# and feed it through mux2 to target-position, preventing a startup jump.
# 100 cycles * 5ms = 500ms
ENABLE_DELAY_CYCLES = 100

# Create HAL component
h = hal.component("cia402")

# Drive 0 - Angle
h.newpin("enable0", hal.HAL_BIT, hal.HAL_IN)
h.newpin("controlword0", hal.HAL_U32, hal.HAL_OUT)
h.newpin("statusword0", hal.HAL_U32, hal.HAL_IN)
h.newpin("is-enabled0", hal.HAL_BIT, hal.HAL_OUT)
h.newpin("is-ready0",   hal.HAL_BIT, hal.HAL_OUT)  # PDO valid + not faulted

# Drive 1 - Radius
h.newpin("enable1", hal.HAL_BIT, hal.HAL_IN)
h.newpin("controlword1", hal.HAL_U32, hal.HAL_OUT)
h.newpin("statusword1", hal.HAL_U32, hal.HAL_IN)
h.newpin("is-enabled1", hal.HAL_BIT, hal.HAL_OUT)
h.newpin("is-ready1",   hal.HAL_BIT, hal.HAL_OUT)

# Drive 2 - Z Height
h.newpin("enable2", hal.HAL_BIT, hal.HAL_IN)
h.newpin("controlword2", hal.HAL_U32, hal.HAL_OUT)
h.newpin("statusword2", hal.HAL_U32, hal.HAL_IN)
h.newpin("is-enabled2", hal.HAL_BIT, hal.HAL_OUT)
h.newpin("is-ready2",   hal.HAL_BIT, hal.HAL_OUT)

h.ready()

# --- Minimal initialization: set CSP mode only ---
print("cia402: Initializing drives...")
for slave_idx in range(3):
    try:
        subprocess.run(
            ["ethercat", "download", "-p", str(slave_idx),
             "0x6060", "0", "--type", "int8", "--", "8"],
            timeout=5, capture_output=True
        )
        print(f"cia402: Slave {slave_idx} -> CSP mode (8)")
    except Exception as e:
        print(f"cia402: WARNING - Slave {slave_idx}: {e}")
print("cia402: Initialization complete")

# Per-drive delay counters for SWITCHED_ON -> OPERATION_ENABLED transition
switched_on_counter = [0, 0, 0]


def process_drive(status, enable, drive_idx):
    """
    CiA402 state machine with delayed enable.
    Returns (controlword, is_operation_enabled)
    """
    cw = 0
    is_enabled = False
    
    # Fault handling
    if status & SW_FAULT:
        switched_on_counter[drive_idx] = 0
        cw = CW_FAULT_RESET
        return cw, False
    
    # Disabled
    if not enable:
        switched_on_counter[drive_idx] = 0
        cw = CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # Shutdown (0x06)
        return cw, False
    
    # Not ready (statusword=0, EtherCAT PDO data not valid yet)
    if status == 0:
        switched_on_counter[drive_idx] = 0
        cw = CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x06
        return cw, False
    
    # State machine to enable operation
    if status & SW_SWITCH_ON_DISABLED:
        switched_on_counter[drive_idx] = 0
        cw = CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x06
    elif (status & SW_READY_TO_SWITCH_ON) and not (status & SW_SWITCHED_ON):
        switched_on_counter[drive_idx] = 0
        cw = CW_SWITCH_ON | CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x07
    elif (status & SW_SWITCHED_ON) and not (status & SW_OPERATION_ENABLED):
        # DELAY HERE: Hold in SWITCHED_ON until counter expires
        # This lets mux2 propagate actual position to target position
        switched_on_counter[drive_idx] += 1
        if switched_on_counter[drive_idx] >= ENABLE_DELAY_CYCLES:
            cw = CW_SWITCH_ON | CW_ENABLE_VOLTAGE | CW_QUICK_STOP | CW_ENABLE_OPERATION  # 0x0F
            if drive_idx == 2:
                print(f"cia402: Drive {drive_idx} ENABLING after {switched_on_counter[drive_idx]} cycles delay")
        else:
            cw = CW_SWITCH_ON | CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x07 - stay in SWITCHED_ON
    elif status & SW_OPERATION_ENABLED:
        cw = CW_SWITCH_ON | CW_ENABLE_VOLTAGE | CW_QUICK_STOP | CW_ENABLE_OPERATION  # 0x0F
        is_enabled = True
    else:
        switched_on_counter[drive_idx] = 0
        cw = CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # Default shutdown
    
    return cw, is_enabled

try:
    loop_count = 0
    while True:
        # Process Drive 0
        status0 = h['statusword0']
        cw0, en0 = process_drive(status0, h['enable0'], 0)
        h['controlword0'] = cw0
        h['is-enabled0'] = en0
        h['is-ready0'] = (status0 != 0) and not (status0 & SW_FAULT)

        # Process Drive 1
        status1 = h['statusword1']
        cw1, en1 = process_drive(status1, h['enable1'], 1)
        h['controlword1'] = cw1
        h['is-enabled1'] = en1
        h['is-ready1'] = (status1 != 0) and not (status1 & SW_FAULT)

        # Process Drive 2
        status2 = h['statusword2']
        cw2, en2 = process_drive(status2, h['enable2'], 2)
        h['controlword2'] = cw2
        h['is-enabled2'] = en2
        h['is-ready2'] = (status2 != 0) and not (status2 & SW_FAULT)
        
        # Debug: Print ALL drive states every 2 seconds (~400 loops at 5ms)
        loop_count += 1
        if loop_count % 400 == 0:
            drive_names = ["Angle(J0)", "Radius(J1)", "Z-Height(J2)"]
            statuses = [status0, status1, status2]
            enables = [en0, en1, en2]
            
            parts = []
            for i in range(3):
                sw = statuses[i]
                if sw & SW_FAULT:
                    state = "❌FAULT"
                elif sw & SW_OPERATION_ENABLED:
                    state = "✅READY"
                elif sw & SW_SWITCHED_ON:
                    state = f"⏳SWITCHING({switched_on_counter[i]}/{ENABLE_DELAY_CYCLES})"
                elif sw & SW_READY_TO_SWITCH_ON:
                    state = "🔄READY_TO_SWITCH"
                elif sw & SW_SWITCH_ON_DISABLED:
                    state = "⬜DISABLED"
                elif sw == 0:
                    state = "⚫NOT_READY"
                else:
                    state = f"❓UNKNOWN(0x{sw:04x})"
                parts.append(f"{drive_names[i]}={state}")
            
            print(f"cia402: {' | '.join(parts)}")
        
        time.sleep(0.005)

except KeyboardInterrupt:
    raise SystemExit

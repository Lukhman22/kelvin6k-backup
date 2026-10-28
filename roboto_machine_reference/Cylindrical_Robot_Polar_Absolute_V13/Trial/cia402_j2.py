#!/usr/bin/env python3
"""
CiA402 State Machine for J2 (Slave 2 - SV670N)
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

# Create HAL component
h = hal.component("cia402_j2")

# Drive 2 - Z Height (This is the only one we care about for this test)
h.newpin("enable", hal.HAL_BIT, hal.HAL_IN)
h.newpin("controlword", hal.HAL_U32, hal.HAL_OUT)
h.newpin("statusword", hal.HAL_U32, hal.HAL_IN)
h.newpin("reset", hal.HAL_BIT, hal.HAL_IN)

h.ready()

# --- Initialization: set CSP mode for Slave 2 ---
print("cia402_j2: Initializing Slave 2...")
try:
    # Set Mode of Operation (0x6060) to 8 (CSP - Cyclic Synchronous Position)
    subprocess.run(
        ["ethercat", "download", "-p", "2",
         "0x6060", "0", "--type", "int8", "8"],
        timeout=5, check=True
    )
    print("cia402_j2: Slave 2 -> CSP mode (8)")
except Exception as e:
    print(f"cia402_j2: WARNING - Slave 2 init failed: {e}")

print("cia402_j2: Initialization complete")

def process_drive(status, enable, reset):
    """
    Standard CiA402 state machine
    """
    cw = 0
    
    # Fault handling
    if status & SW_FAULT:
        if reset:
            cw = CW_FAULT_RESET
        return cw
    
    # Disabled
    if not enable:
        cw = CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # Shutdown (0x06)
        return cw
    
    # State machine to enable operation
    if status & SW_SWITCH_ON_DISABLED:
        cw = CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x06
    elif (status & SW_READY_TO_SWITCH_ON) and not (status & SW_SWITCHED_ON):
        cw = CW_SWITCH_ON | CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x07
    elif (status & SW_SWITCHED_ON) and not (status & SW_OPERATION_ENABLED):
        cw = CW_SWITCH_ON | CW_ENABLE_VOLTAGE | CW_QUICK_STOP | CW_ENABLE_OPERATION  # 0x0F
    elif status & SW_OPERATION_ENABLED:
        cw = CW_SWITCH_ON | CW_ENABLE_VOLTAGE | CW_QUICK_STOP | CW_ENABLE_OPERATION  # 0x0F
    else:
        cw = CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # Default shutdown
    
    return cw

try:
    while True:
        status = h['statusword']
        enable = h['enable']
        reset = h['reset']
        
        h['controlword'] = process_drive(status, enable, reset)
        
        time.sleep(0.005)

except KeyboardInterrupt:
    raise SystemExit

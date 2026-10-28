#!/usr/bin/env python3
"""
Scale Factor Finder for SV660 Motor
Reads raw encoder counts from EtherCAT to determine correct scale

Usage:
1. LinuxCNC should NOT be running
2. EtherCAT master should be running
3. Manually rotate motor shaft and observe counts
"""

import subprocess
import time
import sys

def get_encoder_position(slave_id=1):
    """Read actual position from EtherCAT slave"""
    try:
        result = subprocess.run(
            ['sudo', 'ethercat', 'upload', '-p', str(slave_id), '0x6064', '0'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Parse hex value
            output = result.stdout.strip()
            if '0x' in output:
                value = int(output.split('0x')[1].split()[0], 16)
                # Handle signed 32-bit
                if value > 0x7FFFFFFF:
                    value -= 0x100000000
                return value
        return None
    except Exception as e:
        print(f"Error reading position: {e}")
        return None

def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              SCALE FACTOR FINDER                               ║
║                                                                 ║
║  This tool reads raw encoder counts from your motor.           ║
║  Use it to find the correct scale factor.                      ║
║                                                                 ║
║  INSTRUCTIONS:                                                  ║
║  1. Stop LinuxCNC if running                                    ║
║  2. Mark the motor shaft (put tape/marker on it)               ║
║  3. Run this script                                             ║
║  4. Manually rotate the shaft exactly ONE FULL TURN (360°)     ║
║  5. Read the count difference - that's counts per revolution   ║
║                                                                 ║
║  SCALE CALCULATION:                                             ║
║    feedback_gain = 360 / counts_per_revolution                 ║
║    command_gain  = counts_per_revolution / 360                 ║
║                                                                 ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    slave_id = 1  # Second drive
    
    print(f"Reading from EtherCAT Slave {slave_id}...")
    print("Press Ctrl+C to stop\n")
    
    initial_pos = get_encoder_position(slave_id)
    if initial_pos is None:
        print("ERROR: Could not read encoder position!")
        print("Make sure:")
        print("  - EtherCAT master is running: sudo systemctl start ethercat")
        print("  - Slave is detected: sudo ethercat slaves")
        print("  - You have sudo access")
        return
    
    print(f"Initial position: {initial_pos:,} counts")
    print("\n>>> Rotate the motor shaft ONE FULL TURN (360°) <<<\n")
    
    try:
        while True:
            pos = get_encoder_position(slave_id)
            if pos is not None:
                diff = pos - initial_pos
                
                # Calculate suggested scales
                if diff != 0:
                    fb_scale = 360.0 / abs(diff)
                    cmd_scale = abs(diff) / 360.0
                else:
                    fb_scale = 0
                    cmd_scale = 0
                
                print(f"\rCurrent: {pos:>12,}  |  Diff: {diff:>10,}  |  "
                      f"fb_scale: {fb_scale:.6f}  cmd_scale: {cmd_scale:.2f}", end='')
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        final_pos = get_encoder_position(slave_id)
        if final_pos:
            total_diff = final_pos - initial_pos
            
            print(f"\n\n{'='*60}")
            print(f"FINAL RESULTS")
            print(f"{'='*60}")
            print(f"Initial position:  {initial_pos:>12,}")
            print(f"Final position:    {final_pos:>12,}")
            print(f"Total difference:  {total_diff:>12,} counts")
            print(f"{'='*60}")
            
            if total_diff != 0:
                fb_scale = 360.0 / abs(total_diff)
                cmd_scale = abs(total_diff) / 360.0
                
                print(f"\nSUGGESTED SCALE FACTORS:")
                print(f"  setp scale.2.gain {fb_scale:.6f}   # feedback")
                print(f"  setp scale.3.gain {cmd_scale:.2f}       # command")
                
                print(f"\nFOR INI FILE:")
                print(f"  SCALE = {cmd_scale:.2f}")
            else:
                print("\nNo movement detected!")

if __name__ == '__main__':
    main()

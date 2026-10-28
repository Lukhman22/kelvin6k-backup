#!/usr/bin/env python3
"""
PWM Controller HAL Component for LinuxCNC
Controls 3 PWM outputs via serial communication with ESP32 or Arduino

No enable pins — PWM value alone controls output (0.0 = stopped, 1.0 = full speed).
S-ON is handled by drive parameter H03.00=1 (auto-enable at power-on).

HAL Pins:
    pwm-ctrl.extruder (FLOAT IN) - 0.0-1.0 for extruder speed
    pwm-ctrl.pump (FLOAT IN) - 0.0-1.0 for pump/VFD speed
    pwm-ctrl.fluid-pump (FLOAT IN) - 0.0-1.0 for fluid pump speed
    pwm-ctrl.connected (BIT OUT) - Connection status

Usage in HAL:
    loadusr -Wn pwm-ctrl ./pwm_controller.py
"""

import hal
import serial
import serial.tools.list_ports
import time
import sys

# Configuration
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
UPDATE_RATE = 20  # Hz (50ms between updates)
RECONNECT_DELAY = 2.0  # seconds
HEARTBEAT_INTERVAL = 0.5  # seconds

class PWMController:
    def __init__(self):
        self.serial_port = None
        self.last_update = 0
        self.last_heartbeat = 0
        self.connected = False
        self.pwm_max = 255  # Default Arduino 8-bit; ESP32 sets to 65535
        self.board_type = "unknown"
        
        # Track last sent values to avoid unnecessary communication
        self.last_pwm = [None, None, None]
        
        # Create HAL component
        self.hal = hal.component("pwm-ctrl")
        
        # PWM value pins (0.0 - 1.0)
        self.hal.newpin("extruder", hal.HAL_FLOAT, hal.HAL_IN)
        self.hal.newpin("pump", hal.HAL_FLOAT, hal.HAL_IN)
        self.hal.newpin("fluid-pump", hal.HAL_FLOAT, hal.HAL_IN)
        
        # Status output
        self.hal.newpin("connected", hal.HAL_BIT, hal.HAL_OUT)
        
        # Mark component ready
        self.hal.ready()
        print("pwm-ctrl: HAL component initialized")
    
    def find_device(self):
        """Find ESP32 or Arduino serial port automatically"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            desc = port.description.lower()
            # ESP32 identifiers (check first — preferred board)
            if 'cp210' in desc or 'cp2102' in desc or \
               'silicon labs' in desc or \
               (port.vid == 0x10C4 and port.pid == 0xEA60):
                self.board_type = "esp32"
                self.pwm_max = 65535  # 16-bit
                return port.device
            # Arduino identifiers (fallback)
            if 'arduino' in desc or \
               'ch340' in desc or \
               'usb2.0-serial' in desc or \
               'ttyUSB' in port.device or \
               'ttyACM' in port.device:
                self.board_type = "arduino"
                self.pwm_max = 255  # 8-bit
                return port.device
        return None
    
    def connect(self):
        """Establish connection to ESP32 or Arduino"""
        port = self.find_device()
        if port is None:
            print("pwm-ctrl: No ESP32/Arduino found, retrying...")
            return False
        
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=SERIAL_BAUDRATE,
                timeout=SERIAL_TIMEOUT
            )
            time.sleep(2)  # Wait for device reset
            
            # Check for READY message (don't clear buffer first!)
            start = time.time()
            while time.time() - start < 3:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if 'READY' in line:
                        print(f"pwm-ctrl: Connected to {self.board_type} on {port} (PWM max={self.pwm_max})")
                        self.connected = True
                        self.hal["connected"] = True
                        return True
            
            # Fallback: READY message may have been missed, try heartbeat
            self.serial_port.reset_input_buffer()
            self.serial_port.write(b"H\n")
            time.sleep(0.3)
            if self.serial_port.in_waiting:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                if 'OK' in line:
                    print(f"pwm-ctrl: Connected to {self.board_type} on {port} (via heartbeat, PWM max={self.pwm_max})")
                    self.connected = True
                    self.hal["connected"] = True
                    return True
            
            print(f"pwm-ctrl: Device on {port} not responding")
            self.serial_port.close()
            return False
            
        except serial.SerialException as e:
            print(f"pwm-ctrl: Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.connected = False
        self.hal["connected"] = False
        self.last_pwm = [None, None, None]
    
    def send_command(self, cmd):
        """Send command to device"""
        if not self.connected:
            return None
        try:
            self.serial_port.write(f"{cmd}\n".encode())
            response = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
            return response
        except (serial.SerialException, OSError) as e:
            print(f"pwm-ctrl: Communication error: {e}")
            self.disconnect()
            return None
    
    def update(self):
        """Update PWM values from HAL pins"""
        now = time.time()
        
        # Rate limit updates
        if now - self.last_update < 1.0 / UPDATE_RATE:
            return
        self.last_update = now
        
        # Read HAL pins and convert to PWM range
        pwm_values = [
            int(max(0, min(1, self.hal["extruder"])) * self.pwm_max),
            int(max(0, min(1, self.hal["pump"])) * self.pwm_max),
            int(max(0, min(1, self.hal["fluid-pump"])) * self.pwm_max)
        ]
        
        # Send updates only if values changed
        for i in range(3):
            if pwm_values[i] != self.last_pwm[i]:
                resp = self.send_command(f"P{i}:{pwm_values[i]}")
                if resp and resp.startswith("OK"):
                    self.last_pwm[i] = pwm_values[i]
        
        # Send heartbeat periodically
        if now - self.last_heartbeat > HEARTBEAT_INTERVAL:
            self.send_command("H")
            self.last_heartbeat = now
    
    def run(self):
        """Main loop"""
        print("pwm-ctrl: Starting main loop")
        
        while True:
            try:
                if not self.connected:
                    if not self.connect():
                        time.sleep(RECONNECT_DELAY)
                        continue
                
                self.update()
                time.sleep(0.01)  # Small sleep to prevent CPU hogging
                
            except KeyboardInterrupt:
                print("pwm-ctrl: Shutting down")
                # Stop all outputs
                for i in range(3):
                    self.send_command(f"P{i}:0")
                self.disconnect()
                break

if __name__ == "__main__":
    try:
        component = PWMController()
        component.run()
    except Exception as e:
        print(f"pwm-ctrl: Fatal error: {e}")
        sys.exit(1)

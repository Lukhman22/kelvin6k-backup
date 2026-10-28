# LinuxCNC + EtherCAT Complete Setup Guide
## From Fresh Debian Install to Running Motors

> This guide is based on a **working** Inovance SV660N setup with LinuxCNC 2.9.4 on Debian 12 Bookworm.

---

## 1. System Requirements

| Component | Specification |
|-----------|--------------|
| **OS** | Debian 12 (Bookworm) |
| **Kernel** | PREEMPT_RT (e.g., `6.1.0-30-rt-amd64`) |
| **LinuxCNC** | 2.9.4 uspace |
| **EtherCAT Master** | IgH EtherCAT Master 1.6.x |
| **EtherCAT HAL** | linuxcnc-ethercat (lcec) |
| **Network Card** | Dedicated Ethernet port (not WiFi) |
| **Servo Drives** | CiA402-compatible (Inovance SV660N/SV670P, etc.) |

---

## 2. Install Debian 12 with RT Kernel

### Step 1: Install Debian 12 Bookworm
Download from https://www.debian.org/download and do a standard install.

### Step 2: Install the PREEMPT_RT Kernel
```bash
sudo apt update
sudo apt install linux-image-rt-amd64 linux-headers-rt-amd64
sudo reboot
```

### Step 3: Verify RT Kernel
```bash
uname -r
# Should show something like: 6.1.0-30-rt-amd64
```

---

## 3. Install LinuxCNC

### Step 1: Add LinuxCNC Repository
```bash
# Add the LinuxCNC signing key
sudo apt install curl
curl -s http://linuxcnc.org/dists/bookworm/Release.gpg.key | sudo apt-key add -

# Add the repository
echo "deb http://linuxcnc.org/dists/bookworm bookworm base 2.9-uspace" | \
    sudo tee /etc/apt/sources.list.d/linuxcnc.list

sudo apt update
```

### Step 2: Install LinuxCNC
```bash
sudo apt install linuxcnc-uspace linuxcnc-uspace-dev linuxcnc-doc-en
```

### Step 3: Verify Installation
```bash
linuxcnc --version
# Should show: LINUXCNC - 2.9.4
```

---

## 4. Install IgH EtherCAT Master

### Option A: From Debian Package (Recommended)
```bash
# If packages are available from your distribution:
sudo apt install ethercat-master ethercat-dkms libethercat libethercat-dev
```

### Option B: Build from Source
```bash
# Install build dependencies
sudo apt install git autoconf libtool pkg-config linux-headers-$(uname -r)

# Clone IgH EtherCAT Master
git clone https://gitlab.com/etherlab.org/ethercat.git
cd ethercat

# Build
./bootstrap
./configure --prefix=/usr/local \
    --with-linux-dir=/usr/src/linux-headers-$(uname -r) \
    --enable-generic \
    --disable-8139too
make -j$(nproc)
sudo make install

# Install kernel modules
sudo depmod
```

### Configure EtherCAT Master
```bash
# Find your Ethernet port MAC address
ip link show
# Look for the port connected to the servo drives (NOT your WiFi/internet port)
# Example output: link/ether 1c:69:7a:d9:18:1d

# Edit EtherCAT config
sudo nano /etc/ethercat.conf
```

Set the following in `/etc/ethercat.conf`:
```ini
# Replace with YOUR Ethernet port's MAC address
MASTER0_DEVICE="1c:69:7a:d9:18:1d"

# Use generic driver (works with any Ethernet card)
DEVICE_MODULES="generic"
```

### Start and Enable EtherCAT Master
```bash
# Start the service
sudo systemctl start ethercat
sudo systemctl enable ethercat

# Verify it's running
ethercat master
# Should show: Master0  Phase: Idle
```

---

## 5. Install LinuxCNC-EtherCAT (lcec)

```bash
# If available as package:
sudo apt install linuxcnc-ethercat

# OR build from source:
git clone https://github.com/linuxcnc-ethercat/linuxcnc-ethercat.git
cd linuxcnc-ethercat
make
sudo make install
```

### Verify Installation
```bash
# Check lcec module is available
ls /usr/lib/linuxcnc/modules/lcec.so
# Should exist

# Check lcec_conf tool
which lcec_conf
# Should show path
```

---

## 6. Connect and Scan EtherCAT Slaves

### Physical Wiring

```
┌──────────────┐     Ethernet Cable     ┌──────────────┐     ┌──────────────┐
│  LinuxCNC PC │ ────────────────────►   │  Drive 0     │────►│  Drive 1     │
│  (Ethernet)  │                         │  (SV660N)    │     │  (SV660N)    │
│              │                         │  EtherCAT IN │     │  EtherCAT IN │
└──────────────┘                         └──────────────┘     └──────────────┘
                                          Slave 0 (Angle)      Slave 1 (Radius)
```

- Use **standard Ethernet cables** (Cat5e or better)
- Connect PC Ethernet → Drive 0 IN
- Daisy chain: Drive 0 OUT → Drive 1 IN
- Drive 1 OUT → (empty, or next drive)

### Scan for Slaves
```bash
# Power on all drives, then scan
ethercat slaves
# Expected output:
# 0  0:0  PREOP  +  Inovance SV660N
# 1  0:1  PREOP  +  Inovance SV660N

# Get detailed info about a slave
ethercat slave -p 0 --verbose
# Shows vendor ID, product code, PDO mapping, etc.

# Get PDO info (CRITICAL for ethercat-conf.xml)
ethercat pdos -p 0
# Shows available PDO entries and their indices
```

> [!IMPORTANT]
> **Write down the Vendor ID and Product ID from `ethercat slaves -v`!**
> For Inovance SV660N: `VID=0x00100000`, `PID=0x000c010d`
> You'll need these for `ethercat-conf.xml`.

---

## 7. Configuration Files

All config files go in:
```
~/linuxcnc/configs/your_machine_name/
```

### Directory Structure
```
~/linuxcnc/configs/cylindrical_robot/
├── cylindrical_robot.ini      ← Main INI config (joints, axes, display)
├── cylindrical_robot.hal      ← HAL wiring (connects everything)
├── ethercat-conf.xml          ← EtherCAT PDO mapping (slave config)
├── cia402.py                  ← CiA402 state machine (drive enable/disable)
├── tool.tbl                   ← Tool table
└── linuxcnc.var               ← Persistent variables
```

---

### File 1: `ethercat-conf.xml` — EtherCAT Slave PDO Mapping

This tells LinuxCNC exactly what data to exchange with each drive.

```xml
<masters>
  <master idx="0" appTimePeriod="1000000" refClockSyncCycles="1">

    <!-- Slave 0: First Drive -->
    <slave idx="0" type="generic" vid="0x00100000" pid="0x000c010d">
      <dcConf assignActivate="0x0300" sync0Cycle="*1" sync0Shift="0"/>

      <!-- Output PDOs (PC → Drive): SyncManager 2 -->
      <syncManager idx="2" dir="out">
        <pdo idx="1701">
          <pdoEntry idx="6040" subIdx="0" bitLen="16"
                    halPin="cia-controlword" halType="u32"/>
          <pdoEntry idx="607a" subIdx="0" bitLen="32"
                    halPin="target-position" halType="s32"/>
          <pdoEntry idx="60b8" subIdx="0" bitLen="16"
                    halPin="probe-control" halType="u32"/>
          <pdoEntry idx="60fe" subIdx="1" bitLen="32"
                    halPin="digital-outputs" halType="u32"/>
        </pdo>
      </syncManager>

      <!-- Input PDOs (Drive → PC): SyncManager 3 -->
      <syncManager idx="3" dir="in">
        <pdo idx="1b01">
          <pdoEntry idx="603f" subIdx="0" bitLen="16"
                    halPin="error-code" halType="u32"/>
          <pdoEntry idx="6041" subIdx="0" bitLen="16"
                    halPin="cia-statusword" halType="u32"/>
          <pdoEntry idx="6064" subIdx="0" bitLen="32"
                    halPin="actual-position" halType="s32"/>
          <pdoEntry idx="6077" subIdx="0" bitLen="16"
                    halPin="torque-actual" halType="s32"/>
          <pdoEntry idx="60f4" subIdx="0" bitLen="32"
                    halPin="following-error" halType="s32"/>
          <pdoEntry idx="60b9" subIdx="0" bitLen="16"
                    halPin="probe-status" halType="u32"/>
          <pdoEntry idx="60ba" subIdx="0" bitLen="32"
                    halPin="probe-pos-1" halType="s32"/>
          <pdoEntry idx="60bc" subIdx="0" bitLen="32"
                    halPin="probe-pos-2" halType="s32"/>
          <pdoEntry idx="60fd" subIdx="0" bitLen="32"
                    halPin="digital-inputs" halType="u32"/>
        </pdo>
      </syncManager>
    </slave>

    <!-- Slave 1: Second Drive (same structure) -->
    <slave idx="1" type="generic" vid="0x00100000" pid="0x000c010d">
      <!-- Same dcConf, syncManager, pdo structure as Slave 0 -->
      <!-- Copy the entire slave 0 block and change idx="1" -->
    </slave>

  </master>
</masters>
```

> [!CAUTION]
> **PDO mapping MUST match your drive's fixed PDO assignment exactly.**
> Wrong PDO indices = `EE09.3` error on the drive.
> Use `ethercat pdos -p 0` to see your drive's actual PDO mapping.

**Key CiA402 PDO Objects:**

| Object Index | Name | Direction | Purpose |
|:---:|---|:---:|---|
| 0x6040 | Controlword | OUT | Enable/disable drive |
| 0x607A | Target Position | OUT | Position command |
| 0x6041 | Statusword | IN | Drive state feedback |
| 0x6064 | Actual Position | IN | Encoder position |
| 0x60FD | Digital Inputs | IN | Limit switches, etc. |

---

### File 2: `cia402.py` — CiA402 State Machine

This Python script manages the drive enable/disable sequence:
```
Switch On Disabled → Ready to Switch On → Switched On → Operation Enabled
```

```python
#!/usr/bin/env python3
"""CiA402 State Machine for EtherCAT Drives"""
import hal, time

# Controlword bits
CW_SWITCH_ON        = 0x01
CW_ENABLE_VOLTAGE   = 0x02
CW_QUICK_STOP       = 0x04
CW_ENABLE_OPERATION = 0x08
CW_FAULT_RESET      = 0x80

# Statusword bits
SW_READY_TO_SWITCH_ON = 0x01
SW_SWITCHED_ON        = 0x02
SW_OPERATION_ENABLED  = 0x04
SW_FAULT              = 0x08
SW_SWITCH_ON_DISABLED = 0x40

h = hal.component("cia402")

# Create pins for each drive (add more for additional drives)
for i in range(2):  # 2 drives
    h.newpin(f"enable{i}", hal.HAL_BIT, hal.HAL_IN)
    h.newpin(f"controlword{i}", hal.HAL_U32, hal.HAL_OUT)
    h.newpin(f"statusword{i}", hal.HAL_U32, hal.HAL_IN)

h.ready()

def process_drive(status, enable):
    if status & SW_FAULT:
        return CW_FAULT_RESET
    if not enable:
        return CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x06 Shutdown
    if status & SW_SWITCH_ON_DISABLED:
        return CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x06
    elif (status & SW_READY_TO_SWITCH_ON) and not (status & SW_SWITCHED_ON):
        return CW_SWITCH_ON | CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # 0x07
    elif (status & SW_SWITCHED_ON) and not (status & SW_OPERATION_ENABLED):
        return 0x0F  # Enable operation
    elif status & SW_OPERATION_ENABLED:
        return 0x0F  # Stay enabled
    return CW_ENABLE_VOLTAGE | CW_QUICK_STOP  # Default shutdown

try:
    while True:
        for i in range(2):
            h[f'controlword{i}'] = process_drive(h[f'statusword{i}'], h[f'enable{i}'])
        time.sleep(0.005)
except KeyboardInterrupt:
    raise SystemExit
```

Make it executable:
```bash
chmod +x cia402.py
```

---

### File 3: `cylindrical_robot.hal` — HAL Configuration

This is the central wiring file that connects EtherCAT, motion controller, and CiA402.

```hal
# --- EtherCAT Configuration ---
loadusr -W lcec_conf ethercat-conf.xml

# --- Load Realtime Components ---
loadrt [KINS]KINEMATICS
loadrt [EMCMOT]EMCMOT servo_period_nsec=[EMCMOT]SERVO_PERIOD num_joints=[KINS]JOINTS
loadrt lcec
loadrt scale count=4
loadrt conv_float_s32 count=2
loadrt conv_s32_float count=2

# --- Add Functions to Servo Thread ---
addf lcec.read-all servo-thread
addf conv-s32-float.0 servo-thread
addf scale.0 servo-thread
addf conv-s32-float.1 servo-thread
addf scale.2 servo-thread
addf motion-command-handler servo-thread
addf motion-controller servo-thread
addf scale.1 servo-thread
addf conv-float-s32.0 servo-thread
addf scale.3 servo-thread
addf conv-float-s32.1 servo-thread
addf lcec.write-all servo-thread

# --- CiA402 State Machine ---
loadusr -W ./cia402.py

# ============================================================
# JOINT 0: Angle Drive (Slave 0)
# SCALE = encoder_pulses_per_revolution / 360 degrees
# ============================================================

net angle-enable joint.0.amp-enable-out => cia402.enable0

# Feedback: lcec(s32) → float → scale → joint
net angle-pos-fb-raw lcec.0.0.actual-position => conv-s32-float.0.in
net angle-pos-fb-f   conv-s32-float.0.out     => scale.0.in
setp scale.0.gain    0.000590277778            # 1/1694.4444
net angle-pos-fb     scale.0.out              => joint.0.motor-pos-fb

# Command: joint → scale → s32 → lcec
net angle-pos-cmd    joint.0.motor-pos-cmd    => scale.1.in
setp scale.1.gain    1694.4444                 # encoder_counts_per_degree
net angle-pos-cmd-s  scale.1.out              => conv-float-s32.0.in
net angle-pos-cmd-raw conv-float-s32.0.out    => lcec.0.0.target-position

# CiA402 wiring
net status-word0  lcec.0.0.cia-statusword => cia402.statusword0
net control-word0 cia402.controlword0     => lcec.0.0.cia-controlword

# ============================================================
# JOINT 1: Radius Drive (Slave 1)
# ============================================================
# (Same pattern as Joint 0, but with the radius scale)

# --- E-Stop Loopback ---
net estop-loop iocontrol.0.user-enable-out => iocontrol.0.emc-enable-in
```

---

### File 4: `cylindrical_robot.ini` — Main Configuration

```ini
[EMC]
VERSION = 1.1
MACHINE = My_CNC_Machine
DEBUG = 0

[DISPLAY]
DISPLAY = axis
DEFAULT_LINEAR_VELOCITY = 50.0
MAX_LINEAR_VELOCITY = 200.0

[EMCMOT]
EMCMOT = motmod
COMM_TIMEOUT = 1.0
SERVO_PERIOD = 1000000     # 1ms servo cycle (matches EtherCAT)

[TASK]
TASK = milltask
CYCLE_TIME = 0.010

[HAL]
HALFILE = cylindrical_robot.hal

[TRAJ]
COORDINATES = X Y           # Your axes
LINEAR_UNITS = mm
MAX_LINEAR_VELOCITY = 200.0

[EMCIO]
EMCIO = io
CYCLE_TIME = 0.100
TOOL_TABLE = tool.tbl

[KINS]
KINEMATICS = trivkins coordinates=XY   # Or polarkins for polar
JOINTS = 2

[JOINT_0]
TYPE = LINEAR                # ANGULAR for rotary axis
MAX_VELOCITY = 100.0
MAX_ACCELERATION = 500.0
SCALE = 100.0                # encoder_counts_per_unit
FERROR = 100.0               # Following error limit
MIN_FERROR = 50.0
HOME = 0.0
HOME_OFFSET = 0.0
HOME_SEARCH_VEL = -10.0     # Homing search speed
HOME_LATCH_VEL = 5.0        # Homing latch speed
HOME_SEQUENCE = 0

[JOINT_1]
TYPE = LINEAR
MAX_VELOCITY = 100.0
MAX_ACCELERATION = 500.0
SCALE = 100.0
FERROR = 100.0
MIN_FERROR = 50.0
HOME = 0.0
HOME_OFFSET = 0.0
HOME_SEARCH_VEL = -10.0
HOME_LATCH_VEL = 5.0
HOME_SEQUENCE = 1
```

---

## 8. First Boot Checklist

```
Before launching LinuxCNC:

 1. ☐ RT kernel is booted (uname -r shows "-rt")
 2. ☐ EtherCAT master is running (sudo systemctl status ethercat)
 3. ☐ Drives are powered on and connected via Ethernet
 4. ☐ Slaves are detected (ethercat slaves)
 5. ☐ ethercat-conf.xml PDOs match your drives (ethercat pdos -p 0)
 6. ☐ cia402.py is executable (chmod +x cia402.py)
 7. ☐ All config files in ~/linuxcnc/configs/your_machine/
```

### Launch LinuxCNC
```bash
linuxcnc ~/linuxcnc/configs/cylindrical_robot/cylindrical_robot.ini
```

---

## 9. Troubleshooting

### EtherCAT Issues

| Problem | Command/Solution |
|---------|-----------------|
| No slaves found | `ethercat slaves` — check cables, power |
| Slaves stuck in PREOP | Check ethercat-conf.xml PDO mapping |
| **EE09.3 error** on drive | PDO mismatch — use `ethercat pdos -p 0` to verify |
| Master not starting | `sudo systemctl restart ethercat` |
| Wrong Ethernet port | Check MAC in `/etc/ethercat.conf` |

### LinuxCNC Issues

| Problem | Solution |
|---------|---------|
| `lcec: no slaves` | EtherCAT master not running |
| Following error | Increase `FERROR` in INI, check `SCALE` |
| Joint won't enable | Check cia402.py is running, check statusword |
| Position jumps | SCALE value is wrong |

### Useful Debug Commands
```bash
# Check EtherCAT master status
ethercat master

# List slaves and their states
ethercat slaves

# Read slave PDO mapping (CRITICAL)
ethercat pdos -p 0

# Read a slave's SDO (parameter)
ethercat upload -p 0 0x6041 0    # Read statusword

# Write a slave's SDO
ethercat download -p 0 0x6060 0 8   # Set mode of operation

# Monitor HAL pins in real-time
halcmd show pin lcec*
halcmd show pin cia402*

# Watch a pin value
watch halcmd getp lcec.0.0.cia-statusword
```

---

## 10. How the Data Flows

```
                         EtherCAT Bus (1ms cycle)
                    ┌────────────────────────────────┐
                    │                                │
┌───────────┐    ┌──▼──────────┐    ┌────────────┐   │    ┌──────────┐
│ G-code    │    │ LinuxCNC    │    │ lcec       │   │    │ SV660N   │
│ Program   │───►│ Motion      │───►│ EtherCAT   │───┼───►│ Drive    │───► Motor
│           │    │ Controller  │    │ HAL Driver │   │    │ (CiA402) │
└───────────┘    └──────┬──────┘    └────────────┘   │    └──────────┘
                        │                            │
                   ┌────▼────┐                       │
                   │ cia402  │    Statusword ◄────────┘
                   │ .py     │    Controlword ────────►
                   └─────────┘
```

**Per servo cycle (every 1ms):**
1. `lcec.read-all` reads encoder position + statusword from drives
2. Position is scaled and fed to `joint.X.motor-pos-fb`
3. Motion controller calculates new position command
4. Command is scaled and sent to `lcec.0.X.target-position`
5. `cia402.py` manages drive state (enable/disable/fault reset)
6. `lcec.write-all` sends controlword + target position to drives

---

## 11. Quick Reference: Key Files

| File | Location | Purpose |
|------|----------|---------|
| **ethercat.conf** | `/etc/ethercat.conf` | EtherCAT master config (MAC, driver) |
| **INI file** | `~/linuxcnc/configs/machine/` | Machine parameters (joints, axes, limits) |
| **HAL file** | `~/linuxcnc/configs/machine/` | Signal wiring between components |
| **ethercat-conf.xml** | `~/linuxcnc/configs/machine/` | PDO mapping for each slave drive |
| **cia402.py** | `~/linuxcnc/configs/machine/` | Drive state machine |
| **tool.tbl** | `~/linuxcnc/configs/machine/` | Tool offset definitions |
| **linuxcnc.var** | `~/linuxcnc/configs/machine/` | Persistent G-code variables |

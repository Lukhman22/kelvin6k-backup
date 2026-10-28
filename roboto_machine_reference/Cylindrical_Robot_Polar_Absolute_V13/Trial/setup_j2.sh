#!/bin/bash
# Script to manually configure Inovance SV670I (Slave 1) PDOs
# and launch LinuxCNC.
# This bypasses lcec SDO configuration issues.

echo "--- stopping existing linuxcnc ---"
linuxcnc -k
pkill -9 linuxcnc
pkill -9 halcmd
sleep 2

echo "--- resetting ethercat states to PREOP ---"
sudo ethercat states PREOP
sleep 2

echo "--- configuring Slave 1 (SV670I) PDOs ---"
# Slave 1 is at alias 0, position 1
SLAVE_POS=1

# Check if slave is present
if ! ethercat slaves | grep -q "1:1"; then
    echo "ERROR: Slave 1 not found!"
    exit 1
fi

# 1. Clear Sync Managers
sudo ethercat download -p $SLAVE_POS 0x1c12 0 0 --type uint8
sudo ethercat download -p $SLAVE_POS 0x1c13 0 0 --type uint8

# 2. Assign RxPDO 0x1701
sudo ethercat download -p $SLAVE_POS 0x1c12 1 0x1701 --type uint16
sudo ethercat download -p $SLAVE_POS 0x1c12 0 1 --type uint8

# 3. Assign TxPDO 0x1b01
sudo ethercat download -p $SLAVE_POS 0x1c13 1 0x1b01 --type uint16
sudo ethercat download -p $SLAVE_POS 0x1c13 0 1 --type uint8

echo "--- Slave 1 Configured. Current State: ---"
ethercat slaves | grep "1:1"

echo "--- Starting LinuxCNC ---"
# Ensure we don't start linuxcnc as root if script is run closely
linuxcnc /home/kelvin6k/linuxcnc/configs/cylindrical_robot/test_j2.ini

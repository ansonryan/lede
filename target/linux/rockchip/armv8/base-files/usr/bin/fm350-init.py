#!/usr/bin/env python3

import sys
import os
import time
import serial
import threading
import subprocess
import psutil

os_is_openwrt = False

fm350_idproduct = 0x7127
fm350_idvendor = 0x0e8d

class SerialReader:
    def __init__(self, port, baudrate=115200):
        self.rbuffer = str()
        self.rbuffer_lock = threading.Lock()
        self.thread = None
        self.ser = None

        try:
            self.ser = serial.Serial(port, baudrate, timeout=0)
            self.running = True
            # Create and start the thread
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
        except Exception as e:
            print(e)

    def _read_loop(self):
        if self.ser is None:
            return

        while self.running:
            if self.ser.in_waiting > 0:
                data = self.ser.readall().decode('utf-8')

                with self.rbuffer_lock:
                    if len(self.rbuffer) > 1048576:
                        self.rbuffer = str()

                    self.rbuffer += data

            time.sleep(0.01)

    def send_data(self, message):
        if self.ser is None:
            return

        self.ser.write(f"{message}\r\n".encode('utf-8'))

    def recv_data(self):
        ret = str()
        with self.rbuffer_lock:
            ret = self.rbuffer
            self.rbuffer = str()

        return ret

    def recv_data_with_timeout(self, timeout=1):
        ret = str()
        start_time = time.monotonic()

        while time.monotonic() < start_time + timeout:
            with self.rbuffer_lock:
                if len(self.rbuffer) > 0:
                    ret = self.rbuffer
                    self.rbuffer = str()
                    break
            time.sleep(0.1)

        return ret

    def recv_data_clear(self):
        with self.rbuffer_lock:
            self.rbuffer = str()

    def close(self):
        self.running = False

        if self.thread is not None:
            self.thread.join()

        if self.ser is not None:
            self.ser.close()

def fm350_dial_prepare(sr):
    sr.recv_data_clear()
    sr.send_data("AT+CFUN=1")
    time.sleep(5)
    sbuf = sr.recv_data_with_timeout().strip()

    return True

def main():
    global os_is_openwrt
    fm350_usbsysfs_root = ""
    usbsysfs_root = "/sys/bus/usb/devices"

    usbdirs = os.listdir(usbsysfs_root)
    for usbdir in usbdirs:
        usbfulldir = os.path.join(usbsysfs_root, usbdir)
        idproduct_file = os.path.join(usbfulldir, "idProduct")
        idvendor_file = os.path.join(usbfulldir, "idVendor")
        idproduct = 0
        idvendor = 0

        try:
            with open(idproduct_file, 'r', encoding="ascii") as f:
                idproduct_str = f.read()
                idproduct = int(idproduct_str, 16)

            with open(idvendor_file, 'r', encoding="ascii") as f:
                idvendor_str = f.read()
                idvendor = int(idvendor_str, 16)
        except:
            pass

        if idproduct == fm350_idproduct and idvendor == fm350_idvendor:
            fm350_usbsysfs_root = usbfulldir
            break

    if len(fm350_usbsysfs_root) == 0:
        print("No FM350 modem detected!", file=sys.stderr)
        sys.exit(1)
        return

    print("FM350 modem detected, searching interface and serial port...", file=sys.stderr)

    if os.path.isfile("/sbin/uci") or os.path.isfile("/usr/sbin/uci"):
        os_is_openwrt = True

    modem_manager_running = False
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == "ModemManager":
            modem_manager_running = True

    if modem_manager_running:
        print("ModemManager detected, stopping service...", file=sys.stderr)

        if os_is_openwrt:
            os.system("/etc/init.d/ModemManager stop")
        else:
            os.system("systemctl stop ModemManager")

    serialports = []
    iface = ""

    usbdirs = os.listdir(fm350_usbsysfs_root)
    for usbdir in usbdirs:
        usbfulldir = os.path.join(fm350_usbsysfs_root, usbdir)
        if not os.path.isdir(usbfulldir):
            continue

        usbsubdirs = os.listdir(usbfulldir)
        for usbsubdir in usbsubdirs:
            if usbsubdir == "net":
                usbsubfulldir = os.path.join(usbfulldir, usbsubdir)
                ifaces = os.listdir(usbsubfulldir)

                if(len(ifaces) > 0):
                    iface = ifaces[0]

            if usbsubdir.startswith("ttyUSB"):
                serialports.append(os.path.join("/dev", usbsubdir))

    if len(iface) == 0 or len(serialports) == 0:
        print("No serial port or interfaces detected for FM350 modem, please check device driver!", file=sys.stderr)
        sys.exit(2)
        return

    serialports.sort()
    serialport = ""
    sphandle = None

    for sport in serialports:
        sr = SerialReader(sport)
        if sr is None:
            continue

        sr.send_data("")
        time.sleep(0.5)
        sr.recv_data_clear()

        sr.send_data("AT")
        time.sleep(1)
        sbuf = sr.recv_data_with_timeout().strip()

        if "OK" in sbuf:
            serialport = sport
            sphandle = sr
            break

        sr.close()

    if sphandle is not None:
        print("Interface {0} and serial port {1} detected.".format(iface, serialport), file=sys.stderr)
    else:
        print("No serial port available for commands, please check device driver!", file=sys.stderr)
        sys.exit(3)
        return

    if not fm350_dial_prepare(sphandle):
        print("Failed to do preparation for dialout!", file=sys.stderr)
        sys.exit(4)

if __name__ == "__main__":
    main()

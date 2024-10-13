import mmap
import os
import time
import socket

# HPS/FPGA Memory Addresses
HW_REGS_BASE = 0xFC000000
HW_REGS_SPAN = 0x04000000
HW_REGS_MASK = HW_REGS_SPAN - 1
ALT_LWFPGASLVS_OFST = 0xFF200000
LEDS = 0x00000100

# UDP Server Info
UDP_IP = "0.0.0.0"  # Listen on all available interfaces
UDP_PORT = 80

# Convert 1 digit into 7-seg bit pattern
numtable = {
    "0": 0x40,
    "1": 0x79,
    "2": 0x24,
    "3": 0x30,
    "4": 0x19,
    "5": 0x12,
    "6": 0x02,
    "7": 0x78,
    "8": 0x00,
    "9": 0x10,
    "-": 0x40  # Represent the minus sign if needed
}

# Convert list of 4 numtable into mmap writable string
def cons(bins):
    s = ""
    f = 0
    for i in range(0, 4):
        f = f | bins[i] << (i * 7)

    for i in range(0, 4):
        t = f >> (i * 8)
        s = s + chr(t & 0xFF)

    return s

# Open memory as file descriptor
fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)

# Check if opened successfully
if fd == -1:
    print("error opening /dev/mem!")
    exit()

# Map /dev/mem to writable block of memory
vb = mmap.mmap(
    fd,
    HW_REGS_SPAN,
    flags=mmap.MAP_SHARED,
    offset=HW_REGS_BASE
)

# 7-seg base address
pos = (ALT_LWFPGASLVS_OFST + LEDS) & HW_REGS_MASK

# Move memory block pointer to above address
vb.seek(pos)

# Function to display brightness on Hex0-Hex1 and contrast on Hex2-Hex3
def display(brightness, contrast):
    vb.write(cons([
        numtable[str(contrast % 10)],  # Ones place of contrast
        numtable[str((contrast // 10) % 10)],  # Tens place of contrast
        numtable[str(brightness % 10)],  # Ones place of brightness
        numtable[str((brightness // 10) % 10)]  # Tens place of brightness
    ]))
    vb.seek(pos)

# Initial brightness and contrast values
brightness_value = 0  # Set initial brightness to 00
contrast_value = 0  # Set initial contrast to 00

# Set initial display to 5050 (default values)
display(brightness_value, contrast_value)

# UDP Setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# UDP Server Listener
print("READY")
while True:
    # Adjust buffer size to 5 bytes to match incoming message size
    data, addr = sock.recvfrom(5)
    print("Received message:", data, "from", addr)

    if data == b"END":
        vb.close()
        os.close(fd)
        break
    else:
        if len(data) == 5:  # Expect 5 bytes
            try:
                if data[0:1] == b'C':  # Contrast message
                    contrast_value = int(data[1:])  # Convert remaining string to int
                    contrast_value = abs(contrast_value) % 100  # Ignore negative, wrap at 99
                    print("Setting contrast to:", contrast_value)

                elif data[0:1] == b'B':  # Brightness message
                    brightness_value = int(data[1:])  # Convert remaining string to int
                    brightness_value = abs(brightness_value) % 100  # Ignore negative, wrap at 99
                    print("Setting brightness to:", brightness_value)

                # Update the display with the current brightness and contrast values
                display(brightness_value, contrast_value)

            except ValueError:
                print("Error: Received invalid number format:", data[1:])

        else:
            print("Received data length is not 5, skipping display update.")

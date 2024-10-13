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
hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)
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
    "9": 0x10
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

# Check if opened sucessfully
if fd == -1:
    print ("error opening /dev/mem!")
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
# Display 4 number on Hex0-Hex3
def display(a, b, c, d):
    vb.write(cons([
        numtable[str(d)],
        numtable[str(c)],
        numtable[str(b)],
        numtable[str(a)]
    ]))
    vb.seek(pos)
    
# Initialize contrast and brightness to display both
contrast_value = 0
brightness_value = 0

def update_display():
    # Break contrast and brightness into digits
    d1 = contrast_value % 10  # Get the last digit (ones place) of contrast
    d2 = (contrast_value // 10) % 10  # Get the second last digit (tens place) of contrast
    b1 = brightness_value % 10  # Get the last digit (ones place) of brightness
    b2 = (brightness_value // 10) % 10  # Get the second last digit (tens place) of brightness
    # Display contrast in the first two digits and brightness in the last two digits
    display(d2, d1, b2, b1)

# Sanity check (this will show 0, 1, 2, ..., 9 on the 7-seg display)
for i in range(0, 10):
    display(i, i, i, i)
    time.sleep(0.1)

# Reset display (show 5050 on the 7-seg display)
contrast_value = 50
brightness_value = 50
update_display()

# UDP Setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# UDP Server Listener
print "READY"
while True:
    # Receive 4 byte string (4 digit number)
    data, addr = sock.recvfrom(4)  # Buffer size is 4 bytes
    print "Received message:", data, "from", addr  # Print received data for debugging

    if data == b"END":
        # Cleanup
        vb.close()
        os.close(fd)
        break
    else:
        # Process the received message
        if len(data) == 3:  # Adjust to check if length is 3, not 4
            try:
                if data[0] == 'C':  # Contrast message
                    # Extract contrast value and ensure it's a valid integer
                    contrast_value = int(data[1:])  # Convert the remaining string to int
                    print "Setting contrast to:", contrast_value  # Debug output
                    # Update the display with both contrast and brightness
                    update_display()

                elif data[0] == 'B':  # Brightness message
                    # Extract brightness value and ensure it's a valid integer
                    brightness_value = int(data[1:])  # Convert the remaining string to int
                    print "Setting brightness to:", brightness_value  # Debug output
                    # Update the display with both brightness and contrast
                    update_display()

                else:
                    print "Unknown message format, skipping display update."

            except ValueError:
                print "Error: Received invalid number format:", data[1:]

        else:
            print "Received data length is not 3, skipping display update."

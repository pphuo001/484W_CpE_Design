import mmap  # for memory mapping
import os  # for system-level operations
import time  # for time-based functions
import socket  # for network communications

HW_REGS_BASE = 0xFC000000  # base address for memory-mapped registers
HW_REGS_SPAN = 0x04000000  # total size of the memory region to map
HW_REGS_MASK = HW_REGS_SPAN - 1  # mask to wrap the address within the memory region
ALT_LWFPGASLVS_OFST = 0xFF200000  # base address for lightweight FPGA slave registers
LEDS = 0x00000100  # offset for LED control registers

UDP_IP = "0.0.0.0"  # this listens on all available network interfaces
UDP_PORT = 80  # same in Qt UDPClient.cpp

# convert 1 digit into 7-segment bit pattern for display
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
    "-": 0x40  
}

# convert list of 4 numtable values into a writable string for memory mapping
def cons(bins):
    s = ""  # initialize empty string
    f = 0  # initialize variable for constructing the 7-segment bit pattern

    # loop through the list of 4 numtable values and pack them into a single integer
    for i in range(0, 4):
        f = f | bins[i] << (i * 7)  # Pack 7 bits per digit

    # convert the packed integer into bytes
    for i in range(0, 4):
        t = f >> (i * 8)  # extract each byte
        s = s + chr(t & 0xFF)  # append the byte as a character to the string
    return s  # return the memory-mappable string

# open memory as a file descriptor for read/write access
fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)

# check if the memory file was opened successfully
if fd == -1:
    print("Error opening /dev/mem!")  # print if error
    exit()  

# map the /dev/mem file to a writable block of memory
vb = mmap.mmap(
    fd,
    HW_REGS_SPAN,
    flags=mmap.MAP_SHARED,
    offset=HW_REGS_BASE
)

# 7-segment base address
pos = (ALT_LWFPGASLVS_OFST + LEDS) & HW_REGS_MASK  # calculate the memory-mapped address for the LEDs

# move the memory block pointer to the 7-segment base address
vb.seek(pos)

# function to display brightness on HEX3 to HEX2 and contrast on HEX1 to HEX0
def display(brightness, contrast):
    # write the 7-segment bit patterns to the memory-mapped region
    vb.write(cons([
        numtable[str(contrast % 10)],  # ones place of contrast
        numtable[str((contrast // 10) % 10)],  # tens place of contrast
        numtable[str(brightness % 10)],  # ones place of brightness
        numtable[str((brightness // 10) % 10)]  # tens place of brightness
    ]))
    vb.seek(pos)  # Reset the memory pointer to the start position after writing

brightness_value = 0  # set initial brightness to 0
contrast_value = 0  # set initial contrast to 0

# display brightness and contrast values
display(brightness_value, contrast_value)

# UDP setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # create a UDP socket
sock.bind((UDP_IP, UDP_PORT))  # bind the socket to the IP address and port

print("READY")  # message indicating that server is ready

# loop to listen for incoming UDP messages
while True:
    # receive a 5-byte message from the UDP client
    data, addr = sock.recvfrom(5)
    print("Received message:", data, "from", addr)  

   if data == b"END":
        vb.close()  # close the memory-mapped file
        os.close(fd)  # close the file descriptor
        break  # exit the loop

    # process the message if it's exactly 5 bytes long
    else:
        if len(data) == 5:
            try:
                # if the message starts with 'C', it is a contrast update
                if data[0:1] == b'C':  
                    contrast_value = int(data[1:])  # extract and convert contrast value
                    contrast_value = abs(contrast_value) % 100  # ensure contrast value is between 0 and 99
                    print("Setting contrast to:", contrast_value)  # message the new contrast value

                # if the message starts with 'B', it is a brightness update
                elif data[0:1] == b'B':  
                    brightness_value = int(data[1:])  # extract and convert brightness value
                    brightness_value = abs(brightness_value) % 100  # ensure brightness value is between 0 and 99
                    print("Setting brightness to:", brightness_value)  # message the new brightness value

                # update display with the current brightness and contrast values
                display(brightness_value, contrast_value)

            # handle invalid number format errors
            except ValueError:
                print("Error: Received invalid number format:", data[1:])
            else:
            print("Received data length is not 5, skipping display update.")

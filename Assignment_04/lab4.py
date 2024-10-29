
from PIL import Image
import io
import os  # for system-level operations
import mmap  # for memory mapping
import struct  # for packing and unpacking binary data
import socket  # for network communication (UDP)

# HPS/FPGA memory addresses
HW_REGS_BASE = 0xFF200000  # base address for FPGA memory
HW_REGS_SPAN = 0x00200000  # memory span (size) to map
LED_BASE_OFFSET = 0x00000110  # offset for the LEDs in memory
HEX_BASE_OFFSET = 0x00000100  # offset for HEX display in memory

# 7-segment digit bit pattern table
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

# convert list of 4 numtable values into a memory-mappable string for HEX display
def cons(bins):
    s = ""  # initialize empty string
    f = 0  # initialize variable
    for i in range(0, 4):  # loop through the 4 digits
        f = f | bins[i] << (i * 7)  # pack 7 bits per digit

    # convert the packed value into bytes
    for i in range(0, 4):
        t = f >> (i * 8)  # extract each byte
        s = s + chr(t & 0xFF)  # append byte to string
    return s  # return the memory-mappable string

# open /dev/mem to access physical memory
fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)

# map the memory for access to the FPGA's memory space
virtual_base = mmap.mmap(fd, HW_REGS_SPAN, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=HW_REGS_BASE)

# set memory pointer to HEX display base address
virtual_base.seek(HEX_BASE_OFFSET)

# function to display brightness on HEX3 to HEX2 and contrast on HEX1 to HEX0
def display_on_hex(brightness, contrast):
    virtual_base.seek(HEX_BASE_OFFSET)  # set memory pointer to HEX base address
    # get digit patterns for brightness and contrast
    contrast_digits = [
        numtable[str(contrast % 10)],  # ones place of contrast
        numtable[str((contrast // 10) % 10)],  # tens place of contrast
    ]
    brightness_digits = [
        numtable[str(brightness % 10)],  # ones place of brightness
        numtable[str((brightness // 10) % 10)]  # tens place of brightness
    ]
    # write the patterns to the memory-mapped region for HEX display
    virtual_base.write(cons(contrast_digits + brightness_digits))
    print "Displayed on HEX: Brightness =", brightness, "Contrast =", contrast  # print current brightness and contrast

# function to turn off brightness-related LEDRs
def turn_off_brightness_leds():
    # current LEDR state from memory
    current_leds = struct.unpack('<L', virtual_base.read(4))[0]
    # turn off LEDRs 7, 8, and 9 
    led_value = current_leds & ~((1 << 6) | (1 << 7) | (1 << 8))
    virtual_base.seek(LED_BASE_OFFSET)  # set memory pointer to LEDR base address
    virtual_base.write(struct.pack('<L', led_value))  # write new LEDR state to memory
    print "Brightness LEDs turned off"  # print confirmation

# function to turn off contrast-related LEDRs
def turn_off_contrast_leds():
    # current LEDR state from memory
    current_leds = struct.unpack('<L', virtual_base.read(4))[0]
    # turn off LEDRs 2, 3, and 4 
    led_value = current_leds & ~((1 << 1) | (1 << 2) | (1 << 3))
    virtual_base.seek(LED_BASE_OFFSET)  # set memory pointer to LEDR base address
    virtual_base.write(struct.pack('<L', led_value))  # write new LEDR state to memory
    print "Contrast LEDs turned off"  # print confirmation

# function to activate LEDRs for negative brightness
def light_up_negative_brightness():
    # current LEDR state from memory
    current_leds = struct.unpack('<L', virtual_base.read(4))[0]
    # activate LEDRs 7, 8, and 9 
    led_value = current_leds | ((1 << 6) | (1 << 7) | (1 << 8))
    virtual_base.seek(LED_BASE_OFFSET)  # set memory pointer to LEDR base address
    virtual_base.write(struct.pack('<L', led_value))  # write new LEDR state to memory
    print "Activated LEDs for negative brightness:", bin(led_value)  # print confirmation

# function to activate LEDRs for negative contrast
def light_up_negative_contrast():
    # current LEDR state from memory
    current_leds = struct.unpack('<L', virtual_base.read(4))[0]
    # activate LEDRs 2, 3, and 4
    led_value = current_leds | ((1 << 1) | (1 << 2) | (1 << 3))
    virtual_base.seek(LED_BASE_OFFSET)  # set memory pointer to LEDR base address
    virtual_base.write(struct.pack('<L', led_value))  # write new LEDR state to memory
    print "Activated LEDs for negative contrast:", bin(led_value)  # print confirmation




image_data_buffer = bytearray()  # Buffer to store image data
receiving_image = False  # Flag to indicate if an image is being received


# UDP server settings
UDP_IP = "0.0.0.0"  # listen on all available interfaces
UDP_PORT = 80  # same in Qt UDPClient.cpp
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # create UDP socket
sock.bind((UDP_IP, UDP_PORT))  # bind the socket to the IP and port

print("Listening for incoming messages from the GUI slider...")  # status message

# initial values for brightness and contrast
brightness = 0 
contrast = 0  
brightness_was_negative = False  # track if brightness was negative previously
contrast_was_negative = False  # track if contrast was negative previously

try:
    # loop to listen for UDP messages
    while True:
        data, addr = sock.recvfrom(1024)  # receive UDP message (max size 1024 bytes)
        print "Received data:", data  # print the received data

        # update only the received value, keep the other unchanged
        if data.startswith('B'):  # if message is brightness update
            brightness = int(data[1:])  # extract and update brightness value
            print "Updated brightness:", brightness  # print the new brightness value
        elif data.startswith('C'):  # if message is contrast update
            contrast = int(data[1:])  # extract and update contrast value
            print "Updated contrast:", contrast  # print the new contrast value

        # handle negative brightness
        if brightness < 0:
            light_up_negative_brightness()  # activate negative brightness LEDRs
            brightness_was_negative = True  # mark brightness as negative
        elif brightness >= 0 and brightness_was_negative:
            turn_off_brightness_leds()  # turn off brightness LEDRs if brightness becomes positive
            brightness_was_negative = False  # reset negative brightness flag

        # handle negative contrast
        if contrast < 0:
            light_up_negative_contrast()  # activate negative contrast LEDRs
            contrast_was_negative = True  # mark contrast as negative
        elif contrast >= 0 and contrast_was_negative:
            turn_off_contrast_leds()  # turn off contrast LEDRs if contrast becomes positive
            contrast_was_negative = False  # reset negative contrast flag

        if data.startswith(b'O%1'):  # Start receiving the original image
            print("Starting image transmission...")
            image_data_buffer = bytearray()   # Clear the buffer to store new image data
            receiving_image = True
            continue  # Continue to the next chunk
        
                # Handle brightness and contrast updates only if not receiving an image
        if not receiving_image:
            if data.startswith(b'B'):  # Brightness command
                try:
                    brightness = int(data[1:])
                    print("Updated brightness:", brightness)
                except ValueError:
                    print("Invalid brightness value received:", data)
                continue
            elif data.startswith(b'C'):  # Contrast command
                try:
                    contrast = int(data[1:])
                    print("Updated contrast:", contrast)
                except ValueError:
                    print("Invalid contrast value received:", data)
                continue
        
        
        
        # If in the middle of an image transmission, collect data chunks
        if receiving_image:
            image_data_buffer.extend(data)
            
            if len(data) < 1024:  # Last chunk received
                print("Image transmission completed.")
                
                # Convert the byte data to an image
                try:
                    image = Image.open(io.BytesIO(image_data_buffer))
                    image.show()
                except Exception as e:
                    print("Failed to load image:", e)
                
                # Reset for the next image
                receiving_image = False
                image_data_buffer = bytearray()

        # display brightness and contrast on the HEX displays
        display_on_hex(abs(brightness) % 100, abs(contrast) % 100)  # ensure values are between 0 and 99

except KeyboardInterrupt:
    print "Server stopped."  # print message when server is interrupted

finally:
    # clean up resources
    virtual_base.close()  # close the memory-mapped file
    os.close(fd)  # close the file descriptor
    sock.close()  # close the UDP socket

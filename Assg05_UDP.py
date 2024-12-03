import socket  # Import the socket module for networking
import numpy as np  # Import numpy for handling arrays and image processing
from PIL import Image, ImageEnhance  # Import PIL for image manipulation and enhancements
import StringIO  # Import StringIO for in-memory byte buffer handling
import cv2  # Import OpenCV for displaying images

# Configuration
UDP_IP = "0.0.0.0"  # Listen on all available interfaces
UDP_PORT = 80       # Port matching the Qt app's UdpClient
BUFFER_SIZE = 1024  # Packet size for UDP data chunks

# Initialize variables
original_image_data = bytearray()
overlay_image_data = bytearray()
image_data_buffer = bytearray()
image_type = None
window_initialized = False
overlay_active = False
receiving_image = False
brightness_value = 0
contrast_value = 0

def combine_images(original_path, overlay_path, output_path):
    """
    Combine the original and overlay images and save the result.
    
    Parameters:
    - original_path: Path to the original image.
    - overlay_path: Path to the overlay image.
    - output_path: Path to save the combined image.
    """
    try:
        # Open the original and overlay images
        original = Image.open(original_path).convert("RGBA")
        overlay = Image.open(overlay_path).convert("RGBA")

        # Resize the overlay to be smaller than the original (e.g., 50% scale)
        overlay_size = (original.width // 2, original.height // 2)
        overlay = overlay.resize(overlay_size, Image.ANTIALIAS)

        # Position the overlay at the center of the original
        position = ((original.width - overlay.width) // 2, 
                    (original.height - overlay.height) // 2)

        # Paste the overlay onto the original (using alpha compositing)
        combined = original.copy()
        combined.paste(overlay, position, overlay)

        # Save the result
        combined.save(output_path)
        print("Combined image saved as:", output_path)
    except Exception as e:
        print("Error combining images:", e)

def save_values_to_file():
    """Save brightness and contrast values to a file."""
    print("Attempting to write to Assg05_values.txt...")
    try:
        print("Writing values -> Brightness: {}, Contrast: {}".format(brightness_value, contrast_value))
        paramFile = open("Assg05_values.txt", "w")
        paramFile.write(str(brightness_value))
        paramFile.write('\n')
        paramFile.write(str(contrast_value))
        paramFile.close()
        print("Assg05_values.txt created/updated successfully.")
    except Exception as e:
        print("Error saving values to file: {}".format(e))


def handle_command(command):
    global overlay_active, brightness_value, contrast_value
    print("Handling command: {}".format(command))

    if command.startswith("B"):  # Adjust brightness
        try:
            brightness_value = int(command[1:].lstrip("0"))
            print("Brightness adjusted to: {}".format(brightness_value))
            save_values_to_file()
        except ValueError:
            print("Invalid brightness value received: {}".format(command))

    elif command.startswith("C"):  # Adjust contrast
        try:
            contrast_value = int(command[1:].lstrip("0"))
            print("Contrast adjusted to: {}".format(contrast_value))
            save_values_to_file()
        except ValueError:
            print("Invalid contrast value received: {}".format(command))


def save_image(image_data, file_name):
    """
    Save image data as a PNG file.
    """
    try:
        image = Image.open(StringIO.StringIO(image_data))  # Load image from the buffer
        image.save(file_name)  # Save the image as PNG
        print("Image saved successfully as {}".format(file_name))
    except Exception as e:
        print("Error saving image: {}".format(e))

# Set up the UDP server
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Listening for image data on {}: {}...".format(UDP_IP, UDP_PORT))

while True:  # Run a continuous loop to listen/receive data
    data, addr = sock.recvfrom(BUFFER_SIZE)  # Receive data from the socket
    try:
        msg = data.decode('utf-8')  # Try decoding the data to text
    except UnicodeDecodeError:
        msg = None  # Set message to None if decoding fails

    if msg in ["Original", "Overlay"]:  # Check if message specifies image type
        image_type = msg  # Set the image type
        print("Image type set to: {}".format(image_type))  # Print the current image type
        image_data_buffer = bytearray()  # Reset the data buffer
        receiving_image = False  # Reset receiving image flag

    elif msg == "IMG:START":
        print("Starting image transfer for {}".format(image_type))
        receiving_image = True  # Set receiving image flag
        image_data_buffer = bytearray()  # Clear the buffer for new image data

    elif msg == "IMG:END":
        print("Ending image transfer for {} - received {} bytes.".format(image_type, len(image_data_buffer)))
        if image_type == "Original":
            original_image_data = image_data_buffer  # Store the original image data
            save_image(original_image_data, "Assg05_orig.png")  # Save as PNG
        elif image_type == "Overlay":
            overlay_image_data = image_data_buffer  # Store the overlay image data
            save_image(overlay_image_data, "Assg05_ovrly.png")  # Save as PNG
            
             # Combine the images if both are available
            if original_image_data and overlay_image_data:
                combine_images("Assg05_orig.png", "Assg05_ovrly.png", "Assg05_image.png")

        receiving_image = False
        image_type = None
        image_data_buffer = bytearray()

    elif receiving_image:  # Continue to receive data if true
        image_data_buffer.extend(data)  # Append received data to buffer
        print("Received data chunk, buffer size is now: {}".format(len(image_data_buffer)))  # Print buffer size

    elif msg:
        print("Received command: {}".format(msg))
        handle_command(msg)

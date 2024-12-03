import os
import socket
from PIL import Image

# Constants for TCP Communication
TCP_PORT = 80
TCP_IP = "192.168.0.129"
PACKET_SIZE = 1024

# Get and print host details
HOST_NAME = socket.gethostname()
IP_ADDR = socket.gethostbyname(HOST_NAME)
print(f"HOSTNAME: {HOST_NAME}")
print(f"IPADDR: {IP_ADDR}")


def parse_rgba_image(image_data, width, height):
    """
    Parse RGBA image data into a PIL image object.
    Each row of the image is delimited with a semicolon, and each pixel by spaces.
    """
    try:
        parsed_image = Image.new("RGBA", (width, height))
        image_lines = image_data.split(';')
        for img_row in range(height):
            img_rgba = image_lines[img_row].split(' ')
            for img_col in range(width):
                pix_red = int(img_rgba.pop(0))
                pix_green = int(img_rgba.pop(0))
                pix_blue = int(img_rgba.pop(0))
                pix_alpha = int(img_rgba.pop(0))
                parsed_image.putpixel((img_col, img_row), (pix_red, pix_green, pix_blue, pix_alpha))
        return parsed_image
    except Exception as e:
        print(f"Error parsing RGBA image: {e}")
        return None


def save_parameters(file_path, brightness, contrast):
    """
    Save brightness and contrast parameters to a file.
    """
    try:
        with open(file_path, "w") as param_file:
            param_file.write(f"{brightness}\n{contrast}\n")
        print("Parameters saved successfully.")
    except Exception as e:
        print(f"Error saving parameters: {e}")


def setup_socket(ip, port):
    """
    Setup and bind the socket for TCP communication.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((ip, port))
        print(f"LISTENING TO {ip}...")
        sock.listen(5)
        return sock
    except socket.error as e:
        print(f"Socket error: {e}")
        exit(1)


def handle_data(data):
    """
    Handle incoming data based on its type (_IMAGE_ or _PARAM_).
    """
    data_lines = data.decode().split('\n')
    if data.startswith(b'_IMAGE_'):
        print("Processing image data...")
        try:
            img_width = int(data_lines[1])
            img_height = int(data_lines[2])
            img_string = data_lines[3]
            parsed_image = parse_rgba_image(img_string, img_width, img_height)
            if parsed_image:
                parsed_image.save("Assg05_image.png")
                print("Image saved successfully.")
        except Exception as e:
            print(f"Error processing image: {e}")

    elif data.startswith(b'_PARAM_'):
        print("Processing parameter data...")
        try:
            brightness = int(data_lines[1])
            contrast = int(data_lines[2])
            save_parameters("Assg05_values.txt", brightness, contrast)
        except Exception as e:
            print(f"Error processing parameters: {e}")


def main():
    # Setup socket
    sock = setup_socket(TCP_IP, TCP_PORT)

    print("READY TO SERVE...")

    while True:
        try:
            print("STANDING BY...")
            conn, addr = sock.accept()
            print(f"CONNECTED TO {addr}")

            # Receive data in chunks
            data = b""
            while True:
                chunk = conn.recv(PACKET_SIZE)
                if not chunk:
                    break
                data += chunk
                if data.endswith(b'_END_'):
                    break

            print("Data received successfully.")
            handle_data(data)

        except KeyboardInterrupt:
            print("Shutting down server...")
            break
        except Exception as e:
            print(f"Error: {e}")

    sock.close()


if __name__ == "__main__":
    main()

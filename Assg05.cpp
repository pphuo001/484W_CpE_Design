#include <opencv2/opencv.hpp>  // OpenCV library for image processing
#include <sys/time.h>          // System time library for timing operations
#include "D8MCapture.h"        // Header for D8M camera capture functionality
#include "hps_0.h"             // Header for HPS interaction
#include <string>              // C++ string library
#include <fstream>             // File input/output stream library
#include <iostream>            // Standard input/output stream library

using namespace cv;            // OpenCV namespace for convenience
using namespace std;           // Standard namespace for convenience

#ifndef CAPTURE_RAM_DEVICE
#define CAPTURE_RAM_DEVICE "/dev/f2h-dma-memory" // Default capture RAM device if not defined
#endif

int main() {
    Mat src;  // Matrix to hold the camera feed frame
    D8MCapture *cap = new D8MCapture(TV_DECODER_TERASIC_STREAM_CAPTURE_BASE, CAPTURE_RAM_DEVICE);
    // Create a capture object for reading from the camera feed

    if (!cap->isOpened()) {  // Check if the camera capture object is successfully initialized
        cerr << "Failed to open capture device." << endl;
        return -1;  // Exit program if the camera device fails to open
    }

    // Load overlay image to be used for blending
    Mat overlayedImage = imread("Assg05_image.png"); 
    if (!overlayedImage.empty()) { 
        // Resize the overlay image to a fixed size matching the camera feed
        resize(overlayedImage, overlayedImage, Size(800, 480), INTER_LINEAR);
        // Convert the overlay image to BGRA format to include transparency (alpha channel)
        cvtColor(overlayedImage, overlayedImage, COLOR_BGR2BGRA);
    } else { 
        cerr << "Overlay image not found or failed to load." << endl;
    }

    // Variables to hold brightness and contrast values
    int brightness = 0; 
    int contrast = 50; 
    string parameterFile = "Assg05_values.txt";  // File path for brightness and contrast parameters

    double fps = 0.0;  // Variable to store the calculated frames per second
    int64 prevTick = getTickCount();  // Initial tick count for FPS calculation

    while (true) {  // Main loop to process video frames
        if (!cap->read(src)) {  // Capture the next frame from the camera
            cerr << "Failed to read from camera feed." << endl;
            break;  // Exit loop if frame reading fails
        }

        // Open the parameter file to read updated brightness and contrast values
        ifstream paramStream(parameterFile);
        if (paramStream.is_open()) {
            string line;
            getline(paramStream, line);  // Read the brightness value as a string
            brightness = stoi(line);  // Convert brightness string to integer
            getline(paramStream, line);  // Read the contrast value as a string
            contrast = stoi(line);  // Convert contrast string to integer
        }
        paramStream.close();  // Close the parameter file

        Mat outputImage = src.clone();  // Clone the original frame to modify

        // Apply brightness and contrast adjustments to the camera feed
        double brightnessAdjust = brightness; 
        double contrastAdjust = contrast / 50.0;  // Normalize contrast for scaling
        outputImage.convertTo(outputImage, -1, contrastAdjust, brightnessAdjust);

        if (!overlayedImage.empty()) {  // Check if the overlay image is available
            // Define the region of interest (ROI) for overlaying the image
            Mat overlayROI = outputImage(Rect(0, 0, overlayedImage.cols, overlayedImage.rows));
            // Blend the overlay image with the ROI using addWeighted
            addWeighted(overlayROI, 1.0, overlayedImage, 0.5, 0.0, overlayROI);
        }

        // Calculate frames per second (FPS)
        int64 currentTick = getTickCount();  // Current tick count
        fps = getTickFrequency() / (currentTick - prevTick);  // FPS calculation
        prevTick = currentTick;  // Update the previous tick count

        // Display FPS as text on the modified frame
        string fpsString = "FPS: " + to_string(fps).substr(0, 4);  // Format FPS to two decimals
        putText(outputImage, fpsString, Point(outputImage.cols - 150, 30), FONT_HERSHEY_SIMPLEX, 
                0.7, Scalar(0, 255, 0), 2);

        // Display the processed frame in a window
        imshow("Live Output Image", outputImage);

        // Exit the loop if the ESC key is pressed
        if (waitKey(10) == 27) {
            break;
        }
    }

    delete cap;  // Release the camera capture object
    destroyAllWindows();  // Close all OpenCV windows
    return 0;  // Return success status
}

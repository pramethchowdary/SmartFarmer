import serial
import serial.tools.list_ports
import threading
import time
import json
import random
from flask import Flask, jsonify
from threading import Lock
from gemini import response_LLM

# --- Configuration and Global State ---

SERIAL_PORT = 'COM3'
BAUD_RATE = 9600
STOP_THREAD = False

# Global variable to store the latest sensor data
latest_sensor_data = {
    "temperature": 0.0,
    "humidity": 0.0,
    "moisture": 0,
    "soilType": "",
    "soilPH": 0.0,
    "rainfall": "",
    "season": "",
}
"""
      temperature = 28, // Assuming Celsius for consistency, but will prompt AI to handle either
      humidity = 65,
      moisture = 500, // Assuming a raw sensor reading for example
      soilType = "Loamy",
      soilPH = 6.5,
      rainfall = "Moderate (Outdoor context)",
      season = "Summer",
      locationType = "Outdoor Garden", // Added for completeness based on original prompt
      targetUse = "Leafy Green Vegetable", // Added for completeness based on original prompt
"""
# Lock to ensure thread-safe access to the global data
data_lock = Lock()

app = Flask(__name__)

# --- Utility to Find Arduino Port (Helpful if you don't know the port name) ---
def find_arduino_port():
    """Tries to automatically detect the port used by an Arduino."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Check for common manufacturer names for Arduino devices
        if 'Arduino' in port.description or 'USB Serial' in port.description:
            print(f"Found potential Arduino port: {port.device}")
            return port.device
    print("WARNING: Could not automatically find an Arduino port. Using default.")
    return SERIAL_PORT

# --- Serial Reading Thread ---
def read_serial_data():
    """Thread function to continuously read data from the serial port."""
    global latest_sensor_data, data_lock, STOP_THREAD

    # Attempt to use the automatically found port, fall back to default
    port_to_use = find_arduino_port() if SERIAL_PORT == 'COM3' else SERIAL_PORT

    ser = None
    try:
        # Initialize serial connection
        ser = serial.Serial(port=port_to_use, baudrate=BAUD_RATE, timeout=1)
        time.sleep(2) # Give Arduino time to reset after opening port

        print(f"--- Successfully connected to {port_to_use} at {BAUD_RATE} baud. ---")
        ser.flushInput()

        while not STOP_THREAD:
            # Read a line until newline character (\n) is received
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                print(f"RAW Data: {line}")

                if line:
                    try:
                        # Assumes Arduino sends: "TEMP,HUMIDITY,PRESSURE"
                        parts = line.split(',')
                        if len(parts) >= 8:
                            temp = float(parts[0])
                            humid = float(parts[1])
                            moisture = int(parts[2])
                            soil_type = parts[3]
                            soil_ph = float(parts[4])
                            rainfall = parts[5]
                            season = parts[6]

                            # Update global data safely using the lock
                            with data_lock:
                                latest_sensor_data['temperature'] = temp
                                latest_sensor_data['humidity'] = humid
                                latest_sensor_data['moisture'] = moisture
                                latest_sensor_data['soilType'] = soil_type
                                latest_sensor_data['soilPH'] = soil_ph
                                latest_sensor_data['rainfall'] = rainfall
                                latest_sensor_data['season'] = season
                                print(f"UPDATED: {latest_sensor_data}")
                    except ValueError as e:
                        print(f"Error parsing data: {e} | Line: {line}")
            
            # Use this fallback block if you don't have an Arduino connected, 
            # to simulate data updates every 500ms
            else:
                 with data_lock:
                    latest_sensor_data['temperature'] = round(random.uniform(20, 30), 1)
                    latest_sensor_data['humidity'] = round(random.uniform(40, 70), 1)
                    latest_sensor_data['moisture'] = random.randint(300, 800)
                    latest_sensor_data['soilType'] = random.choice(["Sandy", "Clay", "Loamy"])
                    latest_sensor_data['soilPH'] = round(random.uniform(5.5, 7.5), 1)
                    latest_sensor_data['rainfall'] = random.choice(["None", "Light", "Moderate", "Heavy"])
                    latest_sensor_data['season'] = random.choice(["Spring", "Summer", "Autumn", "Winter"])
                    print(f"SIMULATED UPDATE: {latest_sensor_data}")    
                 time.sleep(0.5)

    except serial.SerialException as e:
        print(f"!!! CRITICAL: Could not open serial port {port_to_use}. Error: {e} !!!")
        print("Please check the port name and ensure the Arduino IDE Serial Monitor is closed.")
    finally:
        if ser:
            ser.close()
            print("Serial port closed.")

# --- Flask Routes ---

@app.route('/')
def home():
    """A simple HTML message to confirm the server is running."""
    return (
        "<h1>Arduino Sensor Flask API is Running</h1>"
        "<p>Access the data at <a href='/api/v1/sensors'>/api/v1/sensors</a></p>"
        "<p>Check the console for serial reading status.</p>"
    )

@app.route('/api/v1/ai_response', methods=['GET'])
def get_ai_response():
    """
    Calls the Gemini model (response_LLM) using the latest sensor data.
    Returns the model's JSON response.
    """
    with data_lock:
        data = latest_sensor_data.copy()  # Thread-safe read of sensor data

    try:
        # Pass the sensor data to your Gemini LLM function
        ai_output = response_LLM(
            temperature=data["temperature"],
            humidity=data["humidity"],
            moisture=data["moisture"],
            soilType=data["soilType"],
            soilPH=data["soilPH"],
            rainfall=data["rainfall"],
            season=data["season"]
        )

        # Ensure the returned result is JSON serializable
        if isinstance(ai_output, str):
            # Try to parse if it’s a JSON string
            try:
                ai_output = json.loads(ai_output)
            except json.JSONDecodeError:
                ai_output = {"response_text": ai_output}

        print(f"AI RESPONSE: {ai_output}")

        return jsonify({
            "status": "success",
            "timestamp": time.time(),
            "ai_output": ai_output
        })

    except Exception as e:
        print(f"Error while calling Gemini model: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# --- Application Startup ---
if __name__ == '__main__':
    # 1. Start the serial reading thread
    # The 'daemon=True' ensures the thread exits when the main Flask app exits
    serial_thread = threading.Thread(target=read_serial_data, daemon=True)
    serial_thread.start()

    # 2. Start the Flask server
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        # Gracefully stop the thread if the user presses Ctrl+C
        STOP_THREAD = True
        serial_thread.join()
        print("\nFlask server and serial thread stopped.")

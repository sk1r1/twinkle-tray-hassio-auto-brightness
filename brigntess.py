import requests
import json
import time
import subprocess
import os

# ===== CONFIGURATION =====
HOME_ASSISTANT_URL = "http://domain.local:8123"
API_TOKEN = "user-api-key"
LUX_SENSOR_ENTITY_ID = "sensor.lux-sensor"

# ===== Brightness Mapping (Lux to Monitor Brightness %) =====
# Adjust these values based on your lighting conditions and preference.
LUX_BRIGHTNESS_MAPPING = [
    (2, 0),     # 2 lux -> 0% brightness
    (4, 15),     # 4 lux -> 15% brightness
    (15, 20),    # 15 lux -> 30% brightness
    (30, 30),    # 30 lux -> 40% brightness
    (40, 50),   # 40 lux -> 60% brightness
    (50, 60),   # 50 lux -> 70% brightness
    (100, 100)  # 100+ lux -> 100% brightness
]

def get_lux_from_home_assistant():
    """Fetches the current lux value from Home Assistant."""
    url = f"{HOME_ASSISTANT_URL}/api/states/{LUX_SENSOR_ENTITY_ID}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        sensor_data = response.json()
        lux_value = float(sensor_data['state'])
        return lux_value
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Home Assistant: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing the sensor data: {e}. Response was: {sensor_data}")
        return None

def map_lux_to_brightness(lux_value):
    """Maps a lux value to a brightness percentage based on the defined mapping."""
    # Sort mapping by lux threshold to ensure correct order
    mapping_sorted = sorted(LUX_BRIGHTNESS_MAPPING, key=lambda x: x[0])
    
    for lux_threshold, brightness in mapping_sorted:
        if lux_value <= lux_threshold:
            return brightness
    # Return the highest brightness if lux is above all thresholds
    return mapping_sorted[-1][1]

def set_monitor_brightness(brightness_percentage):
    """Sets the monitor brightness using Twinkle Tray's command line."""
    # Ensure brightness is an integer between 0 and 100
    brightness_percentage = max(0, min(100, int(brightness_percentage)))
    
    # Path to Twinkle Tray's executable. Adjust if needed.
    twinkle_tray_path = r"C:\Users\user\AppData\Local\Programs\twinkle-tray\Twinkle Tray.exe"
    
    try:
        # Example 1: Set brightness for all monitors
        result = subprocess.run(
            [twinkle_tray_path, "--All", "--Set=" + str(brightness_percentage)],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # Example 2: Set brightness for a specific monitor by number
        # result = subprocess.run(
        #     [twinkle_tray_path, "--MonitorNum=1", "--Set=" + str(brightness_percentage)],
        #     capture_output=True,
        #     text=True,
        #     timeout=15
        # )
        
        if result.returncode == 0:
            print(f"Successfully set brightness to {brightness_percentage}%")
        else:
            print(f"Twinkle Tray command failed. Stderr: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("Error: Twinkle Tray command timed out.")
    except FileNotFoundError:
        print("Error: Twinkle Tray not found at the specified path. Ensure the non-Store version is installed.")

def main():
    print("Starting automatic brightness adjustment script. Press Ctrl+C to stop.")
    
    while True:
        # 1. Get the current lux value
        lux = get_lux_from_home_assistant()
        
        if lux is not None:
            print(f"Current lux reading: {lux}")
            # 2. Map the lux value to a brightness percentage
            new_brightness = map_lux_to_brightness(lux)
            print(f"Mapped brightness: {new_brightness}%")
            # 3. Set the monitor brightness
            set_monitor_brightness(new_brightness)
        else:
            print("Failed to retrieve lux value. Skipping this cycle.")
        
        # 4. Wait for 5 seconds before the next reading
        time.sleep(5)

if __name__ == "__main__":
    main()

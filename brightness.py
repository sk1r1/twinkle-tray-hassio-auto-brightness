import requests
import json
import time
import subprocess
import os

# ===== CONFIGURATION =====
HOME_ASSISTANT_URL = "http://domain.local:8123"
API_TOKEN = "user-api-key"
LUX_SENSOR_ENTITY_ID = "sensor.lux-sensor"
LUX_HYSTERESIS_THRESHOLD = 3.0  # Minimum lux change required to update brightness

# ===== Brightness Mapping (Lux to Monitor Brightness %) =====
# Adjust these values based on your lighting conditions and preference.
LUX_BRIGHTNESS_MAPPING = [
    (2, 0),     # 2 lux -> 0% brightness
    (4, 15),     # 4 lux -> 15% brightness
    (15, 20),    # 15 lux -> 30% brightness
    (30, 30),    # 30 lux -> 40% brightness
    (40, 45),   # 40 lux -> 60% brightness
    (50, 60),   # 50 lux -> 70% brightness
    (100, 100)  # 100+ lux -> 100% brightness
]

# Global variables to track state
previous_lux = None
previous_brightness = None

def get_lux_from_home_assistant():
    """Fetches the current lux value from Home Assistant."""
    url = f"{HOME_ASSISTANT_URL}/api/states/{LUX_SENSOR_ENTITY_ID}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        sensor_data = response.json()
        lux_value = float(sensor_data['state'])
        return lux_value
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Home Assistant: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing the sensor data: {e}")
        return None

def map_lux_to_brightness(lux_value):
    """Maps a lux value to a brightness percentage using linear interpolation."""
    global previous_brightness
    
    # Sort mapping by lux threshold
    calibration_points = sorted(LUX_BRIGHTNESS_MAPPING, key=lambda x: x[0])
    
    # Handle values below minimum
    if lux_value <= calibration_points[0][0]:
        return float(calibration_points[0][1])
    
    # Handle values above maximum
    if lux_value >= calibration_points[-1][0]:
        return float(calibration_points[-1][1])
    
    # Find the two points to interpolate between
    for i in range(len(calibration_points) - 1):
        lux_low, brightness_low = calibration_points[i]
        lux_high, brightness_high = calibration_points[i + 1]
        
        if lux_low <= lux_value <= lux_high:
            # Linear interpolation
            ratio = (lux_value - lux_low) / (lux_high - lux_low)
            interpolated_brightness = brightness_low + ratio * (brightness_high - brightness_low)
            return round(interpolated_brightness, 1)
    
    return float(calibration_points[-1][1])

def should_update_brightness(current_lux, current_brightness):
    """Determines if brightness should be updated based on lux difference threshold."""
    global previous_lux, previous_brightness
    
    # First run - always update
    if previous_lux is None:
        return True
    
    # Calculate absolute difference in lux
    lux_difference = abs(current_lux - previous_lux)
    
    # Only update if lux difference exceeds threshold
    if lux_difference >= LUX_HYSTERESIS_THRESHOLD:
        print(f"Lux change ({lux_difference:.1f}) exceeds threshold ({LUX_HYSTERESIS_THRESHOLD}), updating brightness")
        return True
    else:
        print(f"Lux change ({lux_difference:.1f}) below threshold ({LUX_HYSTERESIS_THRESHOLD}), skipping update")
        return False

def set_monitor_brightness(brightness_percentage):
    """Sets the monitor brightness using Twinkle Tray's command line."""
    global previous_brightness
    
    # Ensure brightness is within valid range
    brightness_percentage = max(0.0, min(100.0, float(brightness_percentage)))
    
    # Check if brightness actually changed
    if previous_brightness is not None and brightness_percentage == previous_brightness:
        print(f"Brightness unchanged at {brightness_percentage}%, skipping hardware update")
        return True
    
    twinkle_tray_path = r"C:\Users\user\AppData\Local\Programs\twinkle-tray\Twinkle Tray.exe"
    
    try:
        # Convert to string (Twinkle Tray might only accept integers)
        brightness_str = str(round(brightness_percentage))
        
        result = subprocess.run(
            [twinkle_tray_path, "--All", "--Set=" + str(brightness_str)],
            capture_output=True,
            text=True,
            timeout=15
        )
        # Example 2: Set brightness for a specific monitor by number
        # result = subprocess.run(
        #     [twinkle_tray_path, "--MonitorNum=1", "--Set=" + str(brightness_str)],
        #     capture_output=True,
        #     text=True,
        #     timeout=15
        # )

        if result.returncode == 0:
            print(f"Successfully set brightness to {brightness_str}%")
            previous_brightness = brightness_percentage
            return True
        else:
            print(f"Twinkle Tray command failed. Stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Error: Twinkle Tray command timed out.")
        return False
    except FileNotFoundError:
        print("Error: Twinkle Tray not found at the specified path.")
        return False

def main():
    global previous_lux, previous_brightness
    
    print("Starting automatic brightness adjustment script. Press Ctrl+C to stop.")
    print(f"Hysteresis threshold: {LUX_HYSTERESIS_THRESHOLD} lux")
    
    while True:
        # 1. Get the current lux value
        current_lux = get_lux_from_home_assistant()
        
        if current_lux is not None:
            print(f"Current lux reading: {current_lux}")
            
            # 2. Map the lux value to a brightness percentage
            new_brightness = map_lux_to_brightness(current_lux)
            print(f"Mapped brightness: {new_brightness}%")
            
            # 3. Check if we should update based on lux difference
            if should_update_brightness(current_lux, new_brightness):
                # 4. Set the monitor brightness
                set_monitor_brightness(new_brightness)
                previous_lux = current_lux
            else:
                print("Skipping brightness update due to small lux change")
        else:
            print("Failed to retrieve lux value. Skipping this cycle.")
        
        # 5. Wait for 5 seconds before the next reading
        time.sleep(5)

if __name__ == "__main__":
    main()

import serial
import serial.tools.list_ports
import time

# 1. Find your USB adapter port automatically (macOS usually uses /dev/cu.usbserial-...)
ports = serial.tools.list_ports.comports()
mac_port = None
for port in ports:
    if "usbserial" in port.device or "usbmodem" in port.device or "uart" in port.device.lower():
        mac_port = port.device
        break

if not mac_port:
    print("Could not find a USB-to-Serial adapter. Are you sure it's plugged in?")
    # Fallback to prompting user
    mac_port = input("Enter your port manually (e.g., /dev/cu.usbserial-0001): ")

print(f"Attempting to connect to {mac_port} at 115200 baud...")

try:
    # 2. Connect to the sensor
    ser = serial.Serial(mac_port, 115200, timeout=1)
    print("Connected! Reading raw data (Press Ctrl+C to stop)...")
    
    # 3. Read the stream
    while True:
        if ser.in_waiting > 0:
            # Read the raw bytes
            raw_data = ser.read(ser.in_waiting)
            
            # The sensor likely sends hexadecimal data packets, not plain text.
            # Let's print the raw hex values so you can see if it's alive.
            hex_data = " ".join([f"{b:02x}" for b in raw_data])
            print(f"Raw RX: {hex_data}")
            
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nTest stopped by user.")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
    
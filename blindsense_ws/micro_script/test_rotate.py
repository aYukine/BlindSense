import serial
import pygame
import math
import sys
import time

# --- CONFIGURATION ---
SERIAL_PORT = "/dev/ttyUSB0"  # Change to your Arduino port (e.g., COM3 on Windows)
BAUD_RATE = 115200

# Initialize Serial Connection
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except Exception as e:
    print(f"Error opening port {SERIAL_PORT}: {e}")
    print("If on Linux, run: sudo chmod 666", SERIAL_PORT)
    sys.exit()

# Initialize Pygame & Fonts
pygame.init()
pygame.font.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GY-521 3D Perspective Facing Front")
clock = pygame.time.Clock()

# Setup Monospace Font for clean data readout alignment
font = pygame.font.SysFont("Courier", 18, bold=True)

# --- 3D GEOMETRY SETUP ---
axis_length = 150
arrow_tip = 40
points_3d = {
    'origin': [0, 0, 0],
    'x_axis': [axis_length, 0, 0],
    'y_axis': [0, axis_length, 0],
    'z_axis': [0, 0, axis_length],
    # Z-Arrowhead points
    'z_tip1': [arrow_tip, 0, axis_length - arrow_tip],
    'z_tip2': [-arrow_tip, 0, axis_length - arrow_tip],
    'z_tip3': [0, arrow_tip, axis_length - arrow_tip],
    'z_tip4': [0, -arrow_tip, axis_length - arrow_tip]
}

# --- ROTATION MATRIX FUNCTIONS ---
def rotate_x(x, y, z, angle):
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return x, y * cos_a - z * sin_a, y * sin_a + z * cos_a

def rotate_y(x, y, z, angle):
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return x * cos_a + z * sin_a, y, -x * sin_a + z * cos_a

def rotate_z(x, y, z, angle):
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return x * cos_a - y * sin_a, x * sin_a + y * cos_a, z

# --- MOTION TRACKING & CALIBRATION VARIABLES ---
roll = 0.0
pitch = 0.0
yaw = 0.0
last_time = time.time()

# MPU-6050 Default Conversion Constants
ACCEL_SCALE = 16384.0  # LSB Sensitivity for +/- 2g range
GYRO_SCALE = 131.0     # LSB Sensitivity for +/- 250 deg/s range

# Calibration Buffer variables
gyro_z_offset = 0.0
calibration_samples = 100
samples_read = 0
calibrating = True
gyro_data_buffer = []

print("==============================================================")
print("CALIBRATION: Place the sensor flat and PERFECTLY STILL...")
print("==============================================================")

running = True
while running:
    # Handle window events
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False

    try:
        # Read and decode line from Arduino
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line or "Accel:" not in line:
            continue
            
        # Delta time calculation (essential for accurate mathematical integration)
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        
        # Parse serial data stream
        # Expected incoming format: Accel: X=123 Y=456 Z=789 | Gyro: X=12 Y=34 Z=56
        parts = line.split('|')
        accel_parts = parts[0].replace("Accel: ", "").split()
        gyro_parts = parts[1].replace("Gyro: ", "").split()
        
        ax_raw = float(accel_parts[0].split('=')[1])
        ay_raw = float(accel_parts[1].split('=')[1])
        az_raw = float(accel_parts[2].split('=')[1])
        gz_raw = float(gyro_parts[2].split('=')[1]) # Z-Gyro handles the Yaw velocity
        
        # --- PHASE 1: GYRO BIAS CALIBRATION ---
        if calibrating:
            gyro_data_buffer.append(gz_raw)
            samples_read += 1
            if samples_read >= calibration_samples:
                gyro_z_offset = sum(gyro_data_buffer) / len(gyro_data_buffer)
                calibrating = False
                print("\n>>> Calibration Complete! You can now move the sensor. <<<\n")
            continue # Skip rendering until calibration finishes

        # --- PHASE 2: PHYSICS DATA SCALING & FILTERING ---
        # Scale Accelerometer data to true g-forces
        ax = ax_raw / ACCEL_SCALE
        ay = ay_raw / ACCEL_SCALE
        az = az_raw / ACCEL_SCALE
        
        # Absolute angular positioning for Roll and Pitch
        roll = math.atan2(ay, az)
        pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))
        
        # Subtract calculated static noise offset from Gyro
        corrected_gz = gz_raw - gyro_z_offset
        gz_deg_per_sec = corrected_gz / GYRO_SCALE
        
        # Small deadzone filter to block micro-vibrations from causing drift
        if abs(gz_deg_per_sec) > 0.2: 
            yaw += math.radians(gz_deg_per_sec) * dt

        # --- PHASE 3: RENDER 3D GRAPHICS ---
        screen.fill((15, 15, 20)) 
        
        # Kept camera_pitch for the 3D flip effect, but removed camera_yaw (the horizontal offset)
        camera_pitch = math.radians(65)  
        
        proj = {}
        for name, pt in points_3d.items():
            # 1. Apply real-time physical sensor rotations
            x, y, z = rotate_z(pt[0], pt[1], pt[2], yaw)
            x, y, z = rotate_y(x, y, z, pitch)
            x, y, z = rotate_x(x, y, z, roll)
            
            # 2. Apply camera tilt ("the flip") without the side angle offset
            x, y, z = rotate_x(x, y, z, camera_pitch)
            
            # 3. 3D to 2D Perspective Projection Math
            distance = 500
            focal_length = 400
            scale = focal_length / (distance + z)
            x_2d = int(WIDTH / 2 + x * scale)
            y_2d = int(HEIGHT / 2 + y * scale)
            proj[name] = (x_2d, y_2d)
            
        # Draw X Axis - RED
        pygame.draw.line(screen, (255, 50, 50), proj['origin'], proj['x_axis'], 4)
        # Draw Y Axis - GREEN
        pygame.draw.line(screen, (50, 255, 50), proj['origin'], proj['y_axis'], 4)
        # Draw Z Axis Main Stem - BLUE
        pygame.draw.line(screen, (50, 100, 255), proj['origin'], proj['z_axis'], 5)
        
        # Draw Z-Axis Flared Arrowhead
        pygame.draw.line(screen, (50, 100, 255), proj['z_axis'], proj['z_tip1'], 3)
        pygame.draw.line(screen, (50, 100, 255), proj['z_axis'], proj['z_tip2'], 3)
        pygame.draw.line(screen, (50, 100, 255), proj['z_axis'], proj['z_tip3'], 3)
        pygame.draw.line(screen, (50, 100, 255), proj['z_axis'], proj['z_tip4'], 3)
        
        # Close arrowhead base geometry
        pygame.draw.line(screen, (50, 100, 255), proj['z_tip1'], proj['z_tip3'], 2)
        pygame.draw.line(screen, (50, 100, 255), proj['z_tip3'], proj['z_tip2'], 2)
        pygame.draw.line(screen, (50, 100, 255), proj['z_tip2'], proj['z_tip4'], 2)
        pygame.draw.line(screen, (50, 100, 255), proj['z_tip4'], proj['z_tip1'], 2)
        
        # Draw white focal origin hub
        pygame.draw.circle(screen, (255, 255, 255), proj['origin'], 6)
        
        # --- PHASE 4: EVERY-LOOP LIVE READOUT OVERLAY ---
        roll_deg  = math.degrees(roll)
        pitch_deg = math.degrees(pitch)
        yaw_deg   = math.degrees(yaw)
        
        text_r = font.render(f"Roll:  {roll_deg:6.1f}°", True, (255, 255, 255))
        text_p = font.render(f"Pitch: {pitch_deg:6.1f}°", True, (255, 255, 255))
        text_y = font.render(f"Yaw:   {yaw_deg:6.1f}°", True, (255, 255, 255))
        
        screen.blit(text_r, (25, 25))
        screen.blit(text_p, (25, 50))
        screen.blit(text_y, (25, 75))
        
        pygame.display.flip()
        clock.tick(60) # Frame rate cap
        
    except Exception as e:
        # Ignore minor parsing/timing errors during serial hiccups
        continue

# Clean up connections on exit
ser.close()
pygame.quit()
print("Program closed smoothly.")
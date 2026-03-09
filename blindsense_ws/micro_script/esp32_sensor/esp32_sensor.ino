#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <QMC5883LCompass.h>

// --- PWM CONFIGURATION ---
const int motor1Pin = 18; 
const int motor2Pin = 19;
const int freq = 5000;     // 5kHz PWM frequency
const int resolution = 8;   // 8-bit resolution (0-255)
const int channel1 = 0;
const int channel2 = 1;

// --- STATE ---
int motorSpeeds[8] = {0, 0, 0, 0, 0, 0, 0, 0};
unsigned long last_cmd_time = 0;
const unsigned long TIMEOUT_MS = 2000;
unsigned long last_imu_time = 0;
const int IMU_INTERVAL = 50; 

Adafruit_MPU6050 mpu;
QMC5883LCompass compass;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  // Initialize PWM Channels
  ledcAttach(motor1Pin, freq, resolution); 
  ledcAttach(motor2Pin, freq, resolution);

  if (!mpu.begin()) while (1) delay(10);
  compass.init();
  // --- CALIBRATION (10 Seconds) ---
  Serial.println("CALIBRATING...");
  int16_t x_min = 32767, x_max = -32768, y_min = 32767, y_max = -32768, z_min = 32767, z_max = -32768;
  uint32_t startCal = millis();
  while (millis() - startCal < 10000) {
    compass.read();
    int16_t x = compass.getX(), y = compass.getY(), z = compass.getZ();
    if (x < x_min) x_min = x; if (x > x_max) x_max = x;
    if (y < y_min) y_min = y; if (y > y_max) y_max = y;
    if (z < z_min) z_min = z; if (z > z_max) z_max = z;
    delay(10);
  }
  compass.setCalibration(x_min, x_max, y_min, y_max, z_min, z_max);
  Serial.println("READY");
}

void loop() {
  // 1. RECEIVE (Expects: MOT,int,int,int,int,int,int,int,int)
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    if (input.startsWith("MOT,")) {
      int count = sscanf(input.c_str(), "MOT,%d,%d,%d,%d,%d,%d,%d,%d", 
                         &motorSpeeds[0], &motorSpeeds[1], &motorSpeeds[2], &motorSpeeds[3], 
                         &motorSpeeds[4], &motorSpeeds[5], &motorSpeeds[6], &motorSpeeds[7]);
      
      if (count == 8) {
        last_cmd_time = millis();
        // Update only the first two physical motors
        ledcWrite(motor1Pin, constrain(motorSpeeds[0], 0, 255));
        ledcWrite(motor2Pin, constrain(motorSpeeds[1], 0, 255));
      }
    }
  }

  // 2. SAFETY WATCHDOG
  if (millis() - last_cmd_time > TIMEOUT_MS) {
    ledcWrite(motor1Pin, 0);
    ledcWrite(motor2Pin, 0);
  }

  // 3. SEND IMU (20Hz)
  if (millis() - last_imu_time >= IMU_INTERVAL) {
    last_imu_time = millis();
    sendIMUData();
  }
}

void sendIMUData() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  compass.read();

  float roll = atan2(a.acceleration.y, a.acceleration.z);
  float pitch = atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z));
  
  // Basic Tilt Comp
  float mx = compass.getX(), my = compass.getY(), mz = compass.getZ();
  float Xh = mx * cos(pitch) + my * sin(roll) * sin(pitch) + mz * cos(roll) * sin(pitch);
  float Yh = my * cos(roll) - mz * sin(roll);

  float yaw = atan2(-Yh, Xh) * 180 / PI;
  if (yaw < 0) yaw += 360;

  Serial.print("IMU,");
  Serial.print(roll * 180/PI); Serial.print(",");
  Serial.print(pitch * 180/PI); Serial.print(",");
  Serial.println(yaw);
}
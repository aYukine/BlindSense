#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <QMC5883LCompass.h>

// --- HARDWARE OBJECTS ---
Adafruit_MPU6050 mpu;
QMC5883LCompass compass;

// --- MOTOR STATE ---
float motors[8] = {0, 0, 0, 0, 0, 0, 0, 0};
unsigned long last_cmd_time = 0;
const unsigned long TIMEOUT_MS = 2000;

// --- TIMER ---
unsigned long last_imu_time = 0;
const int IMU_INTERVAL = 50; // 20Hz

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);

  if (!mpu.begin()) {
    while (1) {
      Serial.println("MPU6050 Not Found!");
      delay(1000);
    }
  }
  
  compass.init();
  Serial.println("CALIBRATION_START: Spin the sensor around!");
  
  int16_t x_min = 32767, x_max = -32768;
  int16_t y_min = 32767, y_max = -32768;
  int16_t z_min = 32767, z_max = -32768;

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
  Serial.println("CALIBRATION_DONE");

  last_cmd_time = millis();
}

void loop() {
  // 1. RECEIVE MOTOR DATA (ROS2 -> ESP32)
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    
    if (input.startsWith("MOT,")) {
      int count = sscanf(input.c_str(), "MOT,%f,%f,%f,%f,%f,%f,%f,%f", 
                         &motors[0], &motors[1], &motors[2], &motors[3], 
                         &motors[4], &motors[5], &motors[6], &motors[7]);
      
      if (count == 8) {
        last_cmd_time = millis();
        applyMotors(); 
      }
    }
  }

  // 2. SAFETY CHECK (Watchdog)
  if (millis() - last_cmd_time > TIMEOUT_MS) {
    for(int i=0; i<8; i++) motors[i] = 0;
    applyMotors();
  }

  // 3. SEND IMU DATA (ESP32 -> ROS2)
  if (millis() - last_imu_time >= IMU_INTERVAL) {
    last_imu_time = millis();
    sendIMU();
  }
}

void sendIMU() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  compass.read();

  float roll = atan2(a.acceleration.y, a.acceleration.z);
  float pitch = atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z));

  float mx = compass.getX(), my = compass.getY(), mz = compass.getZ();
  float cosR = cos(roll), sinR = sin(roll);
  float cosP = cos(pitch), sinP = sin(pitch);

  float Xh = mx * cosP + my * sinR * sinP + mz * cosR * sinP;
  float Yh = my * cosR - mz * sinR;

  float yaw = atan2(-Yh, Xh) * 180 / PI;
  if (yaw < 0) yaw += 360;

  // Format matches our ROS2 bridge parser
  Serial.print("IMU,");
  Serial.print(roll * 180/PI); Serial.print(",");
  Serial.print(pitch * 180/PI); Serial.print(",");
  Serial.println(yaw);
}

void applyMotors() {
  //empty for now 
}
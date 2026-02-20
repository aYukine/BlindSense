#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <QMC5883LCompass.h>

Adafruit_MPU6050 mpu;
QMC5883LCompass compass;

void setup() {
  Serial.begin(115200); // RPi must match this baud rate
  Wire.begin(21, 22);

  if (!mpu.begin()) {
    while (1) delay(10);
  }
  compass.init();

  // Calibration Dance - 10 seconds of figure-8s
  int16_t x_min = 32767, x_max = -32768, y_min = 32767, y_max = -32768, z_min = 32767, z_max = -32768;
  uint32_t startTime = millis();
  while (millis() - startTime < 10000) {
    compass.read();
    int16_t x = compass.getX(), y = compass.getY(), z = compass.getZ();
    if (x < x_min) x_min = x; if (x > x_max) x_max = x;
    if (y < y_min) y_min = y; if (y > y_max) y_max = y;
    if (z < z_min) z_min = z; if (z > z_max) z_max = z;
    delay(10);
  }
  compass.setCalibration(x_min, x_max, y_min, y_max, z_min, z_max);
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  compass.read();

  float roll = atan2(a.acceleration.y, a.acceleration.z);
  float pitch = atan2(-a.acceleration.x, sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z));

  float mx = compass.getX(), my = compass.getY(), mz = compass.getZ();
  float Xh = mx * cos(pitch) + my * sin(roll) * sin(pitch) + mz * cos(roll) * sin(pitch);
  float Yh = my * cos(roll) - mz * sin(roll);

  float yaw = atan2(-Yh, Xh) * 180 / PI;
  if (yaw < 0) yaw += 360;

  // Format: roll,pitch,yaw\n
  Serial.print(roll * 180/PI); Serial.print(",");
  Serial.print(pitch * 180/PI); Serial.print(",");
  Serial.println(yaw);

  delay(50); // 20Hz
}
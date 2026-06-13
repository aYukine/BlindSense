#include <Wire.h>

const int MPU_ADDR = 0x68; // I2C address of the MPU-6050
int16_t acX, acY, acZ, tmp, gyX, gyY, gyZ;

void setup() {
  Serial.begin(115200);
  Wire.begin();
  
  // Wake up the MPU6050 (it starts in sleep mode)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); 
  Wire.write(0);     
  Wire.endTransmission(true);
}

void loop() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // Starting register for Accelerometer data
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true); // Request 14 registers total
  
  // Read Accelerometer
  acX = Wire.read() << 8 | Wire.read();  
  acY = Wire.read() << 8 | Wire.read();  
  acZ = Wire.read() << 8 | Wire.read();  
  // Read Temperature
  tmp = Wire.read() << 8 | Wire.read();  
  // Read Gyroscope
  gyX = Wire.read() << 8 | Wire.read();  
  gyY = Wire.read() << 8 | Wire.read();  
  gyZ = Wire.read() << 8 | Wire.read();  
  
  // Print values to Serial Monitor
  Serial.print("Accel: X="); Serial.print(acX);
  Serial.print(" Y="); Serial.print(acY);
  Serial.print(" Z="); Serial.print(acZ);
  Serial.print(" | Gyro: X="); Serial.print(gyX);
  Serial.print(" Y="); Serial.print(gyY);
  Serial.print(" Z="); Serial.println(gyZ);
  
  delay(200);
}
#include <Wire.h>

const int MPU_ADDR = 0x68;
int16_t acX, acY, acZ, tmp, gyX, gyY, gyZ;

// Motor Pin Definitions [cite: 10]
const int LEFT = 15;  // [cite: 10]
const int RIGHT = 0;  // [cite: 10]

// Non-blocking timer variables for IMU streaming (Target: ~50Hz / 20ms)
unsigned long lastImuTime = 0;
const unsigned long IMU_INTERVAL = 20; 

void stopAll() {
  digitalWrite(LEFT, LOW);   // [cite: 10]
  digitalWrite(RIGHT, LOW);  // [cite: 10]
}

void setup() {
  Serial.begin(115200);      // [cite: 2]
  Wire.begin();              // [cite: 2]
  
  pinMode(LEFT, OUTPUT);     // [cite: 11]
  pinMode(RIGHT, OUTPUT);    // [cite: 11]
  stopAll();                 // [cite: 11]

  // Wake up MPU6050 [cite: 2]
  Wire.beginTransmission(MPU_ADDR); // [cite: 2]
  Wire.write(0x6B);          // [cite: 2]
  Wire.write(0);             // [cite: 2]
  Wire.endTransmission(true); // [cite: 3]
}

void loop() {
  // --- Task 1: Read Serial Commands from ROS 2 Node (Instant Execution) ---
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "L_HIGH") {
      digitalWrite(LEFT, HIGH);
    } else if (command == "L_LOW") {
      digitalWrite(LEFT, LOW);
    } else if (command == "R_HIGH") {
      digitalWrite(RIGHT, HIGH);
    } else if (command == "R_LOW") {
      digitalWrite(RIGHT, LOW);
    } else if (command == "STOP") {
      stopAll();
    }
  }

  // --- Task 2: Non-blocking IMU Telemetry Stream (~50Hz) ---
  unsigned long currentTime = millis();
  if (currentTime - lastImuTime >= IMU_INTERVAL) {
    lastImuTime = currentTime;

    Wire.beginTransmission(MPU_ADDR); // [cite: 3]
    Wire.write(0x3B);                 // [cite: 3]
    Wire.endTransmission(false);      // [cite: 3]
    Wire.requestFrom(MPU_ADDR, 14, true); // [cite: 3]

    acX = Wire.read() << 8 | Wire.read(); // [cite: 4]
    acY = Wire.read() << 8 | Wire.read(); // [cite: 5]
    acZ = Wire.read() << 8 | Wire.read(); // [cite: 5]
    tmp = Wire.read() << 8 | Wire.read(); // [cite: 6]
    gyX = Wire.read() << 8 | Wire.read(); // [cite: 7]
    gyY = Wire.read() << 8 | Wire.read(); // [cite: 7]
    gyZ = Wire.read() << 8 | Wire.read(); // [cite: 8]

    // Send data up to Python [cite: 8]
    Serial.print("Accel: X="); Serial.print(acX); // [cite: 8]
    Serial.print(" Y="); Serial.print(acY); // [cite: 8]
    Serial.print(" Z="); Serial.print(acZ); // [cite: 9]
    Serial.print(" | Gyro: X="); Serial.print(gyX); // [cite: 9]
    Serial.print(" Y="); Serial.print(gyY); // [cite: 9]
    Serial.print(" Z="); Serial.println(gyZ); // [cite: 9]
  }
}
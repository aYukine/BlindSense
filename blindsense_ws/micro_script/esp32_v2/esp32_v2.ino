#include <Arduino.h>

// GPIO pin definitions for the 4 tested motors.
const int LEFT_BELOW = 15;
const int LEFT_UP = 2;
const int RIGHT_BELOW = 0;
const int RIGHT_UP = 4;

void stopAll() {
	digitalWrite(LEFT_BELOW, LOW);
	digitalWrite(LEFT_UP, LOW);
	digitalWrite(RIGHT_BELOW, LOW);
	digitalWrite(RIGHT_UP, LOW);
}

void setup() {
	pinMode(LEFT_BELOW, OUTPUT);
	pinMode(LEFT_UP, OUTPUT);
	pinMode(RIGHT_BELOW, OUTPUT);
	pinMode(RIGHT_UP, OUTPUT);

	stopAll();
}

void loop() {
	// 1. GO FRONT: All motors on for 4 seconds.
	digitalWrite(LEFT_BELOW, HIGH);
	digitalWrite(LEFT_UP, HIGH);
	digitalWrite(RIGHT_BELOW, HIGH);
	digitalWrite(RIGHT_UP, HIGH);
	delay(4000);
	stopAll();

	// 2. GO RIGHT (Horizontal Sweep)
	digitalWrite(LEFT_UP, HIGH);
	digitalWrite(LEFT_BELOW, HIGH);
	delay(500);
	digitalWrite(RIGHT_UP, HIGH);
	digitalWrite(RIGHT_BELOW, HIGH);
	delay(500);
	digitalWrite(LEFT_UP, LOW);
	digitalWrite(LEFT_BELOW, LOW);
	delay(500);
	stopAll();

	digitalWrite(LEFT_UP, HIGH);
	digitalWrite(LEFT_BELOW, HIGH);
	delay(500);
	digitalWrite(RIGHT_UP, HIGH);
	digitalWrite(RIGHT_BELOW, HIGH);
	delay(500);
	digitalWrite(LEFT_UP, LOW);
	digitalWrite(LEFT_BELOW, LOW);
	delay(500);
	stopAll();

	digitalWrite(LEFT_UP, HIGH);
	digitalWrite(LEFT_BELOW, HIGH);
	delay(500);
	digitalWrite(RIGHT_UP, HIGH);
	digitalWrite(RIGHT_BELOW, HIGH);
	delay(500);
	digitalWrite(LEFT_UP, LOW);
	digitalWrite(LEFT_BELOW, LOW);
	delay(500);
	stopAll();

	delay(1000);

	// 3. GO LEFT (Reverse Sweep)
	digitalWrite(RIGHT_UP, HIGH);
	digitalWrite(RIGHT_BELOW, HIGH);
	delay(500);
	digitalWrite(LEFT_UP, HIGH);
	digitalWrite(LEFT_BELOW, HIGH);
	delay(500);
	digitalWrite(RIGHT_UP, LOW);
	digitalWrite(RIGHT_BELOW, LOW);
	delay(500);
	stopAll();

	digitalWrite(RIGHT_UP, HIGH);
	digitalWrite(RIGHT_BELOW, HIGH);
	delay(500);
	digitalWrite(LEFT_UP, HIGH);
	digitalWrite(LEFT_BELOW, HIGH);
	delay(500);
	digitalWrite(RIGHT_UP, LOW);
	digitalWrite(RIGHT_BELOW, LOW);
	delay(500);
	stopAll();

	digitalWrite(RIGHT_UP, HIGH);
	digitalWrite(RIGHT_BELOW, HIGH);
	delay(500);
	digitalWrite(LEFT_UP, HIGH);
	digitalWrite(LEFT_BELOW, HIGH);
	delay(500);
	digitalWrite(RIGHT_UP, LOW);
	digitalWrite(RIGHT_BELOW, LOW);
	delay(500);
	stopAll();

	delay(1000);

	// 4. ROTATE RIGHT (Clockwise Circle)
	digitalWrite(RIGHT_BELOW, HIGH);
	digitalWrite(RIGHT_UP, HIGH);
	delay(4000);
	stopAll();

	// 5. ROTATE LEFT (Counter-Clockwise Circle)
	digitalWrite(LEFT_BELOW, HIGH);
	digitalWrite(LEFT_UP, LOW);
	delay(4000);
	stopAll();

	delay(1000);
}

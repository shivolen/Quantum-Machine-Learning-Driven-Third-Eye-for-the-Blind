/*
 * ESP32-CAM Portable Button Control Example
 * 
 * Add this code to your existing CameraWebServer.ino
 * to enable push button control for portable operation.
 * 
 * Wiring:
 *   Push Button: GPIO 0 → Button → GND
 *   (Uses internal pull-up, no external resistor needed)
 */

// ============================================
// ADD THESE DEFINES AT TOP OF YOUR SKETCH
// ============================================
#define BUTTON_PIN 0          // GPIO 0 for push button
#define BUTTON_DEBOUNCE_MS 200 // Debounce delay (ms)
#define LED_FLASH_PIN 4        // Built-in LED pin (if available)

// ============================================
// ADD THESE VARIABLES AFTER YOUR EXISTING ONES
// ============================================
bool buttonPressed = false;
unsigned long lastButtonPress = 0;
bool cameraStreaming = true;  // Track camera state

// ============================================
// ADD THIS IN setup() FUNCTION
// ============================================
void setupButton() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);  // Enable internal pull-up resistor
  pinMode(LED_FLASH_PIN, OUTPUT);
  digitalWrite(LED_FLASH_PIN, LOW);
  Serial.println("Button initialized on GPIO 0");
}

// ============================================
// ADD THIS NEW FUNCTION
// ============================================
void checkButton() {
  unsigned long now = millis();
  
  // Debounce: ignore rapid button presses
  if (now - lastButtonPress < BUTTON_DEBOUNCE_MS) {
    return;
  }
  
  // Button is pressed (reads LOW because of pull-up)
  if (digitalRead(BUTTON_PIN) == LOW) {
    lastButtonPress = now;
    buttonPressed = true;
    
    // Visual feedback: flash LED
    digitalWrite(LED_FLASH_PIN, HIGH);
    delay(50);
    digitalWrite(LED_FLASH_PIN, LOW);
    
    Serial.println("🔘 Button pressed!");
  }
}

// ============================================
// ADD THIS FUNCTION TO HANDLE BUTTON ACTIONS
// ============================================
void handleButtonAction() {
  if (!buttonPressed) return;
  
  buttonPressed = false;
  
  // Example action: Toggle camera streaming
  cameraStreaming = !cameraStreaming;
  
  if (cameraStreaming) {
    Serial.println("📷 Camera streaming ENABLED");
    // You can add code here to start/resume camera
  } else {
    Serial.println("⏸️  Camera streaming DISABLED");
    // You can add code here to pause/stop camera
  }
  
  // Alternative actions you could implement:
  // - Change camera quality
  // - Toggle flash LED
  // - Enter deep sleep
  // - Restart camera
}

// ============================================
// MODIFY YOUR loop() FUNCTION
// ============================================
/*
void loop() {
  // ... your existing web server code ...
  
  // ADD THESE TWO LINES:
  checkButton();           // Check for button press
  handleButtonAction();    // Handle button action
  
  delay(10);  // Small delay to prevent CPU spinning
}
*/

// ============================================
// OPTIONAL: DEEP SLEEP MODE (Save Battery)
// ============================================
/*
#include "esp_sleep.h"

void enterDeepSleep(int seconds) {
  Serial.printf("💤 Entering deep sleep for %d seconds...\n", seconds);
  esp_sleep_enable_timer_wakeup(seconds * 1000000ULL);
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, LOW);  // Wake on button press
  esp_deep_sleep_start();
}

// To use: call enterDeepSleep(60) to sleep for 60 seconds
// ESP32 will wake on button press or after timer expires
*/

// ============================================
// USAGE INSTRUCTIONS
// ============================================
/*
1. Add the defines and variables to your sketch
2. Call setupButton() in your setup() function
3. Add checkButton() and handleButtonAction() to your loop()
4. Upload code via USB (one-time)
5. Disconnect USB and power via battery/power bank
6. Press button to control camera!

Button will work wirelessly - no USB needed after initial upload!
*/


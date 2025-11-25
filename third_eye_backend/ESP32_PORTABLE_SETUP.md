# ESP32-CAM Portable Setup Guide

## 🎯 Goal
Make your ESP32-CAM fully portable with battery power and push button control, eliminating the need for USB cable connection to your laptop.

---

## 🔋 Power Solutions

### **Option 1: USB Power Bank (EASIEST) ⭐ Recommended**
- **What you need:** Any USB power bank (5V output)
- **Connection:** Connect ESP32-CAM's USB port to power bank
- **Runtime:** 5000mAh = ~20 hours, 10000mAh = ~40 hours
- **Pros:** Simple, no wiring, portable
- **Cons:** Slightly bulkier

### **Option 2: 18650 Li-ion Battery + Boost Converter**
- **What you need:**
  - 2x 18650 batteries (3.7V each, 2000-3000mAh)
  - TP4056 charging module
  - MT3608 boost converter (3.7V → 5V)
  - Battery holder
- **Connection:**
  ```
  18650 Battery → TP4056 (charging) → MT3608 (boost to 5V) → ESP32-CAM VCC
  ```
- **Runtime:** ~8-12 hours
- **Pros:** Compact, rechargeable
- **Cons:** Requires wiring and modules

### **Option 3: 3x AA Batteries + Voltage Regulator**
- **What you need:**
  - 3x AA batteries (1.5V each = 4.5V total)
  - AMS1117 5V regulator
  - Battery holder
- **Runtime:** ~4-6 hours
- **Pros:** Simple, cheap
- **Cons:** Shorter runtime, not rechargeable

---

## 🔘 Push Button Wiring

### **Simple Setup (Recommended)**
```
Push Button:
  Pin 1 → GPIO 0 (or GPIO 2)
  Pin 2 → GND

Note: Use INPUT_PULLUP in code (no external resistor needed)
```

### **Wiring Diagram:**
```
ESP32-CAM:
  GPIO 0 ──[Button]── GND
  (Internal pull-up enabled in code)
```

**Why GPIO 0?** It's available on most ESP32-CAM boards and has internal pull-up.

---

## 💻 Arduino Code Modifications

### **Add to your CameraWebServer.ino:**

```cpp
// Add at top with other pin definitions
#define BUTTON_PIN 0  // GPIO 0 for push button
#define BUTTON_DEBOUNCE_MS 200  // Debounce time

// Add after WiFi setup
bool buttonPressed = false;
unsigned long lastButtonPress = 0;

// Add in setup() function:
pinMode(BUTTON_PIN, INPUT_PULLUP);  // Enable internal pull-up

// Add new function for button handling:
void checkButton() {
  unsigned long now = millis();
  
  // Debounce: ignore rapid presses
  if (now - lastButtonPress < BUTTON_DEBOUNCE_MS) {
    return;
  }
  
  // Button pressed (LOW because of pull-up)
  if (digitalRead(BUTTON_PIN) == LOW) {
    lastButtonPress = now;
    buttonPressed = true;
    
    // Optional: Toggle LED flash to show button press
    digitalWrite(4, HIGH);  // Flash LED
    delay(100);
    digitalWrite(4, LOW);
    
    Serial.println("Button pressed!");
  }
}

// Add in loop() function (or create separate task):
void loop() {
  // ... existing web server code ...
  
  // Check button periodically
  checkButton();
  
  // Handle button action (example: toggle streaming)
  if (buttonPressed) {
    buttonPressed = false;
    // Add your button action here
    // Example: restart camera, toggle flash, etc.
  }
  
  delay(10);  // Small delay to prevent CPU spinning
}
```

### **Optional: Deep Sleep Mode (Save Battery)**

If you want the ESP32 to sleep when not in use:

```cpp
#include "esp_sleep.h"

// Add function to enter deep sleep
void enterDeepSleep(int seconds) {
  Serial.println("Entering deep sleep...");
  esp_sleep_enable_timer_wakeup(seconds * 1000000ULL);
  esp_deep_sleep_start();
}

// Wake up on button press (configure RTC GPIO)
void setupWakeOnButton() {
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, LOW);  // Wake on button press
}

// In your button handler:
if (buttonPressed) {
  // Wake from sleep or toggle mode
  // If sleeping, ESP32 will wake automatically
}
```

---

## 📡 How It Works Wirelessly

### **Current Setup:**
1. ESP32-CAM connects to WiFi: `Airtel_mela_8808`
2. Gets IP: `192.168.1.9`
3. Python client on laptop connects via WiFi (same network)
4. **No USB cable needed!** ✅

### **Portable Workflow:**
```
1. Power ESP32 with battery/power bank
2. ESP32 boots and connects to WiFi automatically
3. Press button to start/stop camera (optional)
4. Python client on laptop fetches images wirelessly
5. FastAPI processes images and generates TTS
```

---

## 🔧 Complete Portable Setup Steps

### **Step 1: Hardware Assembly**
1. Connect push button: GPIO 0 → Button → GND
2. Connect power source (USB power bank or battery setup)
3. **No USB cable to laptop needed!**

### **Step 2: Upload Modified Code**
1. Add button handling code to your Arduino sketch
2. Upload via USB (one-time setup)
3. After upload, disconnect USB
4. Power via battery/power bank

### **Step 3: Test Wirelessly**
1. Power ESP32 with battery
2. Wait for WiFi connection (LED should indicate)
3. On laptop, run: `python client/client_camera_esp32.py`
4. Should work exactly the same as before!

---

## ⚡ Power Consumption Tips

### **To Maximize Battery Life:**
1. **Reduce frame rate:** Increase `SEND_INTERVAL` in `.env` (e.g., 5-10 seconds)
2. **Lower camera resolution:** Use lower quality in camera settings
3. **Disable flash:** Keep flash off unless needed
4. **Deep sleep:** Add sleep between captures (advanced)

### **Current Consumption:**
- **Idle (WiFi on):** ~80mA
- **Active (camera + WiFi):** ~240mA
- **Transmitting:** ~300-500mA (spikes)

### **Battery Life Estimates:**
- **5000mAh power bank:** ~20 hours continuous
- **10000mAh power bank:** ~40 hours continuous
- **2x 18650 (6000mAh):** ~25 hours continuous

---

## 🎮 Button Functions (Customize as Needed)

You can program the button to do different things:

```cpp
// Example 1: Toggle camera on/off
bool cameraActive = true;
if (buttonPressed) {
  cameraActive = !cameraActive;
  // Start/stop camera stream
}

// Example 2: Change camera quality
int qualityLevel = 0;
int qualities[] = {10, 63, 95};  // Low, Medium, High
if (buttonPressed) {
  qualityLevel = (qualityLevel + 1) % 3;
  // Apply new quality
}

// Example 3: Toggle flash
bool flashOn = false;
if (buttonPressed) {
  flashOn = !flashOn;
  digitalWrite(4, flashOn ? HIGH : LOW);
}
```

---

## ✅ Testing Checklist

- [ ] ESP32 powers on with battery (no USB)
- [ ] WiFi connects automatically
- [ ] Can access `http://192.168.1.9` from laptop browser
- [ ] Push button responds (check Serial monitor during development)
- [ ] Python client connects wirelessly
- [ ] Images are captured and sent to FastAPI
- [ ] TTS audio plays correctly

---

## 🚨 Troubleshooting

### **ESP32 won't power on:**
- Check battery voltage (needs 5V)
- Verify connections are secure
- Try USB power first to test

### **WiFi won't connect:**
- Check SSID/password in code
- Ensure ESP32 is in range
- Check Serial monitor for errors

### **Button not working:**
- Verify GPIO pin number
- Check wiring (button → GPIO → GND)
- Test with Serial.println in button handler

### **Python client can't connect:**
- Verify ESP32 IP address (check router or Serial monitor)
- Ensure laptop and ESP32 on same WiFi network
- Test with browser: `http://192.168.1.9/capture`

---

## 📝 Summary

**You can make it fully portable by:**
1. ✅ Using USB power bank or battery setup
2. ✅ Adding push button for control
3. ✅ Removing USB cable (only needed for initial code upload)
4. ✅ Everything works wirelessly via WiFi

**The Python client on your laptop will work exactly the same** - it just connects via WiFi instead of requiring the ESP32 to be USB-connected!


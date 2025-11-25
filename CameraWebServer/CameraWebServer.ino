#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include "img_converters.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// WiFi credentials
const char* ssid = "Airtel_mela_8808";
const char* password = "air09602";

// Camera pins for AI-Thinker ESP32-CAM
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

httpd_handle_t camera_httpd = NULL;

// HTML page with controls
static const char STREAM_HTML[] = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>ESP32-CAM Stream</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial; text-align: center; margin: 20px; background: #1a1a1a; color: white; }
    img { max-width: 100%; height: auto; border: 2px solid #444; margin: 20px 0; }
    .controls { margin: 20px auto; max-width: 600px; }
    button { padding: 10px 20px; margin: 5px; background: #0066cc; color: white; border: none; cursor: pointer; border-radius: 4px; }
    button:hover { background: #0052a3; }
    select { padding: 8px; margin: 5px; border-radius: 4px; }
    input[type="range"] { width: 200px; }
    h1 { color: #0066cc; }
  </style>
</head>
<body>
  <h1>ESP32-CAM Live Stream</h1>
  <img id="stream" src="/stream">
  <div class="controls">
    <h3>Camera Controls</h3>
    <div>
      <label>Resolution: </label>
      <select id="framesize" onchange="updateConfig('framesize', this.value)">
        <option value="10">UXGA(1600x1200)</option>
        <option value="9">SXGA(1280x1024)</option>
        <option value="8">XGA(1024x768)</option>
        <option value="7">SVGA(800x600)</option>
        <option value="6" selected>VGA(640x480)</option>
        <option value="5">CIF(400x296)</option>
      </select>
    </div>
    <div>
      <label>Quality: </label>
      <select id="quality" onchange="updateConfig('quality', this.value)">
        <option value="10" selected>10</option>
        <option value="12">12</option>
        <option value="15">15</option>
        <option value="20">20</option>
      </select>
    </div>
    <div>
      <label>Brightness: </label>
      <input type="range" id="brightness" min="-2" max="2" value="0" onchange="updateConfig('brightness', this.value)">
    </div>
    <div>
      <label>Contrast: </label>
      <input type="range" id="contrast" min="-2" max="2" value="0" onchange="updateConfig('contrast', this.value)">
    </div>
    <div>
      <button onclick="capturePhoto()">Take Snapshot</button>
      <button onclick="toggleFlash()">Toggle Flash</button>
    </div>
  </div>
  
  <script>
    function updateConfig(key, value) {
      fetch(`/control?var=${key}&val=${value}`)
        .then(response => response.text())
        .then(data => console.log(data))
        .catch(err => console.error(err));
    }
    
    function capturePhoto() {
      window.open('/capture', '_blank');
    }
    
    function toggleFlash() {
      fetch('/flash')
        .then(response => response.text())
        .then(data => alert(data))
        .catch(err => console.error(err));
    }
  </script>
</body>
</html>
)rawliteral";

// Stream handler
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char part_buf[64];

  res = httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=frame");
  if(res != ESP_OK) return res;

  while(true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
      break;
    } else {
      if(fb->format != PIXFORMAT_JPEG) {
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if(!jpeg_converted) {
          Serial.println("JPEG compression failed");
          res = ESP_FAIL;
          break;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }
    
    if(res == ESP_OK) {
      size_t hlen = snprintf(part_buf, 64, "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", _jpg_buf_len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if(res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if(res == ESP_OK) {
      res = httpd_resp_send_chunk(req, "\r\n--frame\r\n", 13);
    }
    
    if(fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if(_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    
    if(res != ESP_OK) break;
  }
  return res;
}

// Control handler
static esp_err_t control_handler(httpd_req_t *req) {
  char buf[128];
  size_t buf_len = httpd_req_get_url_query_len(req) + 1;
  if (buf_len > 1) {
    if (httpd_req_get_url_query_str(req, buf, buf_len) == ESP_OK) {
      char param[32], value[32];
      if (httpd_query_key_value(buf, "var", param, sizeof(param)) == ESP_OK &&
          httpd_query_key_value(buf, "val", value, sizeof(value)) == ESP_OK) {
        int val = atoi(value);
        sensor_t * s = esp_camera_sensor_get();
        
        if(strcmp(param, "framesize") == 0) s->set_framesize(s, (framesize_t)val);
        else if(strcmp(param, "quality") == 0) s->set_quality(s, val);
        else if(strcmp(param, "brightness") == 0) s->set_brightness(s, val);
        else if(strcmp(param, "contrast") == 0) s->set_contrast(s, val);
        
        return httpd_resp_send(req, "OK", 2);
      }
    }
  }
  return httpd_resp_send_500(req);
}

// Main page handler
static esp_err_t index_handler(httpd_req_t *req) {
  return httpd_resp_send(req, STREAM_HTML, strlen(STREAM_HTML));
}

// Capture handler
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

// Flash handler
static esp_err_t flash_handler(httpd_req_t *req) {
  static bool flash_state = false;
  flash_state = !flash_state;
  pinMode(4, OUTPUT);
  digitalWrite(4, flash_state ? HIGH : LOW);
  return httpd_resp_send(req, flash_state ? "Flash ON" : "Flash OFF", HTTPD_RESP_USE_STRLEN);
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.stack_size = 4096;

  httpd_uri_t index_uri = {
    .uri = "/",
    .method = HTTP_GET,
    .handler = index_handler,
    .user_ctx = NULL
  };

  httpd_uri_t stream_uri = {
    .uri = "/stream",
    .method = HTTP_GET,
    .handler = stream_handler,
    .user_ctx = NULL
  };

  httpd_uri_t control_uri = {
    .uri = "/control",
    .method = HTTP_GET,
    .handler = control_handler,
    .user_ctx = NULL
  };

  httpd_uri_t capture_uri = {
    .uri = "/capture",
    .method = HTTP_GET,
    .handler = capture_handler,
    .user_ctx = NULL
  };

  httpd_uri_t flash_uri = {
    .uri = "/flash",
    .method = HTTP_GET,
    .handler = flash_handler,
    .user_ctx = NULL
  };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &stream_uri);
    httpd_register_uri_handler(camera_httpd, &control_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    httpd_register_uri_handler(camera_httpd, &flash_uri);
    Serial.println("Camera server started successfully");
  } else {
    Serial.println("Failed to start camera server");
  }
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  Serial.begin(115200);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  
  if(psramFound()) {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
    Serial.println("PSRAM found");
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    Serial.println("PSRAM not found");
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }
  Serial.println("Camera initialized");

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected!");

  startCameraServer();

  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");
  Serial.print("Stream URL: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");
}

void loop() {
  delay(10000);
}
# MoodMatrix – AI Powered Wireless Matrix Lamp  
### Emotion-Driven LED System using ESP32 + Python AI

MoodMatrix is a real-time emotion-reactive wireless LED matrix lamp powered by an ESP32 web server and a Python-based AI emotion detection engine.

The system analyzes facial expressions using DeepFace and dynamically maps emotions to advanced LED animation effects rendered on an 8x8 WS2812B matrix.

It combines:

• Embedded Systems  
• Real-time Computer Vision  
• Wireless IoT Control  
• Custom Animation Engine  
• Gesture Interaction  
• Adaptive Lighting Intelligence  

---

# 🧠 System Overview

## High-Level Architecture

Camera → Python AI Engine → Emotion Processing → Gesture Engine  
↓  
HTTP API → ESP32 Web Server → Animation Engine → LED Matrix  

The Python controller performs:
- Face detection
- Emotion classification
- Gesture tracking
- Energy modeling
- FX selection logic

The ESP32 firmware handles:
- WiFi SoftAP
- REST API server
- Pattern rendering engine
- Palette blending
- Particle system
- Pattern transitions
- LED hardware control

---

# 🔥 Core Features

## 🎭 AI Emotion Detection
- DeepFace emotion classification
- Real-time face tracking
- Emotion smoothing and decay model
- Energy-based adaptive behavior
- Comfort mode memory system

## ✋ Gesture Control
- MediaPipe Hands
- Brightness control via hand height
- Animation speed via hand velocity
- FX switching via horizontal movement
- Emotional intensity boost via hand openness

## 🌐 Wireless ESP32 Web Server
- SoftAP mode (no router required)
- Built-in modern control UI
- REST API endpoints
- Manual pixel control
- Real-time brightness & speed tuning

## 🎨 Advanced Animation Engine

### 1. Fluid / Organic FX
- Liquid Lava (3D noise)
- Caustics (Underwater ripple)
- Vortex Spiral
- Nebula Drift
- Lava Crack Pattern

### 2. Energy / Impact FX
- Lightning Strikes
- Flame Engine (Fire2012)
- Shockwave Expansion
- Cyberpunk Glitch
- Reactor Pulse Core

### 3. Space FX
- Starfield Particles
- Spiral Galaxy
- Orbital Motion
- Aurora Curtains

### 4. Geometric FX
- Kaleidoscope Mirror
- Concentric Rings
- Moving Grid
- Bloom Flower

### 5. Natural / Toy FX
- Rain System
- Snowfall
- Bounce Ball Physics
- Snake Movement
- Bubbles Engine
- Audio Visualizer Simulation
- Auto FX Cycle

### 6. Emotion Wrappers
Each emotion automatically maps to:
- Custom palette
- Specific animation
- Smooth palette blending

---

# ⚙️ Hardware Requirements

## 🧩 Components

- ESP32 Development Board
- 8x8 WS2812B LED Matrix
- 5V Power Supply (≥ 2A recommended)
- USB Cable
- Webcam (for AI controller)

## 🪛 Wiring

LED Data → GPIO 5  
LED 5V → External 5V supply  
LED GND → ESP32 GND  

Important:
Use a proper power supply for stability.

---

# 💻 Software Requirements

## Python Side

- Python 3.10 (64-bit recommended)
- DeepFace
- TensorFlow
- OpenCV
- MediaPipe
- PyQt6
- NumPy
- psutil
- pyqtgraph

## ESP32 Side

- Arduino IDE
- ESP32 Board Package
- FastLED library
- ArduinoJson library

---

# 🚀 Installation Guide

---

## 🟢 ESP32 Setup

1. Install Arduino IDE
2. Install ESP32 Board Package
3. Install Libraries:
   - FastLED
   - ArduinoJson
4. Open the provided .ino file
5. Upload to ESP32
6. After upload, ESP32 creates WiFi:
   
   SSID: ESP32_MoodMatrix  
   Password: password123  

7. Connect your PC to this WiFi
8. Open browser:
   
   http://192.168.4.1

You will see the control interface.

---

## 🔵 Python AI Controller Setup

### Step 1 – Install Python 3.10

Download from:
https://www.python.org/downloads/

Install 64-bit version.

---

### Step 2 – Clone Repository

```
git clone https://github.com/yourusername/MoodMatrix-ESP32-AI-Lamp.git
cd MoodMatrix-ESP32-AI-Lamp/python-controller
```

---

### Step 3 – Create Virtual Environment

Windows:

```
python -m venv venv
venv\Scripts\activate
```

---

### Step 4 – Install Requirements

```
pip install -r requirements.txt
```

---

### Step 5 – Run Application

```
python main.py
```

The AI Controller window will open.

---

# 🌐 API Endpoints

## Change Mode

GET  
```
/api/mode?name=happy
```

## Change Settings

POST  
```
/api/settings
{
  "brightness": 120,
  "speed": 20
}
```

## Manual Pixel Control

GET  
```
/api/pixel?x=3&y=4&r=255&g=0&b=0
```

---

# 🎨 Animation Engine Design

## Particle System

- Up to 16 particles
- Velocity-based motion
- Life decay model
- Boundary auto-destroy
- Additive blending

## Palette Blending

Smooth transitions using:

```
nblendPaletteTowardPalette()
```

Emotion changes do not cause hard cuts.
Instead, they gradually morph colors.

## Transition System

When pattern changes:

- Fade-out sequence
- Reset flag for new pattern
- Particle reinitialization
- Soft cross-pattern blending

---

# 🧠 Emotion Intelligence Model

Instead of raw dominant emotion switching:

System uses:

Emotion Energy (-100 to +100)

Positive emotions increase energy.
Negative emotions decrease energy.

Decay model slowly returns energy to neutral.

This avoids:
- Flickering
- Sudden mode switching
- Over-reactivity

---

# 📊 Performance Design

- Frame throttling via gSpeed
- AI detection interval control
- Tracker fallback when inference skipped
- 480x360 camera resolution for performance
- DSHOW capture on Windows

---

# 🏗 Project Structure

```
MoodMatrix/
│
├── esp32-firmware/
│   └── MoodMatrix.ino
│
├── python-controller/
│   ├── main.py
│   └── requirements.txt
│
├── assets/
│   ├── screenshots/
│   └── diagrams/
│
└── README.md
```

---

# 🔮 Future Enhancements

- Microphone-based sound reactive mode
- Bluetooth mode
- Mobile App Controller
- Home Assistant integration
- OLED display status
- Multi-matrix expansion
- Custom shader-based animation engine
- Edge TPU acceleration

---

# 🧪 Testing Checklist

- WiFi connection stable
- Web UI loads
- API calls responsive
- AI detection running
- Gesture override working
- Brightness control functional
- Pattern transitions smooth
- No memory leaks

---

# 📜 License

MIT License

You are free to use, modify, and distribute this project.

---

# 👨‍💻 Author

Developed as a hybrid AI + Embedded IoT system  
Combining Computer Vision, Emotion Modeling, and Real-time LED Rendering.

---

# 🏁 Final Result

MoodMatrix is not just a lamp.

It is:

- Emotion-aware lighting system
- AI-interactive device
- Wireless programmable LED engine
- Embedded + AI integration showcase
- Final-year / startup-grade product

---


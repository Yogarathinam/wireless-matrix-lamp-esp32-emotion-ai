from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSlider, QGroupBox, 
                             QProgressBar, QColorDialog, QFrame, QGridLayout, QTabWidget, 
                             QComboBox, QCheckBox, QScrollArea, QSizePolicy, QSplitter)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QColor, QFont, QPalette, QBrush
import sys
import cv2
import requests
import time
import collections
import psutil
import numpy as np
from deepface import DeepFace

# Try importing MediaPipe and PyQtGraph
try:
    import mediapipe as mp
    import pyqtgraph as pg
    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False
    print("WARNING: 'mediapipe' or 'pyqtgraph' not found. Some features disabled.")

# ==== CONFIG ====
ESP32_IP = "192.168.4.1"   
BASE_URL = f"http://{ESP32_IP}"

# Mapped to ESP32 'emo*' functions (Used for AI Logic)
EMOTION_MAP = {
    "happy":    {"mode": "happy",    "color": "#FFD700", "label": "HAPPY ✨"},
    "sad":      {"mode": "sad",      "color": "#0000FF", "label": "SAD 🌊"},
    "angry":    {"mode": "angry",    "color": "#FF0000", "label": "ANGRY 🔥"},
    "fear":     {"mode": "glitch",   "color": "#8000FF", "label": "FEAR 👻"}, 
    "surprise": {"mode": "surprise", "color": "#FFFFFF", "label": "SURPRISE 😲"},
    "disgust":  {"mode": "icon_alien","color": "#00FF00", "label": "DISGUST 👽"},
    "neutral":  {"mode": "neutral",  "color": "#00CCFF", "label": "NEUTRAL 😐"}
}

# Dynamic FX Pools for AI Rotation
EMOTION_FX_POOL = {
    "happy":    ["bubbles", "flower", "stars", "aurora", "kaleidoscope"],
    "sad":      ["liquid", "rain", "caustics", "snow"],
    "angry":    ["magma", "fire", "shockwave", "lightning"],
    "fear":     ["nebula", "glitch", "grid"],
    "surprise": ["orbit", "shockwave", "pulse"],
    "neutral":  ["nebula", "galaxy", "vortex", "liquid"],
    "disgust":  ["icon_alien", "glitch"]
}

PERSONALITY_PROFILES = {
    "Reactive": {"smooth": 3, "brightness": 120, "desc": "Fast response, high energy"},
    "Chill":    {"smooth": 10, "brightness": 60,  "desc": "Slow transitions, relaxed"},
    "Stable":   {"smooth": 6,  "brightness": 90,  "desc": "Balanced monitoring"}
}

# ==== STYLESHEET ====
MODERN_STYLE = """
    QMainWindow { background-color: #0d0d0f; color: #f0f0f0; font-family: 'Segoe UI', sans-serif; }
    
    /* Splitter */
    QSplitter::handle { background-color: #333; height: 2px; }
    
    /* Tabs */
    QTabWidget::pane { border: 1px solid #333; background: #161619; border-radius: 6px; }
    QTabBar::tab { 
        background: #202025; color: #aaa; 
        padding: 10px 25px; 
        border-top-left-radius: 6px; border-top-right-radius: 6px; 
        font-weight: bold; margin-right: 4px;
        min-width: 80px;
    }
    QTabBar::tab:selected { background: #00e676; color: #000; }
    
    /* Group Boxes */
    QGroupBox { 
        border: 1px solid #333; 
        border-radius: 8px; 
        margin-top: 12px; 
        padding-top: 24px; 
        background-color: #1a1a1d; 
    }
    QGroupBox::title { 
        subcontrol-origin: margin; left: 12px; padding: 0 5px; 
        color: #00e676; font-weight: bold; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    }
    
    /* Labels */
    QLabel { color: #ddd; font-size: 12px; }
    
    /* Buttons in Modes Grid */
    QPushButton { 
        background-color: #2a2a30; 
        border: 1px solid #444; 
        border-radius: 6px; 
        padding: 12px; 
        color: #eee; 
        font-weight: 600; 
        font-size: 12px; 
    }
    QPushButton:hover { background-color: #00e676; color: #000; border: 1px solid #00e676; }
    QPushButton:pressed { background-color: #00b359; transform: translateY(1px); }
    
    /* Sliders */
    QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }
    QSlider::handle:horizontal { background: #00e676; width: 18px; margin: -6px 0; border-radius: 9px; }
    
    /* Bars */
    QProgressBar { border: none; background-color: #111; height: 10px; border-radius: 5px; text-align: center; }
    QProgressBar::chunk { background-color: #00e676; border-radius: 5px; }
    
    /* Scroll */
    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { border: none; background: #111; width: 8px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: #444; border-radius: 4px; }
    
    /* Checkbox */
    QCheckBox { color: #ddd; spacing: 8px; font-size: 13px; }
    QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #555; background: #111; }
    QCheckBox::indicator:checked { background: #00e676; border: 1px solid #00e676; }
"""

class EmotionWorker(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    stats_signal = pyqtSignal(dict, str, dict) 
    graph_signal = pyqtSignal(str) 
    
    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.last_mode = "neutral"
        self.personality = "Stable"
        self.smoothing_buffer = collections.deque(maxlen=6)
        
        # Flags
        self.ai_enabled = True 
        self.gesture_enabled = False # Toggle state
        
        # Emotional Energy
        self.emotion_state = 0.0      
        self.decay_rate = 5.0         
        self.reactivity = 0.3         
        
        # AI Params
        self.detection_interval = 0.4  
        self.conf_threshold = 25       
        self.reactive_mode = False     
        
        # Tracking
        self.tracker = None
        self.face_box = None 
        self.frame_count = 0
        self.tracking_active = False
        self.last_inference_time = 0
        
        # Memory
        self.emotion_memory = collections.deque(maxlen=600)
        self.comfort_mode_active = False
        self.gesture_lock = False

        # Gesture State
        self.prev_hand_pos = None
        self.gesture_active = False
        self.gesture_brightness = 100
        self.gesture_speed = 20
        self.gesture_fx_index = 0

        # Metrics
        self.fps_start_time = time.time()
        self.fps_counter = 0
        self.current_fps = 0
        self.inference_time = 0

    def run(self):
        # Use DSHOW on Windows for speed
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if sys.platform == 'win32' else cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        
        mp_hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.7) if HAS_EXTRAS else None
        
        while self._run_flag:
            ret, frame = cap.read()
            if not ret: continue

            if not self.ai_enabled:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                qt_img = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.change_pixmap_signal.emit(qt_img)
                time.sleep(0.03)
                continue

            self.frame_count += 1
            
            # ================= 1. GESTURE CONTROL ENGINE =================
            self.gesture_active = False
            
            # Only run gestures if enabled AND frame modulo to save CPU
            if self.gesture_enabled and mp_hands and self.frame_count % 3 == 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                hand_results = mp_hands.process(rgb_frame)
                
                if hand_results.multi_hand_landmarks:
                    self.gesture_active = True
                    for landmarks in hand_results.multi_hand_landmarks:
                        mp.solutions.drawing_utils.draw_landmarks(frame, landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                        
                        wrist = landmarks.landmark[0]
                        thumb_tip = landmarks.landmark[4]
                        index_tip = landmarks.landmark[8]
                        pinky_tip = landmarks.landmark[20]
                        
                        hand_y = wrist.y
                        hand_x = wrist.x
                        current_pos = np.array([wrist.x, wrist.y])

                        # A. Height -> Brightness (Inverted: Top=1.0 Brightness, Bottom=0.2)
                        b_val = int(np.interp(hand_y, [0.1, 0.9], [255, 40]))
                        self.gesture_brightness = max(40, min(255, b_val))
                        cv2.putText(frame, f"BRIGHT: {self.gesture_brightness}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                        # B. Horizontal -> FX Index
                        self.gesture_fx_index = int(np.interp(hand_x, [0.1, 0.9], [0, 4]))
                        
                        # C. Hand Openness -> Intensity Boost
                        hand_span = abs(thumb_tip.x - pinky_tip.x)
                        intensity_boost = np.interp(hand_span, [0.05, 0.25], [0, 50])
                        self.emotion_state += intensity_boost * 0.1 
                        self.emotion_state = min(100, self.emotion_state)

                        # D. Velocity -> Animation Speed
                        if self.prev_hand_pos is not None:
                            velocity = np.linalg.norm(current_pos - self.prev_hand_pos)
                            s_val = int(np.interp(velocity, [0.001, 0.05], [80, 5]))
                            self.gesture_speed = s_val
                            cv2.putText(frame, f"SPEED(ms): {s_val}ms", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                            
                            # E. Swipes -> Emotion Shift
                            dx = wrist.x - self.prev_hand_pos[0]
                            if abs(dx) > 0.1: 
                                if dx > 0: self.emotion_state += 20 
                                else: self.emotion_state -= 20      
                        
                        self.prev_hand_pos = current_pos

            # ================= 2. DETECTION ENGINE =================
            run_detection = False
            if time.time() - self.last_inference_time > self.detection_interval:
                run_detection = True
            elif self.tracking_active:
                try:
                    success, box = self.tracker.update(frame)
                    if success:
                        self.face_box = tuple(map(int, box))
                    else:
                        self.tracking_active = False
                except: self.tracking_active = False

            emotions = {}
            dominant = self.last_mode

            if run_detection:
                try:
                    t0 = time.time()
                    scale_factor_ai = 0.7
                    small_frame = cv2.resize(frame, (0, 0), fx=scale_factor_ai, fy=scale_factor_ai)
                    results = DeepFace.analyze(
                        small_frame, actions=['emotion'], enforce_detection=False, 
                        silent=True, detector_backend='opencv'
                    )
                    self.inference_time = (time.time() - t0) * 1000
                    self.last_inference_time = time.time()
                    
                    if results:
                        res = results[0]
                        emotions = res['emotion']
                        
                        # Energy Engine
                        positive = emotions["happy"] + emotions["surprise"]
                        negative = emotions["sad"] + emotions["angry"] + emotions["fear"] + emotions["disgust"]
                        delta = (positive - negative) * self.reactivity
                        self.emotion_state = max(-100, min(100, self.emotion_state + delta))
                        
                        # Decay
                        if self.emotion_state > 0: self.emotion_state -= self.decay_rate
                        elif self.emotion_state < 0: self.emotion_state += self.decay_rate
                        
                        # Region
                        region = res['region']
                        coord_scale = 1.0 / scale_factor_ai
                        x = int(region['x'] * coord_scale)
                        y = int(region['y'] * coord_scale)
                        w = int(region['w'] * coord_scale)
                        h = int(region['h'] * coord_scale)
                        self.face_box = (x, y, w, h)
                        
                        try: self.tracker = cv2.TrackerCSRT_create()
                        except: self.tracker = cv2.TrackerKCF_create()
                        self.tracker.init(frame, self.face_box)
                        self.tracking_active = True
                        
                except Exception: self.tracking_active = False
            
            # ================= 3. OUTPUT LOGIC =================
            if self.face_box:
                
                current_profile = PERSONALITY_PROFILES.get(self.personality, PERSONALITY_PROFILES["Stable"])
                
                # Determine Emotion from Energy
                if self.emotion_state > 40: most_common = "happy"
                elif self.emotion_state > 10: most_common = "surprise"
                elif self.emotion_state < -40: most_common = "sad"
                elif self.emotion_state < -10: most_common = "angry"
                else: most_common = "neutral"
                
                # Memory Logic
                self.emotion_memory.append(most_common)
                recent_sadness = list(self.emotion_memory).count("sad")
                if recent_sadness > len(self.emotion_memory) * 0.4:
                    if not self.comfort_mode_active:
                        self.comfort_mode_active = True
                        most_common = "happy"
                        self.emotion_state = 50
                else:
                    self.comfort_mode_active = False

                if most_common != self.last_mode:
                    self.last_mode = most_common
                
                # Prepare System Stats
                sys_stats = {
                    "cpu": psutil.cpu_percent(),
                    "fps": self.current_fps,
                    "inference": self.inference_time,
                    "comfort": self.comfort_mode_active,
                    "energy": self.emotion_state,
                    # Gesture Data Overrides
                    "gesture_active": self.gesture_active,
                    "gesture_bri": self.gesture_brightness,
                    "gesture_spd": self.gesture_speed,
                    "gesture_fx": self.gesture_fx_index
                }
                
                self.stats_signal.emit(emotions, most_common, sys_stats)
                self.graph_signal.emit(most_common)

                # Draw UI
                x, y, w, h = self.face_box
                color = (0, 255, 157) if not self.comfort_mode_active else (0, 165, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, f"{most_common.upper()} ({int(self.emotion_state)})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # FPS
            self.fps_counter += 1
            if time.time() - self.fps_start_time > 1.0:
                self.current_fps = self.fps_counter
                self.fps_counter = 0
                self.fps_start_time = time.time()

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            qt_img = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.change_pixmap_signal.emit(qt_img)
        
        cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MoodMatrix Controller AI")
        self.resize(1300, 850)
        self.setStyleSheet(MODERN_STYLE)
        
        self.last_sent_emotion = None
        self.current_fx = None
        self.last_fx_change = 0
        self.fx_change_interval = 8
        
        # Initialize Graph Data safely (FIXED: Init here to prevent AttributeError)
        self.graph_data = collections.deque(maxlen=100)
        self.curve = None

        # Main Layout
        central = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # Splitter for Resizable Layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === LEFT PANEL CONTAINER ===
        left_widget = QWidget()
        self.setup_left_panel(left_widget)
        splitter.addWidget(left_widget)

        # === RIGHT PANEL CONTAINER ===
        right_widget = QWidget()
        self.setup_right_panel(right_widget)
        splitter.addWidget(right_widget)
        
        # Set stretch factor
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)
        
        main_layout.addWidget(splitter)

        # Start Logic
        self.worker = EmotionWorker()
        self.worker.change_pixmap_signal.connect(self.update_image)
        self.worker.stats_signal.connect(self.update_stats)
        self.worker.graph_signal.connect(self.update_graph)
        self.worker.start()

    def setup_left_panel(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 10, 0)
        
        # Camera Feed
        self.image_label = QLabel("INITIALIZING OPTICS...")
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setStyleSheet("border: 2px solid #00e676; background: #000; border-radius: 8px;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)
        
        # Status Text
        self.status_display = QLabel("SYSTEM READY")
        self.status_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_display.setStyleSheet("font-size: 24px; font-weight: 900; color: #fff; background: #1e1e24; padding: 15px; border-radius: 8px; border: 1px solid #333;")
        layout.addWidget(self.status_display)

        # Reactive Emotion Bars (Below Camera)
        bars_group = QGroupBox("LIVE EMOTION MATRIX")
        bars_layout = QGridLayout()
        self.emotion_bars = {}
        emotions_list = ["happy", "sad", "angry", "surprise", "fear", "neutral", "disgust"]
        
        for i, emo in enumerate(emotions_list):
            lbl = QLabel(emo.upper())
            lbl.setStyleSheet("font-size: 11px; color: #ccc; font-weight: bold;")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            c = EMOTION_MAP.get(emo, {}).get("color", "#888")
            bar.setStyleSheet(f"QProgressBar {{ background: #111; border: none; border-radius: 4px; }} QProgressBar::chunk {{ background: {c}; border-radius: 4px; }}")
            
            self.emotion_bars[emo] = bar
            bars_layout.addWidget(lbl, i, 0)
            bars_layout.addWidget(bar, i, 1)
            
        bars_group.setLayout(bars_layout)
        layout.addWidget(bars_group)

    def setup_right_panel(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 0, 0, 0)
        
        # 1. Toggles Group
        tog_group = QGroupBox("SYSTEM CONTROL")
        tog_layout = QVBoxLayout()
        
        self.btn_ai_toggle = QPushButton("AI: ACTIVE")
        self.btn_ai_toggle.setStyleSheet("background-color: #00e676; color: #000; font-size: 14px; padding: 12px;")
        self.btn_ai_toggle.clicked.connect(self.toggle_ai)
        tog_layout.addWidget(self.btn_ai_toggle)
        
        # GESTURE BUTTON
        self.btn_gesture = QPushButton("✋ GESTURE CONTROL: OFF")
        self.btn_gesture.setStyleSheet("background-color: #2a2a35; color: #888; font-size: 12px; padding: 10px;")
        self.btn_gesture.clicked.connect(self.toggle_gesture)
        tog_layout.addWidget(self.btn_gesture)
        
        tog_group.setLayout(tog_layout)
        layout.addWidget(tog_group)

        # 2. Tabs
        ctrl_tabs = QTabWidget()
        
        # -- MODES TAB (Full ESP32 Feature Set) --
        tab_modes = QWidget()
        modes_layout = QVBoxLayout(tab_modes)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_grid = QVBoxLayout(scroll_content)

        def add_btn_group(title, items, col_count=3):
            g = QGroupBox(title)
            gl = QGridLayout()
            gl.setSpacing(8)
            for i, (name, code) in enumerate(items):
                btn = QPushButton(name)
                btn.setMinimumHeight(45)
                btn.clicked.connect(lambda ch, c=code: self.trigger_esp32_raw(c))
                gl.addWidget(btn, i // col_count, i % col_count)
            g.setLayout(gl)
            scroll_grid.addWidget(g)

        # Matching ESP32 Firmware Categories
        add_btn_group("EMOTIONS", [
            ("😊 Happy", "happy"), ("😢 Sad", "sad"), ("😡 Angry", "angry"), 
            ("😲 Shock", "surprise"), ("😐 Calm", "neutral")
        ])
        add_btn_group("FLUID FX", [
            ("💧 Liquid", "liquid"), ("🌊 Ripple", "caustics"), ("🌀 Vortex", "vortex"), 
            ("🌫 Nebula", "nebula"), ("🌋 Magma", "magma"), ("🪨 Crack", "lavacrack")
        ])
        add_btn_group("ENERGY FX", [
            ("⚡ Bolt", "lightning"), ("🔥 Fire", "fire"), ("💥 Shock", "shockwave"), 
            ("👾 Glitch", "glitch"), ("☢ Pulse", "pulse")
        ])
        add_btn_group("SPACE FX", [
            ("🌠 Stars", "stars"), ("🌌 Galaxy", "galaxy"), ("🪐 Orbit", "orbit"), 
            ("🌈 Aurora", "aurora")
        ])
        add_btn_group("GEOMETRIC", [
            ("🧿 Kal-scope", "kaleidoscope"), ("💍 Rings", "rings"), ("🌐 Grid", "grid"), 
            ("🌸 Bloom", "flower")
        ])
        add_btn_group("FUN & TOYS", [
            ("🌧 Rain", "rain"), ("❄️ Snow", "snow"), ("🏀 Bounce", "bounce"), 
            ("🐍 Snake", "snake"), ("🫧 Bubbles", "bubbles"), ("🎵 Audio", "audio"), 
            ("🔄 Cycle", "cycle")
        ])
        add_btn_group("ICONS", [
            ("😊 Icon", "icon_happy"), ("😢 Icon", "icon_sad"), ("❤️ Icon", "icon_heart"),
            ("💀 Icon", "icon_skull"), ("👽 Icon", "icon_alien")
        ])
        
        scroll.setWidget(scroll_content)
        modes_layout.addWidget(scroll)
        ctrl_tabs.addTab(tab_modes, "MODES")

        # -- TUNING TAB --
        tab_ai = QWidget()
        ai_layout = QVBoxLayout(tab_ai)
        
        def add_slider(layout, label_text, min_val, max_val, default_val, callback):
            lbl = QLabel(f"{label_text}: {default_val}")
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(min_val, max_val)
            sl.setValue(default_val)
            sl.valueChanged.connect(lambda v: (callback(v), lbl.setText(f"{label_text}: {v}")))
            layout.addWidget(lbl)
            layout.addWidget(sl)

        grp_ai = QGroupBox("AI CONFIG")
        l_ai = QVBoxLayout()
        add_slider(l_ai, "Detection (ms)", 100, 1500, 400, self.update_detection_interval)
        add_slider(l_ai, "Reactivity", 1, 10, 3, self.update_reactivity)
        add_slider(l_ai, "Decay Rate", 1, 20, 5, self.update_decay)
        self.cb_auto_fx = QCheckBox("Auto FX Cycle")
        self.cb_auto_fx.setChecked(True)
        l_ai.addWidget(self.cb_auto_fx)
        btn_reset = QPushButton("Reset Memory")
        btn_reset.clicked.connect(self.reset_buffers)
        l_ai.addWidget(btn_reset)
        grp_ai.setLayout(l_ai)
        ai_layout.addWidget(grp_ai)
        
        # Settings Group
        grp_set = QGroupBox("LAMP SETTINGS")
        l_set = QVBoxLayout()
        self.lbl_bright = QLabel("Brightness: 100")
        l_set.addWidget(self.lbl_bright)
        self.sl_bright = QSlider(Qt.Orientation.Horizontal)
        self.sl_bright.setRange(5, 255)
        self.sl_bright.setValue(100)
        self.sl_bright.valueChanged.connect(lambda v: (self.send_setting("brightness", v), self.lbl_bright.setText(f"Brightness: {v}")))
        l_set.addWidget(self.sl_bright)
        
        self.lbl_speed = QLabel("Speed: 20")
        l_set.addWidget(self.lbl_speed)
        self.sl_speed = QSlider(Qt.Orientation.Horizontal)
        self.sl_speed.setRange(0, 100)
        self.sl_speed.setValue(20)
        self.sl_speed.valueChanged.connect(lambda v: (self.send_setting("speed", v), self.lbl_speed.setText(f"Speed: {v}")))
        l_set.addWidget(self.sl_speed)
        grp_set.setLayout(l_set)
        ai_layout.addWidget(grp_set)
        
        ai_layout.addStretch()
        ctrl_tabs.addTab(tab_ai, "TUNING")

        # -- GRAPH TAB --
        tab_graph = QWidget()
        graph_layout = QVBoxLayout(tab_graph)
        if HAS_EXTRAS:
            self.plot_widget = pg.PlotWidget(title="EMOTION TIMELINE")
            self.plot_widget.setBackground('#1a1a1d') # Matches groupbox bg roughly
            self.plot_widget.setYRange(0, 7) # 7 emotions
            # Use fixed Y-Axis Labels
            self.plot_widget.getAxis('left').setTicks([[(i, e) for i, e in enumerate(["neutral", "happy", "surprise", "sad", "angry", "fear", "disgust"])]])
            self.curve = self.plot_widget.plot(pen=pg.mkPen('#00e676', width=2))
            graph_layout.addWidget(self.plot_widget)
        else:
            graph_layout.addWidget(QLabel("Install pyqtgraph to enable graphs."))
        
        ctrl_tabs.addTab(tab_graph, "GRAPH")

        layout.addWidget(ctrl_tabs)

        # Footer
        self.sys_lbl = QLabel("CPU: 0% | FPS: 0 | LATENCY: 0ms")
        self.sys_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sys_lbl)

        btn_close = QPushButton("❌ TERMINATE SYSTEM")
        btn_close.setStyleSheet("background-color: #3d0000; color: #ff5555; border: 1px solid #ff5555; padding: 12px; font-weight: bold;")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    # ==== LOGIC ====
    def toggle_ai(self):
        self.worker.ai_enabled = not self.worker.ai_enabled
        if self.worker.ai_enabled:
            self.btn_ai_toggle.setText("AI: ACTIVE")
            self.btn_ai_toggle.setStyleSheet("background-color: #00ff9d; color: #000; padding: 10px;")
        else:
            self.btn_ai_toggle.setText("AI: STANDBY")
            self.btn_ai_toggle.setStyleSheet("background-color: #444; color: #aaa; padding: 10px;")
            self.status_display.setText("MANUAL MODE")

    def toggle_gesture(self):
        self.worker.gesture_enabled = not self.worker.gesture_enabled
        if self.worker.gesture_enabled:
            self.btn_gesture.setText("✋ GESTURE CONTROL: ON")
            self.btn_gesture.setStyleSheet("background-color: #00d4ff; color: #000; padding: 8px;")
        else:
            self.btn_gesture.setText("✋ GESTURE CONTROL: OFF")
            self.btn_gesture.setStyleSheet("background-color: #2a2a35; color: #888; padding: 8px;")

    def update_image(self, qimg):
        self.image_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def update_stats(self, emotions, dominant, sys_stats):
        if emotions:
            for emo, bar in self.emotion_bars.items():
                val = emotions.get(emo, 0)
                bar.setValue(int(val))

        if self.worker.ai_enabled:
            
            # --- DECISION LOGIC: GESTURE vs AI ---
            if sys_stats.get("gesture_active", False):
                # Gesture Override active
                brightness = sys_stats["gesture_bri"]
                speed = sys_stats["gesture_spd"]
                
                # Get FX from pool based on hand X position
                fx_pool = EMOTION_FX_POOL.get(dominant, ["neutral"])
                fx_idx = sys_stats.get("gesture_fx", 0)
                selected_fx = fx_pool[min(fx_idx, len(fx_pool)-1)]
                
                self.trigger_esp32_raw(selected_fx)
                self.send_setting("brightness", brightness)
                self.send_setting("speed", speed)
                
                # UI Update for Override
                self.status_display.setText(f"GESTURE: {selected_fx.upper()}")
                self.status_display.setStyleSheet(f"font-size: 32px; font-weight: 900; color: #00d4ff; background: #111; padding: 15px; border: 2px solid #00d4ff; border-radius: 8px;")
                
            else:
                # Standard AI Logic
                brightness = 140 if sys_stats["comfort"] else sys_stats.get("brightness", 100)
                
                if self.cb_auto_fx.isChecked():
                    now = time.time()
                    if (dominant != self.last_sent_emotion) or (now - self.last_fx_change > self.fx_change_interval):
                        self.last_sent_emotion = dominant
                        self.last_fx_change = now
                        
                        fx_pool = EMOTION_FX_POOL.get(dominant, ["neutral"])
                        energy = sys_stats.get("energy", 0)
                        intensity = abs(energy)
                        idx = int(np.interp(intensity, [0, 100], [0, len(fx_pool)-1]))
                        selected_fx = fx_pool[idx]
                        
                        self.current_fx = selected_fx
                        self.trigger_esp32_raw(selected_fx)
                        self.send_setting("brightness", brightness)
                else:
                    if dominant != self.last_sent_emotion:
                        self.last_sent_emotion = dominant
                        config = EMOTION_MAP.get(dominant, EMOTION_MAP["neutral"])
                        self.trigger_esp32_raw(config['mode'])
                        self.send_setting("brightness", brightness)
                        
                # UI Update for AI
                txt = f"COMFORT ({dominant.upper()})" if sys_stats["comfort"] else dominant.upper()
                col = "#FFA500" if sys_stats["comfort"] else EMOTION_MAP.get(dominant, {}).get("color", "#fff")
                self.status_display.setText(txt)
                self.status_display.setStyleSheet(f"font-size: 32px; font-weight: 900; color: {col}; background: #1e1e24; padding: 15px; border-radius: 8px;")

        self.sys_lbl.setText(f"CPU: {sys_stats['cpu']}% | FPS: {sys_stats['fps']} | AI: {int(sys_stats['inference'])}ms | Energy: {int(sys_stats.get('energy',0))}")
        
    def update_graph(self, emotion):
        if not HAS_EXTRAS or self.curve is None: return
        # Stable mapping
        mapping = ["neutral", "happy", "surprise", "sad", "angry", "fear", "disgust"]
        try: val = mapping.index(emotion)
        except: val = 0
        self.graph_data.append(val)
        self.curve.setData(list(self.graph_data))

    # ==== HANDLERS ====
    def update_detection_interval(self, value): self.worker.detection_interval = value / 1000.0
    def update_reactivity(self, value): self.worker.reactivity = value / 10.0
    def update_decay(self, value): self.worker.decay_rate = value
    def reset_buffers(self):
        self.worker.smoothing_buffer.clear()
        self.worker.emotion_memory.clear()
        self.worker.emotion_state = 0
        self.worker.last_mode = "neutral"
        self.last_sent_emotion = None

    def trigger_esp32_raw(self, mode_name):
        try: requests.get(f"{BASE_URL}/api/mode", params={"name": mode_name}, timeout=0.05)
        except: pass

    def send_setting(self, key, val):
        try: requests.post(f"{BASE_URL}/api/settings", json={key: val}, timeout=0.05)
        except: pass

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

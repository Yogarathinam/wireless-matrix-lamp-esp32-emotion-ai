#include <WiFi.h>
#include <WebServer.h>
#include <FastLED.h>
#include <ArduinoJson.h>

// ================= USER CONFIGURATION =================
#define LED_PIN       5
#define MATRIX_WIDTH  8
#define MATRIX_HEIGHT 8
#define NUM_LEDS      (MATRIX_WIDTH * MATRIX_HEIGHT)
#define LED_TYPE      WS2812B
#define COLOR_ORDER   GRB
#define MAX_PARTICLES 16

// Set to true for Zig-Zag layout
const bool SERPENTINE_LAYOUT = false; 

const char* ssid     = "ESP32_MoodMatrix";
const char* password = "password123";

// ================= GLOBALS & STATE =================
CRGB leds[NUM_LEDS];
WebServer server(80);
StaticJsonDocument<3000> jsonDoc;

// --- Animation & Palette State ---
uint8_t gBrightness = 60;
uint8_t gSpeed = 20;        
uint8_t gHue = 0;           
CRGBPalette16 currentPalette = RainbowColors_p;
CRGBPalette16 targetPalette = RainbowColors_p;
bool gPatternReset = false; // logic flag for init

// --- Transition System ---
uint8_t currentPatternIndex = 0;
uint8_t nextPatternIndex = 0;
bool isTransitioning = false;
uint8_t transitionProgress = 0;

// --- Particle System ---
struct Particle {
  float x, y;
  float vx, vy;
  CRGB color;
  uint8_t life;     // 0-255
  uint8_t decay;    // How fast it dies
  bool active;
};
Particle particles[MAX_PARTICLES];

// --- Bitmap Assets ---
const uint64_t IMG_HAPPY    = 0x3C4299A581A5423C;
const uint64_t IMG_SAD      = 0x3C42A5998199423C;
const uint64_t IMG_HEART    = 0x0066FF7E3C180000;
const uint64_t IMG_SKULL    = 0x3C42A581C381423C;
const uint64_t IMG_ALIEN    = 0xC3423C5A5A3C42C3;

// ================= HELPER FUNCTIONS =================
uint16_t XY(uint8_t x, uint8_t y) {
  uint16_t i;
  if (SERPENTINE_LAYOUT == false) {
    i = (y * MATRIX_WIDTH) + x;
  } else {
    if (y & 0x01) {
      uint8_t reverseX = (MATRIX_WIDTH - 1) - x;
      i = (y * MATRIX_WIDTH) + reverseX;
    } else {
      i = (y * MATRIX_WIDTH) + x;
    }
  }
  return i;
}
float randomf() {
  // random between 0.0 and 1.0
  return random(0, 1000) / 1000.0;
}

void drawBitmap(uint64_t bitmap, CRGB color) {
  for (int y = 0; y < 8; y++) {
    for (int x = 0; x < 8; x++) {
      if ((bitmap >> ((7-y)*8 + (7-x))) & 1) {
        leds[XY(x, y)] += color;
      }
    }
  }
}

// ================= PARTICLE ENGINE =================
void initParticles() {
  for(int i=0; i<MAX_PARTICLES; i++) particles[i].active = false;
}

void spawnParticle(float x, float y, float vx, float vy, CRGB color, uint8_t life, uint8_t decay) {
  for(int i=0; i<MAX_PARTICLES; i++) {
    if(!particles[i].active) {
      particles[i].x = x;
      particles[i].y = y;
      particles[i].vx = vx;
      particles[i].vy = vy;
      particles[i].color = color;
      particles[i].life = life;
      particles[i].decay = decay;
      particles[i].active = true;
      break;
    }
  }
}

void updateParticles() {
  for(int i=0; i<MAX_PARTICLES; i++) {
    if(particles[i].active) {
      particles[i].x += particles[i].vx;
      particles[i].y += particles[i].vy;
      if(particles[i].life > particles[i].decay) particles[i].life -= particles[i].decay;
      else { particles[i].active = false; continue; }
      if(particles[i].x < -2 || particles[i].x > 10 || particles[i].y < -2 || particles[i].y > 10) particles[i].active = false;
    }
  }
}

void renderParticles() {
  for(int i=0; i<MAX_PARTICLES; i++) {
    if(particles[i].active) {
      int ix = (int)particles[i].x;
      int iy = (int)particles[i].y;
      if(ix >=0 && ix < 8 && iy >=0 && iy < 8) {
        leds[XY(ix, iy)] += particles[i].color;
        leds[XY(ix, iy)].nscale8(particles[i].life);
      }
    }
  }
}

// ================= 1. FLUID / ORGANIC FX =================

void patLiquidLava() {
  // Thick molten blobs
  for(int x = 0; x < 8; x++) {
    for(int y = 0; y < 8; y++) {
      uint8_t noise = inoise8(x*40, y*40 - millis()/4, millis()/10);
      leds[XY(x,y)] = ColorFromPalette(currentPalette, noise);
    }
  }
}

void patCaustics() {
  // Underwater ripples
  for(int x = 0; x < 8; x++) {
    for(int y = 0; y < 8; y++) {
      uint8_t v = sin8(x*30 + millis()/3) + sin8(y*25 + millis()/4);
      leds[XY(x,y)] = ColorFromPalette(currentPalette, v/2 + 100);
    }
  }
}

void patVortex() {
  // Polar spiral
  for(int x = 0; x < 8; x++) {
    for(int y = 0; y < 8; y++) {
      float dx = x - 3.5;
      float dy = y - 3.5;
      float angle = atan2(dy, dx);
      float dist = sqrt(dx*dx + dy*dy);
      uint8_t hue = angle * 40 + dist * 20 - millis()/2;
      leds[XY(x,y)] = ColorFromPalette(currentPalette, hue);
    }
  }
}

void patNebula() {
  // Slow 3D noise drift
  for(int i=0; i<NUM_LEDS; i++) {
    int x = i % 8; int y = i / 8;
    uint8_t n = inoise8(x*20, y*20, millis()/30); // Very slow
    leds[i] = ColorFromPalette(currentPalette, n, map(n, 0, 255, 100, 255));
  }
}

void patLavaCrack() {
  // Dark background, bright cracks
  for(int i=0; i<NUM_LEDS; i++) {
    uint8_t n = inoise8(i*50, millis()/5);
    if(n > 230) leds[i] = CRGB::White;
    else if(n > 200) leds[i] = ColorFromPalette(currentPalette, n);
    else leds[i] = CRGB::Black;
  }
}

// ================= 2. ENERGY / IMPACT FX =================

void patLightning() {
  fadeToBlackBy(leds, NUM_LEDS, 30);
  if(random8() < 5) {
    int col = random8(8);
    for(int y=0; y<8; y++) leds[XY(col, y)] = CRGB::White; // Flash column
  }
  if(random8() < 2) {
    fill_solid(leds, NUM_LEDS, CRGB(100,100,150)); // Global flash
  }
}

void patFlame() {
  // Fire 2012 style
  static byte heat[NUM_LEDS];
  for(int i=0; i<NUM_LEDS; i++) heat[i] = qsub8(heat[i], random8(0, 10));
  for(int k=NUM_LEDS-1; k>=2; k--) heat[k] = (heat[k-1] + heat[k-2] + heat[k-2])/3;
  if(random8() < 120) heat[random8(8)] = qadd8(heat[random8(8)], random8(160,255));
  for(int j=0; j<NUM_LEDS; j++) leds[j] = HeatColor(heat[j]);
}

void patShockwave() {
  fadeToBlackBy(leds, NUM_LEDS, 60);
  static byte radius = 0;
  if(gPatternReset) radius = 0;
  
  if(radius < 12) {
    for(int x=0; x<8; x++) {
      for(int y=0; y<8; y++) {
        int dist = sqrt(pow(x-3.5, 2) + pow(y-3.5, 2));
        if(dist == radius/2) leds[XY(x,y)] += ColorFromPalette(currentPalette, gHue);
      }
    }
    if(millis() % 50 == 0) radius++;
  } else {
    if(random8() < 10) radius = 0; // Trigger new
  }
}

void patGlitch() {
  // Cyberpunk glitches
  if(random8() < 40) {
    int y = random8(8);
    for(int x=0; x<8; x++) leds[XY(x,y)] = CHSV(random8(), 255, 255);
  } else {
    fadeToBlackBy(leds, NUM_LEDS, 10);
  }
  if(random8() < 10) {
    for(int i=0; i<NUM_LEDS; i++) if(random8()>200) leds[i] = CRGB::White;
  }
}

void patPulse() {
  // Reactor core
  float breath = (exp(sin(millis()/500.0*PI)) - 0.36787944)*108.0;
  for(int x=0; x<8; x++) {
    for(int y=0; y<8; y++) {
      float dist = sqrt(pow(x-3.5, 2) + pow(y-3.5, 2));
      uint8_t bright = constrain(breath - (dist*40), 0, 255);
      leds[XY(x,y)] = ColorFromPalette(currentPalette, gHue, bright);
    }
  }
}

// ================= 3. SPACE FX =================

void patStarfield() {
  fadeToBlackBy(leds, NUM_LEDS, 20);
  if(random8() < 30) {
    spawnParticle(randomf()*8, randomf()*8, 0, 0, CRGB::White, 255, 5);
  }
}

void patGalaxy() {
  // Spiral arms
  fadeToBlackBy(leds, NUM_LEDS, 40);
  static float angle = 0;
  for(int i=0; i<2; i++) {
    float r = (sin8(millis()/20)/255.0 * 3.0) + 1.0;
    float x = 3.5 + cos(angle + i*3.14)*r;
    float y = 3.5 + sin(angle + i*3.14)*r;
    if(x>=0 && x<8 && y>=0 && y<8) leds[XY((int)x,(int)y)] = ColorFromPalette(currentPalette, angle*10);
  }
  angle += 0.1;
}

void patOrbit() {
  fadeToBlackBy(leds, NUM_LEDS, 20);
  static float angle = 0;
  float x = 3.5 + cos(angle)*3.0;
  float y = 3.5 + sin(angle)*3.0;
  if(x>=0 && x<8 && y>=0 && y<8) leds[XY((int)x,(int)y)] = CRGB::White;
  angle += 0.1;
}

void patAurora() {
  // Vertical curtains
  for(int x=0; x<8; x++) {
    uint8_t noise = inoise8(x*30, millis()/10);
    for(int y=0; y<8; y++) {
       uint8_t bright = inoise8(x*20, y*20 - millis()/5);
       leds[XY(x,y)] = ColorFromPalette(currentPalette, noise, bright);
    }
  }
}

// ================= 4. GEOMETRIC FX =================

void patKaleidoscope() {
  for(int x=0; x<4; x++) {
    for(int y=0; y<4; y++) {
      uint8_t col = inoise8(x*40, y*40, millis()/5);
      CRGB c = ColorFromPalette(currentPalette, col);
      // Mirror x4
      leds[XY(x,y)] = c;
      leds[XY(7-x,y)] = c;
      leds[XY(x,7-y)] = c;
      leds[XY(7-x,7-y)] = c;
    }
  }
}

void patRings() {
  for(int x=0; x<8; x++) {
    for(int y=0; y<8; y++) {
      float dist = sqrt(pow(x-3.5, 2) + pow(y-3.5, 2));
      uint8_t val = sin8(dist*30 - millis()/2);
      leds[XY(x,y)] = ColorFromPalette(currentPalette, val + gHue);
    }
  }
}

void patGrid() {
  fadeToBlackBy(leds, NUM_LEDS, 40);
  static int lx = 0; static int ly = 0;
  if(millis()%200==0) lx = (lx+1)%8;
  if(millis()%200==0) ly = (ly+1)%8;
  for(int i=0; i<8; i++) {
    leds[XY(lx, i)] += CRGB::Gray;
    leds[XY(i, ly)] += CRGB::Gray;
  }
}

// ================= 5. NATURAL FX =================

void patRain() {
  fadeToBlackBy(leds, NUM_LEDS, 20);
  if(random8() < 40) spawnParticle(random8(8), 0, 0, 0.2, ColorFromPalette(currentPalette, 128), 255, 5);
}

void patSnow() {
  fadeToBlackBy(leds, NUM_LEDS, 10);
  if(random8() < 20) spawnParticle(random8(8), 0, randomf()*0.1-0.05, 0.05, CRGB::White, 255, 2);
}

void patFlower() {
  // Expanding center bloom
  static float size = 0;
  if(gPatternReset) size = 0;
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  for(int x=0; x<8; x++) {
    for(int y=0; y<8; y++) {
      float dist = sqrt(pow(x-3.5, 2) + pow(y-3.5, 2));
      if(dist < size) leds[XY(x,y)] = ColorFromPalette(currentPalette, dist*30);
    }
  }
  size += 0.05;
  if(size > 5) size = 0;
}

// ================= 6. FUN / TOY FX =================

void patBounce() {
  static float bx = 3.5, by = 3.5, bvx = 0.2, bvy = 0.3;
  if(gPatternReset) { bx=3.5; by=3.5; bvx=0.2; bvy=0.3; }
  
  fadeToBlackBy(leds, NUM_LEDS, 20);
  bx += bvx; by += bvy;
  if(bx < 0 || bx > 7) bvx *= -1;
  if(by < 0 || by > 7) bvy *= -1;
  
  leds[XY((int)constrain(bx,0,7), (int)constrain(by,0,7))] = CRGB::White;
}

void patSnake() {
  fadeToBlackBy(leds, NUM_LEDS, 50);
  static float sx = 3.5, sy = 3.5;
  static float svx = 0.2, svy = 0;
  
  if(random8() < 20) {
    if(random8() > 128) { svx = 0; svy = (random8()>128 ? 0.2 : -0.2); }
    else { svy = 0; svx = (random8()>128 ? 0.2 : -0.2); }
  }
  sx += svx; sy += svy;
  if(sx<0) sx=7; if(sx>7) sx=0;
  if(sy<0) sy=7; if(sy>7) sy=0;
  
  leds[XY((int)sx, (int)sy)] = ColorFromPalette(currentPalette, gHue);
}

void patBubbles() {
  // Upward bubbles (Happy)
  fadeToBlackBy(leds, NUM_LEDS, 20);
  if(random8() < 60) spawnParticle(random8(8), 7, 0, -0.2, ColorFromPalette(currentPalette, random8()), 255, 5);
}

// ================= 7. ADVANCED FX =================

void patAudioSim() {
  // Fake EQ bars
  fadeToBlackBy(leds, NUM_LEDS, 80);
  for(int x=0; x<8; x++) {
    int height = inoise8(x*50, millis()/2);
    height = map(height, 0, 255, 0, 8);
    for(int y=7; y>7-height; y--) {
      leds[XY(x,y)] = ColorFromPalette(currentPalette, y*30);
    }
  }
}

void patCycle() {
  // Auto cycle through favorites
  static uint8_t cycleStage = 0;
  EVERY_N_SECONDS(5) { cycleStage++; if(cycleStage > 4) cycleStage = 0; }
  
  if(cycleStage == 0) patNebula();
  else if(cycleStage == 1) patRain();
  else if(cycleStage == 2) patFlame();
  else if(cycleStage == 3) patAurora();
  else patAudioSim();
}

// ================= EMOTION WRAPPERS =================
// These set specific palettes then call the generic pattern
void emoHappy() { targetPalette = PartyColors_p; patBubbles(); }
void emoSad() { targetPalette = OceanColors_p; patRain(); }
void emoAngry() { targetPalette = LavaColors_p; patGlitch(); }
void emoSurprise() { targetPalette = RainbowColors_p; patShockwave(); }
void emoNeutral() { targetPalette = ForestColors_p; patPulse(); }

// --- ICONS (Wrappers) ---
void drawHappy() { drawBitmap(IMG_HAPPY, CRGB::Yellow); }
void drawSad()   { drawBitmap(IMG_SAD, CRGB::Blue); }
void drawHeart() { drawBitmap(IMG_HEART, CRGB::Red); }
void drawSkull() { drawBitmap(IMG_SKULL, CRGB::White); }
void drawAlien() { drawBitmap(IMG_ALIEN, CRGB::Green); }

// --- UTILS ---
void patManual() { /* Wait for API */ }
void patBlackout() { fadeToBlackBy(leds, NUM_LEDS, 10); }

// ================= PATTERN REGISTRY =================
typedef void (*PatternList[])();

PatternList patterns = {
  // Emotions [0-4]
  emoHappy, emoSad, emoAngry, emoSurprise, emoNeutral,
  // Fluid [5-9]
  patLiquidLava, patCaustics, patVortex, patNebula, patLavaCrack,
  // Energy [10-14]
  patLightning, patFlame, patShockwave, patGlitch, patPulse,
  // Space [15-18]
  patStarfield, patGalaxy, patOrbit, patAurora,
  // Geom [19-22]
  patKaleidoscope, patRings, patGrid, patFlower,
  // Nature/Fun [23-28]
  patRain, patSnow, patBounce, patSnake, patBubbles, patAudioSim,
  // Utils
  patCycle, drawHappy, drawSad, drawHeart, drawSkull, drawAlien, patManual, patBlackout
};

// Map strings to indices
void setPatternByName(String name) {
  name.toLowerCase();
  uint8_t idx = 0; // Default Happy
  
  // Emotions
  if(name == "happy") idx = 0;
  else if(name == "sad") idx = 1;
  else if(name == "angry") idx = 2;
  else if(name == "surprise") idx = 3;
  else if(name == "neutral") idx = 4;
  
  // Fluid
  else if(name == "liquid") idx = 5;
  else if(name == "caustics") idx = 6;
  else if(name == "vortex") idx = 7;
  else if(name == "nebula") idx = 8;
  else if(name == "magma") idx = 9;
  
  // Energy
  else if(name == "lightning") idx = 10;
  else if(name == "fire") idx = 11;
  else if(name == "shockwave") idx = 12;
  else if(name == "glitch") idx = 13;
  else if(name == "pulse") idx = 14;
  
  // Space
  else if(name == "stars") idx = 15;
  else if(name == "galaxy") idx = 16;
  else if(name == "orbit") idx = 17;
  else if(name == "aurora") idx = 18;
  
  // Geom
  else if(name == "kaleidoscope") idx = 19;
  else if(name == "rings") idx = 20;
  else if(name == "grid") idx = 21;
  else if(name == "flower") idx = 22;
  
  // Nature/Fun
  else if(name == "rain") idx = 23;
  else if(name == "snow") idx = 24;
  else if(name == "bounce") idx = 25;
  else if(name == "snake") idx = 26;
  else if(name == "bubbles") idx = 27;
  else if(name == "audio") idx = 28;
  else if(name == "cycle") idx = 29;
  
  // Icons/Utils
  else if(name == "icon_happy") idx = 30;
  else if(name == "icon_sad") idx = 31;
  else if(name == "icon_heart") idx = 32;
  else if(name == "icon_skull") idx = 33;
  else if(name == "icon_alien") idx = 34;
  else if(name == "manual") idx = 35;
  else if(name == "off") idx = 36;
  
  if(idx != currentPatternIndex) {
    nextPatternIndex = idx;
    isTransitioning = true;
    transitionProgress = 0;
  }
}

// ================= WEB INTERFACE =================
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ULTIMATE MATRIX</title>
  <style>
    :root { --bg: #0a0a0c; --card: #141418; --accent: #00e676; --text: #ececec; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; text-align: center; padding: 10px; margin: 0; }
    
    .container { display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; max-width: 1200px; margin: auto; }
    .card { background: var(--card); padding: 20px; border-radius: 16px; box-shadow: 0 8px 16px rgba(0,0,0,0.4); flex: 1 1 300px; max-width: 400px; }
    .card h3 { border-bottom: 1px solid #333; padding-bottom: 10px; margin-top: 0; color: #888; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }

    input[type=range] { width: 100%; accent-color: var(--accent); }
    
    .grid-btn { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 8px; margin-top: 15px; }
    button { background: #222; border: 1px solid #333; color: #ccc; padding: 10px; cursor: pointer; border-radius: 8px; font-weight: 600; font-size: 0.75em; transition: 0.2s; white-space: nowrap; overflow: hidden; }
    button:hover { background: var(--accent); color: #000; transform: translateY(-2px); }
    
    .emo-btn { border-top: 3px solid #ffea00; }
    .fluid-btn { border-top: 3px solid #00b0ff; }
    .nrg-btn { border-top: 3px solid #ff3d00; }
    .space-btn { border-top: 3px solid #651fff; }
    .fun-btn { border-top: 3px solid #00e676; }
    
    .off-btn { background: #ff1744; color: white; border: none; width: 100%; margin-top: 15px; padding: 15px; font-size: 1em; }
  </style>
</head>
<body>
  <h2>✨ MATRIX OS PRO</h2>
  
  <div class="container">
    <div class="card">
      <h3>System</h3>
      <label>Brightness</label><input type="range" min="5" max="255" value="60" oninput="sendSet('brightness', this.value)">
      <br><br>
      <label>Speed</label><input type="range" min="0" max="100" value="20" oninput="sendSet('speed', this.value)">
      <button class="off-btn" onclick="setMode('off')">SYSTEM OFF</button>
    </div>

    <div class="card">
      <h3>Emotions</h3>
      <div class="grid-btn">
        <button class="emo-btn" onclick="setMode('happy')">😊 Happy</button>
        <button class="emo-btn" onclick="setMode('sad')">😢 Sad</button>
        <button class="emo-btn" onclick="setMode('angry')">😡 Angry</button>
        <button class="emo-btn" onclick="setMode('surprise')">😲 Shock</button>
        <button class="emo-btn" onclick="setMode('neutral')">😐 Calm</button>
      </div>
    </div>

    <div class="card">
      <h3>Fluid & Organic</h3>
      <div class="grid-btn">
        <button class="fluid-btn" onclick="setMode('liquid')">💧 Liquid</button>
        <button class="fluid-btn" onclick="setMode('caustics')">🌊 Ripple</button>
        <button class="fluid-btn" onclick="setMode('vortex')">🌀 Vortex</button>
        <button class="fluid-btn" onclick="setMode('nebula')">🌫 Nebula</button>
        <button class="fluid-btn" onclick="setMode('magma')">🌋 Magma</button>
      </div>
    </div>

    <div class="card">
      <h3>Energy & Space</h3>
      <div class="grid-btn">
        <button class="nrg-btn" onclick="setMode('lightning')">⚡ Bolt</button>
        <button class="nrg-btn" onclick="setMode('fire')">🔥 Fire</button>
        <button class="nrg-btn" onclick="setMode('shockwave')">💥 Shock</button>
        <button class="nrg-btn" onclick="setMode('glitch')">👾 Glitch</button>
        <button class="space-btn" onclick="setMode('stars')">🌠 Stars</button>
        <button class="space-btn" onclick="setMode('galaxy')">🌌 Galaxy</button>
        <button class="space-btn" onclick="setMode('aurora')">🌈 Aurora</button>
      </div>
    </div>
    
    <div class="card">
      <h3>Toys & Patterns</h3>
      <div class="grid-btn">
        <button class="fun-btn" onclick="setMode('bubbles')">🫧 Bubbles</button>
        <button class="fun-btn" onclick="setMode('rain')">🌧 Rain</button>
        <button class="fun-btn" onclick="setMode('snow')">❄️ Snow</button>
        <button class="fun-btn" onclick="setMode('bounce')">🏀 Bounce</button>
        <button class="fun-btn" onclick="setMode('snake')">🐍 Snake</button>
        <button class="fun-btn" onclick="setMode('flower')">🌸 Bloom</button>
        <button class="fun-btn" onclick="setMode('kaleidoscope')">🧿 Kal-scope</button>
        <button class="fun-btn" onclick="setMode('audio')">🎵 Audio</button>
        <button class="fun-btn" onclick="setMode('cycle')">🔄 Cycle</button>
      </div>
    </div>
  </div>

  <script>
    function sendSet(key, val) {
      fetch('/api/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({[key]: val}) });
    }
    function setMode(mode) { fetch('/api/mode?name=' + mode); }
  </script>
</body>
</html>
)rawliteral";

// ================= SERVER HANDLERS =================

void handleSettings() {
  if (server.hasArg("plain")) {
    String body = server.arg("plain");
    deserializeJson(jsonDoc, body);
    if (jsonDoc.containsKey("brightness")) {
      gBrightness = jsonDoc["brightness"];
      FastLED.setBrightness(gBrightness);
    }
    if (jsonDoc.containsKey("speed")) gSpeed = jsonDoc["speed"];
    server.send(200, "application/json", "{\"success\":true}");
  } else server.send(400, "text/plain", "Bad Request");
}

void handleMode() {
  if (server.hasArg("name")) {
    setPatternByName(server.arg("name"));
    server.send(200, "text/plain", "OK");
  }
}

void handlePixel() {
  currentPatternIndex = 35; // MANUAL index
  if(server.hasArg("x") && server.hasArg("y")) {
    int x = server.arg("x").toInt();
    int y = server.arg("y").toInt();
    CRGB color = CRGB::White;
    if(server.hasArg("r")) color.r = server.arg("r").toInt();
    if(server.hasArg("g")) color.g = server.arg("g").toInt();
    if(server.hasArg("b")) color.b = server.arg("b").toInt();
    if(x >=0 && x < 8 && y >= 0 && y < 8) {
      leds[XY(x,y)] = color;
      FastLED.show();
    }
    server.send(200, "text/plain", "Lit");
  }
}

// ================= MAIN LOOP =================

void setup() {
  Serial.begin(115200);
  
  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(gBrightness);
  FastLED.clear();
  
  initParticles();

  WiFi.softAP(ssid, password);
  Serial.print("AP Started: "); Serial.println(WiFi.softAPIP());

  server.on("/", [](){ server.send(200, "text/html", index_html); });
  server.on("/api/mode", handleMode);
  server.on("/api/settings", HTTP_POST, handleSettings);
  server.on("/api/pixel", handlePixel);
  
  server.begin();
}

void loop() {
  server.handleClient();
  EVERY_N_MILLISECONDS(20) { gHue++; }
  
  // 1. Palette Blending (Smooth color transitions)
  nblendPaletteTowardPalette(currentPalette, targetPalette, 48);

  static unsigned long lastFrame = 0;
  if (millis() - lastFrame > gSpeed) {
    lastFrame = millis();

    // 2. Transition Logic
    if(isTransitioning) {
      fadeToBlackBy(leds, NUM_LEDS, 40); 
      transitionProgress++;
      if(transitionProgress > 15) {
        currentPatternIndex = nextPatternIndex;
        isTransitioning = false;
        gPatternReset = true; // Signal new pattern to init
        initParticles(); 
      }
    } else {
      // 3. Render
      patterns[currentPatternIndex]();
      gPatternReset = false; // clear init flag after first frame
      
      updateParticles();
      renderParticles();
    }
    FastLED.show();
  }
}

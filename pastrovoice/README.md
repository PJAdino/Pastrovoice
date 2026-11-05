# 🎙️ PastroVoice — Layer 3: Script Generation & Dual-Voice Audio Synthesizer

> **Part of the PastroVoice Multimodal Climate Early Warning Engine for ASAL Rangelands.**  
> Layer 3 transforms structured climate, water, and agronomic indicators into authentic, broadcast-ready two-person radio dialogue and synthesizes them into `.mp3` broadcast packs for Community Radio and Feature-Phone Voice (IVR).

---

## 📋 Table of Contents
1. [Overview & Layer 2 -> Layer 3 Bridge](#1-overview--layer-2---layer-3-bridge)
2. [Quick Start (CLI)](#2-quick-start-cli)
3. [Python Integration (For Layer 4 & Layer 5 Teammates)](#3-python-integration-for-layer-4--layer-5-teammates)
4. [Input Contract & Automated Database Mapping](#4-input-contract--automated-database-mapping)
5. [Output Files (Broadcast Pack)](#5-output-files-broadcast-pack)
6. [Voice Profiles & Characters](#6-voice-profiles--characters)
7. [API Configuration & Offline Fallback](#7-api-configuration--offline-fallback)
8. [Folder Structure](#8-folder-structure)

---

## 1. Overview & Layer 2 -> Layer 3 Bridge

```
[ LAYER 2: INDICATOR DATABASE ]
  • WardIndicator (rainfall anomaly, VCI drought index)
  • WaterPoint (functional vs non-functional water pans / boreholes)
                      │
                      ▼
[ AUTOMATED BRIDGE (pastrovoice/bridge.py) ]
  • build_advisory_payload_from_db(ward_name, lang)
  • Translates raw indicators into 8 pastoralist survival facts
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 PASTROVOICE LAYER 3 ENGINE                  │
│  1. Payload Validator (payload.py)                          │
│  2. Google Gemini Scripting (script_generator.py)           │
│  3. Dual-Voice Neural Audio Synthesizer (audio_synthesizer) │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼ (.mp3 Audio + .json Cue-Sheet)
[ LAYER 4: Radio Station ZIP Packs & IVR Phone Systems ]
[ LAYER 5: Institutional Web Command Cockpit ]
```

### What Layer 3 Delivers:
* **Automated Layer 2 Bridge (`bridge.py`):** Automatically queries ward indicators and real water points and compiles the advisory payload on the fly.
* **Natural Studio Format:** Two distinct radio personalities — a female radio host (**Fatuma Hassan**) and a male agricultural/veterinary officer (**Dr. Peter Leruk**).
* **Zero Jargon:** Translates complex SPI indices and satellite moisture anomalies into 6 practical pastoralist survival cues (rainfall outlook, pasture, dry water points, operational water points, market timing, veterinary action).
* **Dual Language:** Supports both **Kiswahili** (`--lang sw`) and **English** (`--lang en`).
* **Authentic Voices:** Powered by authentic Kenyan neural voice models (`sw-KE-ZuriNeural` & `sw-KE-RafikiNeural`).
* **Zero-Downtime Guarantee:** Automatically falls back to offline reference dialogues if the Gemini API or network encounters temporary rate limits or 503 load spikes.

---

## 2. Quick Start (CLI)

Run Layer 3 directly from your terminal. It automatically bridges to the database:

```powershell
# 1. Generate a Kiswahili broadcast for Laisamis Ward (auto-queries Layer 2):
python -m pastrovoice.engine --ward "Laisamis" --lang sw

# 2. Generate an English broadcast for North Horr Ward:
python -m pastrovoice.engine --ward "North Horr" --lang en

# 3. Specify a custom output folder:
python -m pastrovoice.engine --ward "Marsabit Central" --lang sw --out "broadcast_packs"
```

---

## 3. Python Integration (For Layer 4 & Layer 5 Teammates)

If you are building the **Radio Station Pack Builder (Layer 4)**, the **IVR phone flow (Layer 4)**, or the **Streamlit Command Cockpit (Layer 5)**, you can generate a complete broadcast with a single Python function:

```python
from pastrovoice import run_pastrovoice

# Option A: Run directly from Layer 2 Database (Fully Automated Bridge)
# It queries the DB for Laisamis, writes the script, and builds the MP3:
result = run_pastrovoice(ward="Laisamis", lang="sw", output_dir="output")

print(result["audio_file"])   # Path to master .mp3 (e.g. "output/Laisamis_sw_advisory.mp3")
print(result["script_file"])  # Path to studio cue sheet .json
print(result["script"])       # Raw dialogue Python dictionary
print(result["file_size_kb"]) # MP3 size in KB

# Option B: Run with custom/in-memory data passed from Layer 2
custom_payload = {
    "ward_name": "Loiyangalani",
    "county": "Marsabit",
    "language": "sw",
    "urgency_level": "Severe",
    "weather_outlook": "Mvua haitarajiwi; upepo mkali na jua kali litaendelea.",
    "pasture_status": "Malisho yamepungua kwa kiasi kikubwa kuelekea ziwa.",
    "critical_water_point_dry": "Visima vya mchanga vya jirani vimekauka.",
    "safe_water_point_available": "Borehole ya Loiyangalani mjini bado inafanya kazi.",
    "market_advice": "Punguzeni mifugo dhaifu sokoni kabla bei haijaporomoka zaidi.",
    "veterinary_action": "Chanja mbuzi dhidi ya maradhi ya CCPP kabla ya kusafiri."
}

result = run_pastrovoice(
    ward="Loiyangalani",
    lang="sw",
    custom_payload=custom_payload,
    output_dir="output"
)
```

---

## 4. Input Contract & Automated Database Mapping

The bridge (`pastrovoice/bridge.py`) automatically maps raw database values into these 8 required fields:

| Field Name | Type | Description | Source in Layer 2 |
| :--- | :--- | :--- | :--- |
| `ward_name` | `string` | Target administrative ward in Marsabit | `WardIndicator.ward_code` |
| `county` | `string` | Target county | Fixed (`"Marsabit"`) |
| `weather_outlook` | `string` | 14-day rainfall and temperature forecast | Mapped from `rain_pon3` / `rain_mm` |
| `pasture_status` | `string` | Vegetation cover / forage condition | Mapped from `vci` / `vci3` thresholds |
| `critical_water_point_dry` | `string` | Compromised or non-functional water pan/well | `WaterPoint (reported_status='non_functional')` |
| `safe_water_point_available` | `string` | Verified functional water point/borehole | `WaterPoint (reported_status='functional')` |
| `market_advice` | `string` | Livestock trading/destocking recommendation | Derived agronomic rule |
| `veterinary_action` | `string` | Urgent herd vaccination / treatment guidance | Derived veterinary rule |

---

## 5. Output Files (Broadcast Pack)

Each run produces two synced assets in the designated output folder:

1. **`{Ward}_{lang}_advisory.mp3`**: The combined radio-ready master audio clip with alternating host and expert turns.
2. **`{Ward}_{lang}_script.json`**: The complete text cue-sheet for radio studio presenters and archival reference:
   ```json
   {
     "ward": "Laisamis",
     "language": "Kiswahili",
     "dialogue": [
       {
         "speaker": "mtangazaji",
         "text": "Hamjamboni na karibuni kwenye Makala Maalum ya Hali ya Hewa na Malisho. Jina langu ni Fatuma Hassan..."
       },
       {
         "speaker": "mtaalamu",
         "text": "Asante sana Fatuma, na nawatakia heri wafugaji..."
       }
     ]
   }
   ```

---

## 6. Voice Profiles & Characters

Layer 3 uses dual neural speech profiles to create an authentic studio interview dynamic:

| Character | Role | Kiswahili Voice | English Voice | Style / Tone |
| :--- | :--- | :--- | :--- | :--- |
| **Fatuma Hassan** | Radio Host (`mtangazaji`) | `sw-KE-ZuriNeural` | `en-KE-AsiliaNeural` | Welcoming, warm, community broadcaster |
| **Dr. Peter Leruk** | Senior Livestock Officer (`mtaalamu`) | `sw-KE-RafikiNeural` | `en-KE-ChilembaNeural` | Calm, authoritative, trusted technical advisor |

---

## 7. API Configuration & Offline Fallback

* **Live Mode:** Put your Google AI Studio API key in `.env` at the project root:
  ```env
  GEMINI_API_KEY=AIzaSy...
  ```
  Layer 3 calls `gemini-3.5-flash-lite` with native JSON mode enforcement.
* **Offline / Fallback Mode:** If no key is set, or if Google servers experience high demand (HTTP 503), the engine automatically falls back to pre-computed reference dialogue without crashing, ensuring smooth local development and offline demonstrations.

---

## 8. Folder Structure

```
pastrovoice/
├── __init__.py               # Public API exports (run_pastrovoice, build_advisory_payload_from_db, etc.)
├── README.md                 # This documentation file
├── bridge.py                 # Layer 2 -> Layer 3 automated indicator mapper
├── engine.py                 # Master orchestrator & CLI entrypoint
├── payload.py                # Schema validator & test fixture loader
├── script_generator.py       # Google Gemini LLM caller with offline fallback
├── audio_synthesizer.py      # Edge-TTS dual-voice synthesizer and stitcher
│
├── prompts/
│   ├── radio_sw.txt          # Swahili broadcast prompt template (Fatuma & Dr. Leruk)
│   └── radio_en.txt          # English broadcast prompt template
│
└── samples/
    ├── sample_payload.json   # Marsabit County benchmark data
    └── sample_script.json    # Reference multi-turn cue-sheets (Swahili & English)
```

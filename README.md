# RaidR

### Computer Vision & OCR-Driven GUI Automation Research Suite

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey.svg)](https://www.microsoft.com/windows)
[![OpenCV](https://img.shields.io/badge/Computer%20Vision-OpenCV-green.svg)](https://opencv.org/)
[![Tesseract OCR](https://img.shields.io/badge/OCR-Tesseract%205-orange.svg)](https://github.com/tesseract-ocr/tesseract)

**RaidR** is an educational open-source research testbed exploring real-time computer vision (OpenCV), optical character recognition (Tesseract OCR), and non-intrusive GUI automation patterns on Windows desktop environments.

Developed as a case study in **black-box UI testing and visual telemetry** against dynamic, adversarially animated graphical targets, RaidR demonstrates how an external system can perceive, analyze, and interact with complex interactive software through pure visual observation:
- **Zero memory tampering:** No process memory reading or DLL injection.
- **Zero packet manipulation:** No network hooking or protocol spoofing.
- **Pure external observation:** Operates solely via screen capture, template matching, OCR heuristics, and standard OS accessibility input messages.

💬 **Community Discussions:** [https://discord.gg/TWwc4W6eMq](https://discord.gg/TWwc4W6eMq)

<p align="center">
  <img src="docs/raidr_preview.png" alt="RaidR UI running alongside target window" width="850"/>
</p>

---

## What It Does

RaidR provides an autonomous session execution pipeline powered by non-intrusive computer vision and real-time OCR telemetry:

- **Automated Raid & Match Navigation:** Identifies matchmaking controls, scans available resource targets with configurable minimum loot thresholds (Gold, Elixir, Dark Elixir), and navigates the search interface automatically.
- **Visual Strategy & Unit Deployment:** Executes tactical troop deployment routines using template matching to recognize unit badges in the deployment bar. Supports standard presets (*Full Four-Edge Spam*, *Diamond Perimeter*, *Corner Focus*) as well as customized multi-unit configurations via the visual **Strategy Designer**.
- **Visual Upgrade Advisor (OCR-driven):** Reads the builder overview menu directly using Tesseract 5 OCR to evaluate upgrade costs and allocate available resources:
  - **Maxer Heuristic:** Prioritizes defense and building upgrades while safeguarding higher-tier progression milestones until structures are maxed.
  - **Rusher Heuristic:** Commits to central progression targets as soon as resource requirements are met.
  - **Dry Run Mode:** Simulates and logs would-be upgrades without issuing input clicks—ideal for verifying OCR accuracy and decision rules.
- **Intelligent Idle & Resource Gatekeeper:** Automatically detects when builders are fully utilized or resource storages reach capacity. Rather than initiating redundant cycles that would waste resources, the engine enters an intelligent **Idle state**, periodically polling builder timers and resuming activity as soon as capacity frees up.
- **Batch Wall Upgrade Heuristics:** Automatically pools excess elixir and gold into sequential wall upgrades above user-defined reserve thresholds, preserving adequate reserves for match entry fees.
- **Live Optical Telemetry & Performance Metrics:** Tracks gold, elixir, and dark elixir acquisitions directly from post-battle and HUD overlays. Calculates real-time **gain-per-hour** performance rates verified across multiple frames to eliminate OCR noise.
- **Dual Village Support:** Autonomous session management for both primary village and secondary base architectures.
- **Error Recovery & Pop-up Handling:** Automatically recognizes and recovers from unexpected interruption dialogues, disconnects, confirmation prompts, and reward overlays.

---

## Technical Architecture & Core Capabilities

### 1. Computer Vision Pipeline (OpenCV)
- **Multi-Scale Normalized Cross-Correlation:** Uses `cv2.matchTemplate` with dynamic fallback thresholds (0.78 down to 0.62) to reliably identify user interface buttons, unit badges, and dialog elements across varying graphics configurations and resolutions.
- **Adaptive Region-of-Interest (ROI) Masking:** Evaluates segmented frame regions (e.g., bottom deployment bar, upper resource HUD) to accelerate inference latency and avoid false-positive matches in animated background terrain.
- **Integrated Real-Time Cropping Utility (`GameCropWindow`):** Built-in visual snip tool allowing users to extract high-precision pixel crops directly from the live application surface for custom entity registration.

### 2. Optical Character Recognition & Telemetry (Tesseract 5)
- **HUD Metric Extraction:** Digitizes real-time resource tallies, builder availability counters, and timers directly from screen buffers.
- **Multi-Frame Consistency Verification:** Mandates agreement across successive capture frames with sanity-check bounds filtering, eliminating OCR jitter or transient visual artifacts.
- **Building Menu Parsing:** Scans upgrade dialogs to parse building identifiers and upgrade costs before committing visual interactions.

### 3. Human-Centric Input Kinematics
- **Cubic Bézier Curve Trajectory Planning:** Simulates natural ergonomic mouse trajectories with non-linear velocity easing (`-(cos(pi * t) - 1) / 2`).
- **Dynamic Dwell Times & Position Jitter:** Injects micro-variations into mouse dwell durations and target coordinates to model realistic human interaction patterns.
- **Discrete Perimeter Tapping:** Uses coordinate quantization to distribute tap sequences evenly across application boundaries while respecting safe margins (`y >= 50` and `y <= 0.77 * height`).

### 4. Autonomous State Machine & Error Recovery
- **Modal Dialogue Handling:** Automatically detects and resolves modal interruption dialogues, network disconnect notices, and confirm prompts.
- **State Transition Safeguards:** Verifies state transitions (such as builder counter increments or screen transitions) before proceeding down execution trees.
- **Visual Log Archiving:** Saves anomalous visual frames to `%LOCALAPPDATA%\RaidR\debug\` for inspection and model evaluation.

### 5. Strategy Designer & Custom Multi-Troop Sequencer
- **Visual Strategy Editor:** Interactive Qt dialog to configure multi-unit sequences with custom deployment patterns:
  - *Diamond Perimeter:* Uniform perimeter spread across top boundary lines.
  - *Full Four-Edge Spam:* Balanced tap distribution spanning all four quadrants of the arena.
  - *Custom Zone Clusters:* Matrix-based 5-point coordinate clusters mapped to resolution.
  - *Corner Focus:* Focused regional deployment with localized dispersion.

### 6. Modern PySide6 Desktop Interface
- **Frosted Glass Styling:** Modern Qt6 interface with 13 built-in themes (including Minimal Monochrome, Crimson Sunset, Electric Blue, Deep Midnight Navy, Cyberpunk Teal, and Pure Pitch Black).
- **Session Telemetry:** Real-time data readouts showing runtime, session statistics, rate-per-hour telemetry, and active worker indicators.

---

## System Requirements

- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **Runtime Environment:** Google Play Games on PC (standard 16:9 / 16:10 isometric view)
- **Display Aspect Ratio:** **16:9** (native 2560×1440 or scaled equivalent) or **16:10** (2560×1600)
- **Display Scaling Note:** If using an ultrawide (21:9) monitor, set the display to 16:9 in *Settings → Switch display to 16:9*, restart the target application to lock aspect ratio, then restore your native resolution.

---

## Installation & Usage

### Option 1: Standalone Binary (Recommended)

1. Download the pre-compiled `RaidR.exe` from [GitHub Releases](../../releases/latest).
2. The executable is self-contained with the Tesseract OCR engine bundled in (no external dependencies required).
3. Configuration and session logs reside in `%LOCALAPPDATA%\RaidR\`.

### Option 2: Running from Source

**Prerequisites:** Python 3.11+ on Windows.

1. Clone the repository:
   ```bash
   git clone https://github.com/staticmooniq/RaidR.git
   cd RaidR
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure Tesseract 5 is installed (e.g., via Chocolatey: `choco install tesseract` or from UB-Mannheim). Set `TESSERACT_CMD` environment variable if installed in a non-standard path.
4. Launch the application:
   ```bash
   python main.py
   ```

### Option 3: Building Standalone Executable

To compile into a standalone `.exe` using PyInstaller:

```bash
# Stage tesseract bundle into tesseract_bundle/ (contains tesseract.exe, DLLs, and tessdata/)
pyinstaller RaidR.spec --noconfirm
```
The compiled output will be generated in `dist/RaidR.exe`.

---

## Command Line Automation Interface

RaidR supports headless or scripted test execution via CLI arguments:

```bash
# Run continuous telemetry and test evaluation
RaidR.exe --autostart --minutes 0 --walls --upgrades maxer
```

Flags:
- `--autostart`: Automatically begins execution upon launch.
- `--minutes <n>`: Session duration in minutes (`0` for continuous execution).
- `--upgrades <mode>`: Upgrade heuristic (`off`, `dry`, `maxer`, `rusher`).
- `--walls`: Enables batch wall coordinate evaluation.

---

## Visual Unit Configuration Guide

For standard benchmark testing:
- **Army Composition:** 42 Valkyries, 11 Earthquake spells, 1 Siege machine, plus hero units.
- **Deployment Bar Configuration:** Keep target unit icons visible in the standard deployment bar for reliable template matching.
- **Custom Unit Snapping:** Open the *Strategy Designer*, click **Snip from Game** on any troop row to capture real-time pixel crops directly from the live window.

---

## Acknowledgments & Credits

- Special thanks and attribution to [efebolukbasi/BasePilot](https://github.com/efebolukbasi/BasePilot) for the foundational inspiration, early concepts, and architectural patterns that inspired this project.
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for the optical character recognition engine.
- [OpenCV](https://opencv.org/) for real-time computer vision primitives.
- [PySide6](https://wiki.qt.io/Qt_for_Python) for modern Qt interface bindings.

---

## License

Distributed under the [MIT License](LICENSE).
Tesseract OCR is bundled under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).

---

## Educational & Academic Research Disclaimer

> [!IMPORTANT]
> **PLEASE READ CAREFULLY BEFORE USING THIS SOFTWARE:**
> 
> RaidR is an open-source research suite published strictly for **educational, academic, and software engineering research purposes**. It is designed as a real-world case study exploring the implementation of real-time computer vision, optical character recognition (OCR), and non-intrusive GUI automation patterns against dynamic, animated graphical targets.
> 
> - **Pure External Observation:** Operates solely via screen capture, template matching, OCR heuristics, and standard OS accessibility input messages. It performs zero memory reading, zero DLL injection, zero binary modification, and zero network packet inspection.
> - **Platform Guidelines & User Responsibility:** Automated interaction with third-party software may conflict with platform rules or end-user terms. This project is intended solely as an academic proof-of-concept and technical demonstration, not for disruptive or unfair use. Users assume full personal responsibility for how they choose to evaluate, run, or utilize this codebase.
> - **No Warranty & Limitation of Liability:** This software is provided "as is", without warranty of any kind, express or implied. The author and contributors assume no liability for any direct, indirect, incidental, or consequential damages or actions resulting from the use or misuse of this codebase.
> - **Trademark & Fair Use Notice:** All product names, logos, trademarks, and registered trademarks belong to their respective owners. *Clash of Clans* and *Supercell* are registered trademarks of Supercell Oy. This project is an independent educational research suite and is not affiliated with, endorsed by, authorized by, or in any way officially connected to Supercell Oy.

# Changelog

All notable changes to the RaidR project are documented in this file.

## [1.1] - 2026-11-10

### Added
- **Text-Only Templates for Wall Actions:** Added clean text-only templates for `Upgrade More`, `Add Wall`, and `Remove Wall` across both 16:9 and 16:10 aspect ratios to ensure 100% template match confidence regardless of wall level graphics.
- **5-Wall Batch Upgrade Routine:** Builder Base wall upgrading now operates in batches of 5 walls at a time, calculating affordability and safely executing the batch.
- **Strict Anti-Inactivity Zoom:** Implemented `anti_inactivity_zoom` to simulate random zoom in/out cycles strictly every 2 minutes, preventing automatic logout due to inactivity.
- **Automated Bundled Tesseract Discovery:** Automatic fallback and binding for `tesseract_bundle/tesseract.exe` in source execution mode without requiring system-wide installation.
- **CLI Automation Flag:** Added `--bb-walls-only` (and `tools/run_bb_walls_only.py`) for standalone or automated Builder Base wall upgrading.
- **In-App Changelog Viewer:** Added a Changelog dialog in the settings interface to inspect version history and new features.

### Fixed
- Fixed Builder Base wall upgrader failure caused by template mismatch on Level 8+ wall icons.
- Fixed `_bb_wall_batch_sequence` failure where unlimited adds waited indefinitely for unaffordable resource states.
- Fixed OCR failure in dev/source mode when Tesseract was not installed in `Program Files`.
- Fixed window enumeration across isolated desktop sessions in Windows API.

---

## [1.0.2] - 2026-11-06
- Added loot-based matchmaking filters, including optional dark-elixir filtering and configurable skip limit.
- Tracked loot from pre-attack HUD with configurable post-star cleanup delay.
- Added optional secondary troop deployment with icon template and configurable count.
- Recovered from Clan Capital screen using Return Home button.
- Bundled Tesseract OCR in standalone build.

---

## [1.0.1] - 2026-11-06
- Added auto-updater service with in-app banner and modal dialog.
- Added support for Windows 10/11 taskbar thumbnail integration.

---

## [1.0.0] - 2026-10-26
- Initial release of RaidR research automation suite.

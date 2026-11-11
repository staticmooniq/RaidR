# Changelog

All notable changes to the RaidR project are documented in this file.

## [1.2] - 2026-11-11

### Added
- **Universal Depleted Card Filter:** Real-time color channel divergence filter ignores exhausted `x0` cards (troops, spells, knocked-out heroes) across all attack strategies to prevent post-deploy button spamming.
- **Hero Ability Timing in Strategy Editor:** Configure individual hero abilities to trigger `Never`, `Random (5–12s)`, or custom seconds after deployment.
- **Dual-Resource Wall Upgrading:** Builder Base checks wall prices and upgrades with both Gold and Elixir every 5 battles.
- **Automated Loot Cart Collection:** Collects Builder Base elixir loot cart every 8 battles with multi-threshold recognition and camera settling.
- **4-Second Build Button Detection:** Dedicated 4-second wait for the Build button after battle ends to ensure the Builder Base screen settles before opening the build panel.
- **Clean Single-Tap Builder Base Deploy:** Eliminated accidental duplicate clicks and removed post-deploy camp re-clicks.

---

## [1.1] - 2026-11-10

### Added
- **Dual-Resource Wall Upgrading (Gold + Elixir):** Builder Base wall upgrader now checks and upgrades 5x walls with Gold, and if Elixir is also available, performs a second pass to upgrade 5x walls with Elixir in the same cycle.
- **Hero Ability Trigger Timing in Strategy Editor:** Configure each individual hero's ability trigger timing with options for `Random (5–12s)`, `Custom delay (seconds)`, or `Never` (leaves ability for auto-activation or manual use), complete with quick presets (`All Random`, `All 15s`, `All Never`).
- **Post-Deployment Verification & Recheck Sweep:** The bot now actively re-scans the bottom deployment bar after deploying armies. If any troops, heroes, siege machines, or spells were missed (due to tap lag, frame drops, or red forbidden drop boundaries), the bot selects and deploys them immediately.
- **Builder Base Multi-Camp & Hero Deployment:** Builder Base attacks now explicitly cycle through each Army Camp slot individually and verify Battle/Flying Machine deployment with multi-threshold fallback, preventing missed camp troops.
- **In-Built Game Launcher:** Added a one-click "🎮 Launch Game" button to the top navigation bar and the Run page controls to launch Clash of Clans directly via Google Play Games PC.
- **Strict Background Window Input Isolation:** Hardened input dispatch to strictly target the game window surface (`hwnd`). Completely eliminated cursor movement (`SetCursorPos`) and hardware wheel events (`mouse_event`) so browsing YouTube or working in other apps will never experience unwanted clicks, cursor jumps, or scrolls.
- **No-Steal Window Restore:** Background capture restores minimized windows via `SW_SHOWNOACTIVATE` without stealing foreground focus from the user's active apps.
- **Text-Only Templates for Wall Actions:** Added clean text-only templates for `Upgrade More`, `Add Wall`, and `Remove Wall` across both 16:9 and 16:10 aspect ratios to ensure 100% template match confidence regardless of wall level graphics.
- **5-Wall Batch Upgrade Routine:** Builder Base wall upgrading now operates in batches of 5 walls at a time, calculating affordability and safely executing the batch.
- **Battle & Deployment Keep-Alive Protection:** Anti-inactivity zoom is strictly paused during battles and troop drops, only running while safely idling in the village.
- **Automated Bundled Tesseract Discovery:** Automatic fallback and binding for `tesseract_bundle/tesseract.exe` in source execution mode without requiring system-wide installation.
- **CLI Automation Flag:** Added `--bb-walls-only` (and `tools/run_bb_walls_only.py`) for standalone or automated Builder Base wall upgrading.
- **In-App Changelog Viewer:** Added a Changelog dialog in the settings interface to inspect version history and new features.

### Fixed
- Fixed accidental clicks and scrolls on YouTube and external windows during background automation.
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

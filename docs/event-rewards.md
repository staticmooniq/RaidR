# Timed Attack Rewards & Event Overlays

The event overlay at 33%, 66%, and 100% pauses input interactions while its countdown
automatically selects a reward. The visual state engine verifies that the modal disappears before resuming.
No OCR or reward-card interaction is required. A cancellation signal interrupts the wait.

The primary strategy's End Battle and Exit rules remain unchanged. The engine does
not wait for later milestones if conditions are met. Final metric tallying can advance during exit confirmation.
Hero abilities retain their stored deployment slots; only an unexpected layout shift
requires relocating the live hero portrait if the unit selection bar moves.

Validation: `python -m unittest discover -s tests -v`.
Live validation at 1299x731 confirmed unit ability triggers,
automatic reward selection after roughly 12 seconds, and battle completion after passing
50% (55% on the results screen).

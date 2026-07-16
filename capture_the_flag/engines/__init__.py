"""Game-playing engines for Capture the Flag.

Subpackages that need optional dependencies (e.g. `neural_network`, which
imports `torch` from the `learning` extra) are deliberately not re-exported
here: import them explicitly on the code path that uses them, so the base
install keeps working without the extras.
"""

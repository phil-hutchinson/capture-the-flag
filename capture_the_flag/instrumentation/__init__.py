"""Game-agnostic measurement apparatus.

Nothing in this subpackage knows anything about Capture the Flag: it is the
shareable half of story 00000029, kept free of game imports so it can migrate to
`game-engine-core` later (CLAUDE.md's shared-asset convention). The
game-specific wiring — which regions exist, what a run records — lives in the
game package that consumes it.
"""

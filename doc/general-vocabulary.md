# General Vocabulary

A living glossary of non-domain terms (machine learning, game theory, search,
and related computer-science concepts) that have come up in developer
discussion — built up by `/learning-assistant` rather than written in one
pass. Entries are short, plain-language groundings, not formal definitions.
Game-specific terms already have a glossary in
[`doc/ruleset/rules.md`](ruleset/rules.md#7-glossary); this document is for
everything else.

Avoid trademarked product names here — describe concepts generically.

## Machine learning

**Inductive bias** — knowledge built into a model's structure rather than
learned from data, biasing it toward solutions of a known shape. Convolutions
are an inductive bias ("patterns that work in one place work everywhere");
choosing whether to encode a game symmetry into the network or let training
discover it is choosing how much inductive bias to add.

**Equivariance / weight sharing** — a model is equivariant to a transform when
shifting the input shifts the output the same way, usually achieved by reusing
(sharing) the same weights across positions. Convolutions are equivariant to
board translation; the same trick can be applied along any axis with a genuine
symmetry (e.g. piece rank, when interactions depend only on rank differences).

## Neural networks

**Feature plane / channel** — one 2D grid-shaped layer of a network's input,
holding a single kind of fact about each board square (e.g. "is there an own
Knight here"). Planes stack along the *channel* axis to form the full input
(a 12×12×N tensor is an N-channel image). Only the grid axes carry spatial
meaning; channels have no adjacency or ordering significance, so their order
just needs to be fixed and consistent.

**One-hot encoding** — representing a category as a vector (or plane stack)
that is all zeros except a single 1 marking which category applies. Preferred
over numeric codes (Knight=3, Tower=7) because a network would otherwise have
to learn to undo the arbitrary arithmetic relationships the codes imply.

**Cumulative (thermometer) encoding** — an ordinal alternative to one-hot:
entry *k* means "value is *k* or beyond," so a rank-2 piece lights planes 2
through 6 rather than plane 2 alone. Makes order comparisons ("outranks")
directly readable as differences, letting one learned pattern apply across
all rank levels.

## Game theory

## Search / PUCT

## Mathematics

**Involution** — an operation that is its own undo: applying it twice gets you
back exactly where you started (like flipping a card face-down and back). Both
a 180° board rotation and a single-axis mirror are involutions; that property
is what lets the encoder and decoder share one perspective transform without
needing separate "forward" and "inverse" versions.


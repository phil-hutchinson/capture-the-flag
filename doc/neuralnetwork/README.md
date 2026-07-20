# Engine I/O specifications

This folder holds the **input/output specifications** for the game's neural
network engines. Each spec (`eng-nn-{n}.md`, named `ENG_NN_{n}`) defines the
tensor contract between the game and a network: how a position becomes the
network's input, and how the network's outputs are interpreted as a position
value and ply preferences.

A spec deliberately says **nothing about network internals** — architecture,
depth, width, layer types, or parameter counts. Any network whose input and
output tensors match the spec satisfies it. This is what lets internals evolve
freely (a deeper or wider stack, a different body) without breaking consumers,
and it is what makes the spec the complete integration contract for anything
that runs a network without this codebase — training pipelines, batch runners,
or an external front end driving an AI opponent from an exported model.

## What a spec contains

- **Name** — the spec's identifier, `ENG_NN_{n}`.
- **Compatible rulesets** — a list of ruleset combinations, each a complete
  `(version, name, flags)` triple (e.g. version `1.2`, name `PRE-RELEASE`,
  flags none). Compatibility is listed per combination, not as independent
  lists of versions and flags — a flag compatible under one version may not
  be under another.
- **Input** — the input tensor's shape and the meaning of every axis and
  feature plane, including perspective conventions (inputs are always from
  the side to move's viewpoint) and how board coordinates map to tensor
  indices.
- **Output** — the shape and interpretation of the value output and the
  policy output, including the action-space layout that maps policy entries
  to plies, and the value's perspective convention.

## Ruleset compatibility

A ruleset combination is compatible with a spec exactly when:

1. the input encoding can **faithfully represent every distinguishable game
   state** of that ruleset (two positions that differ under the rules must
   encode differently), and
2. the action space can **index every ply that ruleset can ever make legal**.

Ply *legality* is not part of the test — legality always comes from the rules
engine at decode time; the spec only has to be able to address whatever the
engine says is legal. So a rule change that only restricts or relaxes which
plies are legal (e.g. dropping a placement-formation rule) leaves the spec
compatible, while a change that introduces new state the planes cannot express
or new ply geometry the action space cannot address (e.g. a capture along a
diagonal, with an eligibility condition) requires a new spec.

Rules changes are not the only trigger: adding feature planes purely for
feature engineering — new derived inputs with no rule change at all — also
changes the tensor contract and therefore also requires a new spec.

## Versioning

The `{n}` in `ENG_NN_{n}` increments whenever the tensor contract changes, for
any reason: input shape or plane semantics, action-space layout, perspective
or normalisation conventions, whether driven by a rules change or by feature
engineering. Network-internal changes never increment it.

Once trained parameters exist against a spec, that spec is **immutable**:
later edits may clarify wording but must not alter the contract. A contract
change mints a new spec document with the next number; superseded specs stay
in this folder for as long as parameters trained against them exist.

## Relationship to trained networks

A spec describes a *class* of networks; a trained network is an *artifact*
instantiating exactly one spec. Metadata that belongs to the artifact — which
ruleset combination it was trained under, its architecture and
hyperparameters, training provenance — is recorded with the artifact, not in
the spec. In particular, a network may legally *play* under any ruleset
combination its spec lists as compatible, but its judgment is only calibrated
for the combination it was trained on; the spec answers "can it play there,"
the artifact's metadata answers "was it trained for there."

The intended distribution form for a trained network is a portable model
interchange file (see the general vocabulary) bundling the computation graph
and parameters, stamped with its spec name and trained ruleset in the file's
metadata. Consumers then need only that file, a runtime, and the named spec
document here to encode positions and decode results. The exact artifact
format is settled in the training story; this folder only owns the specs.

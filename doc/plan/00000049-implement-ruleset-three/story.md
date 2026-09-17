# Story 49: Implement Ruleset Three

## Summary

Implement major 3 in code, and publish it.

[Story 46](../00000046-document-ruleset-three/story.md) wrote a complete major 3
as **shadow documents** under [`doc/ruleset/proposed-3/`](../../ruleset/proposed-3/README.md)
and published nothing. This story takes the decision that story deferred: major 3
is adopted, it **replaces** major 2 rather than joining it, and the shadow folder
graduates into the published documents.

1. **The shadow folder graduates.** `proposed-3/rules.md`, `start-position.md`,
   `technical-notes.md` and `changelog.md` become the published documents at
   `doc/ruleset/`, and `proposed-3/` goes away. `3-0:PRE-RELEASE` is published and
   becomes the only Active edition.
2. **The rules engine is rewritten to major 3.** An open 8 × 8 board, a 16-piece
   army over five ranks with **rank 5 strongest**, direction-relative
   encumbrance, diagonal attack against every piece behind an open-path
   requirement, **rank reduction** on surviving combat, attrition endings, and a
   40-ply inactivity limit.
3. **Generation replaces placement.** Phase 1 is deleted outright. A game begins
   from a generated, fully visible starting position, and a **position ID** names
   one.
4. **Major 2 is retired.** `2-0:BATTLE`, `2-0:CLASH` and `2-1:SKIRMISH` become
   historical. Nothing plays them, and every artifact stamped with them — records
   on disk, training runs, checkpoints — is stranded deliberately and not
   migrated.
5. **The learned engine follows.** A new engine spec covers the new army and
   board; the tensor layout, the evaluator's planes, and checkpoint stamping move
   to it. Training *quality* is not in this story — only that the learned engine
   builds, self-plays, and trains under major 3.

## Context: the documents describe a game the code cannot play

The gap this story closes is intentional, unlike the one story 37 closed. Story
46 was documentation-only by design and put its ruleset in a shadow folder
precisely so that nothing outside it could depend on it — the front-end player
application could prototype major 3 while this repository went on playing major 2
undisturbed.

That arrangement has an explicit exit condition, stated in
[`doc/ruleset/CLAUDE.md`](../../ruleset/CLAUDE.md): *if a shadow ruleset is
adopted, its documents merge into or replace their counterparts at this level and
the folder goes away; if it is abandoned, the folder is deleted and nothing
breaks. Either way the decision is explicit — a shadow folder never graduates by
drift.*

This story is that explicit decision. It is also why implementing major 3 cannot
be done against the shadow documents: no code may cite one as a definition, so
the documents have to be published *before* the engine can be checked against
them. That ordering is a constraint on the implementation plan, not a
formality — `doc/ruleset/CLAUDE.md`'s standing rule is that the document leads and
the code follows.

## The decision this story makes: major 3 replaces major 2

Story 46 left the fate of the major 2 rulesets open and did not prejudge it. The
decision is: **major 3 replaces them, and no backward compatibility is
maintained.**

**What that means concretely.**

- `3-0:PRE-RELEASE` is the only Active edition. `ACTIVE_EDITIONS` is a set of one
  and `DEFAULT_EDITION` names it.
- `2-0:BATTLE`, `2-0:CLASH` and `2-1:SKIRMISH` keep their rows in `EDITIONS` and
  are **historical**. They stay nameable so that a record already stamped with one
  still names something meaningful, which is the standing rule that editions are
  never removed from the table. Retaining a *label* is not backward compatibility:
  no code path can set one up, and `unsupported_aspects` refuses them as
  historical exactly as it already refuses `1-2:PRE-RELEASE`.
- **Every existing checkpoint becomes unloadable**, twice over: on its ruleset
  stamp (a historical edition) and on its engine-spec stamp (a superseded spec).
  Training runs under `training-runs/` are left where they are and are not
  migrated, retrained or converted. This is the same outcome story 37 accepted for
  `1-2:PRE-RELEASE` artifacts, and it is intended behaviour rather than a gap.
- **The Tower and lakes leave the code**, not just the rules text. So does phase 1.
  There is no configuration under which any of them comes back.

**Why replacement rather than coexistence.** The repository's configuration model
is scoped *within* a major by construction: a rule flag is a point of variation in
one baseline rules text, with a default that preserves behaviour. Major 3 is a
different baseline — it inverts what a rank digit means, makes a piece's rank
mutable, deletes a phase of the game, and changes the notation. None of that is
expressible as a flag, which is the argument story 46 already made for why it
needs a major at all. Carrying both would mean a `major` axis above the flag
model, with every rules module branching on it permanently, to keep playable a
set of rulesets the project is moving off.

**Why `PRE-RELEASE` keeps its name.** The name is reused from `1-2:PRE-RELEASE`,
retired at major 1. That is a deliberate choice and not an oversight: an edition
id carries its major, so `1-2:PRE-RELEASE` and `3-0:PRE-RELEASE` are distinct
permanent labels that can never collide, and the ruleset *name* is a pointer by
definition — `PRE-RELEASE` means whichever edition of it is Active, which is now
the major 3 one. The name says what is true: the game is not finished.

## Specification

### 1. Documents: the shadow folder graduates

| Document | Change |
|---|---|
| `doc/ruleset/rules.md` | replaced by `proposed-3/rules.md`, with its draft banner removed and its Appendix rewritten to publish `3-0:PRE-RELEASE` as Active and list the major 2 editions as Historical |
| `doc/ruleset/start-position.md` | new, from `proposed-3/start-position.md` |
| `doc/ruleset/technical-notes.md` | replaced by `proposed-3/technical-notes.md`, plus the two corrections story 46 listed as owed on adoption: the within-major scoping of "a notation break moves every live ruleset to the next major at once", and anything that generalises over the major 2 rulesets |
| `doc/ruleset/changelog.md` | the `proposed-3/changelog.md` entry published at the top, newest first, recording story 49 and the date, and marked published rather than proposed |
| `doc/ruleset/proposed-3/` | deleted |
| `doc/ruleset/proposed-variants.md` | `DIAGONAL_ATTACKABLE` and `DIAGONAL_ATTACK_PATH` are **withdrawn, not graduated**: both are baseline behaviour at major 3, and there is no longer a major 2 for them to be proposals against. The file records that outcome rather than deleting the entries silently |
| `doc/ruleset/CLAUDE.md` | one Active edition instead of three; the shadow-folder section reduced to the general rule now that no shadow folder exists; the army/board "three places" tables restated for a single board and army |
| `CLAUDE.md` (root) | the game is no longer two-phase and no longer has secret placement; the ruleset/edition vocabulary section restated for the live ruleset |
| `README.md` | placement, the `placements/` folder, the ruleset list, and the record example all change |
| `doc/neuralnetwork/eng-nn-4.md` | new spec (see §9) |

**The changelog entry is the deliverable consumers actually track.** It is already
written, in the form they track, and states its own breaking changes; publishing
it is mostly a matter of moving it and changing its status.

### 2. The board and the army

**The board.** 8 × 8, `home_rows` 2, and **no lakes**. `BoardLayout` loses
`lake_rows`, `lake_pattern`, `lake_squares`, `lane_squares`,
`lane_adjacent_squares`, `is_lake`, and the validation that exists to catch a lake
in a home zone. What remains is dimensions, home-zone depth, and the derived home
square sets.

**`BoardLayout` and `ArmyComposition` survive as values even though there is now
exactly one of each.** `CtfPosition.layout` is the only channel move generation
has — `legal_plies` is an argument-less protocol property — so collapsing the
layout back into module constants would undo the seam story 37 built and would
have to be rebuilt the first time major 3 grows a second board. The cost of
keeping them is one instance apiece.

**Their ids are internal now, and must not reuse a published label.**
`standard_64` permanently names the *Skirmish* board, which is 8 × 8 **with
lakes**; the major 3 board is a different board and needs a different id. Since
major 3 publishes no `BOARD_LAYOUT` flag, the id is no longer a published value
label at all — it appears only in the engine-spec name and in error messages. The
same applies to the composition id.

**The army.** Three each of ranks 1–5 plus one Flag: 16 pieces, filling 16 home
squares exactly.

| Rank | Name | Symbol |
|---|---|---|
| 5 | Master-of-Arms | `5` |
| 4 | Champion | `4` |
| 3 | Foot Soldier | `3` |
| 2 | Militia | `2` |
| 1 | Peasant | `1` |
| — | Flag | `F` |

**Rank 5 is now the strongest.** `PieceType` loses `TOWER`, `KNIGHT` and
`HALBERDIER`, gains `PEASANT`, and every remaining member's rank changes.
`Mobility` survives with one immobile piece instead of two.

**The army exactly fills the home zone**, which retires the "an army must fit its
home zone" inequality check in favour of an equality: 16 pieces into 16 squares,
with no arrangement leaving a home square empty.

### 3. Movement

- **Encumbrance becomes direction-relative.** A piece is encumbered *for a
  direction of travel* when an enemy stands on any of the five squares ahead of or
  beside it in that direction; the three behind it do not encumber. Today
  encumbrance is one boolean per piece, computed once from all eight surrounding
  squares and applied to every direction. It becomes one answer per direction, so
  the same piece may have a two-square move one way and a one-square move another.
  It is still judged only from the square the piece starts on.
- **Diagonal attack applies to every enemy piece, the Flag included.** The
  movable-target restriction is deleted. With no Tower, the Flag was its only
  remaining subject, and major 3 deliberately makes the Flag diagonally
  capturable.
- **A diagonal attack requires an open path.** At least one of the two squares
  orthogonally adjacent to both attacker and target must be empty, whichever side
  occupies them. This is a generation-time restriction, like the ones it replaces:
  a diagonal attack that is generated resolves by exactly the rules an orthogonal
  one does.
- **White's first ply of the game is limited to one square.** This is the one
  movement rule that is not a function of the board — it depends on *when* in the
  game the position occurs, so `CtfPosition` must carry enough state to answer it.
  A ply count is the general form of that state and is preferred to a boolean.
- The two-square move, its clear-intermediate-square requirement, and the
  no-two-square-diagonal rule are unchanged.

**Lakes leave move generation entirely**: the walk stops at the board edge, a
friendly piece, or the first enemy, and nothing else.

### 4. Combat and rank reduction

- **Higher rank wins.** Every rank comparison inverts. So does the formation
  bonus's "one rank stronger", which now means one *higher*.
- **The Tower branch is deleted.** Attacking a Tower was the only combat outcome
  that did not follow from rank.
- **Any piece that survives combat is reduced by one rank**, attacker and defender
  alike. A draw reduces nothing, because it leaves no survivor. Capturing the Flag
  is not combat and does not reduce the capturing piece.

**Rank reduction needs no new state.** A piece's rank is expressed by *which*
`PieceType` stands on a square, so reduction is a substitution of one member for
the next one down — the board mapping already carries it, and a position is still
fully described by its board. What it does need is an explicit rank-to-piece
relation, which today exists only implicitly.

**Where it lives is `transitions.py`, not `combat.py`.** `resolve_combat` answers
who survives; reduction is what happens to the survivor as the board is rebuilt,
and the attacker-wins and attacker-loses branches each reduce a different piece.
Keeping combat resolution a pure question about an attack, and reduction a
property of applying one, is what keeps the formation bonus evaluable at the
moment the rules say it is evaluated.

**Rank 1 never survives combat** — it draws against another rank 1 and loses to
everything above — so no piece can be reduced below rank 1 and there is no floor
case to implement. That is an invariant worth asserting rather than a branch worth
writing.

**A rank's population is no longer bounded by the army composition.** Three
Master-of-Arms winning three fights produce three more rank 4s on top of the three
that started there. Anything that treats a composition count as a maximum is wrong
after the first combat of the game — see §9 and §10 for the two places that
currently do.

### 5. Starting the game: generation replaces placement

Phase 1 is deleted. `placement.py`, `placement_file.py`, the `placements/`
directory and their tests go; so do the `CtfPlayer.get_placement` seam,
`PlayerContext.placements_dir`, the `--placements-dir` option, and the
placement fields on `MatchResult`.

What replaces them is a start-position module implementing
`doc/ruleset/start-position.md`:

- **Generation.** Draw White's arrangement uniformly from the constrained set —
  the Flag on a uniform square of row 1, the 15 numbered pieces shuffled into the
  remaining 15 squares — and derive Black's by the strength rule: sum the ranks of
  the seven numbered pieces in the Flag's half, half-turn at 22 or more, reflect
  at 21 or less.
- **The threshold is derived and must be derived in code**, from the army rather
  than written as the literal 22, with the general form the document states.
  Carrying a constant that is correct only for three each of ranks 1–5 is exactly
  the hazard the document calls out.
- **Position IDs.** Encode, decode, and *validate* — the encoding is sparse, so a
  reader must check that a code has exactly three each of `1`–`5`, exactly one
  `F`, and that `F` among the first eight characters. Sixteen uppercase hex
  characters, case-normalised on input, handled as a string.
- **A position is never generated by drawing a random ID.**
- **Mirror-equivalent positions are not collapsed.** A `mirror_of` helper is
  permitted for study; the generator must not apply one.

**Seeding.** `--seed` currently seeds placement, play and network init; it now
seeds start-position generation in placement's stead, and a seeded run must
produce the same starting position it did before the run was interrupted.

**New surface.** The runners gain a way to name a starting position
(`--start-position <ID>`), which is what makes the document's stated purpose —
replaying a position, and playing it twice with the sides reversed — reachable
from this repository rather than only from the front end.

### 6. Endings

| Ending | Change |
|---|---|
| Flag capture | unchanged |
| **Attrition** | replaces "no legal move": a player with no numbered pieces loses immediately, checked after every ply rather than at the start of a turn. The Flag does not count |
| **Mutual attrition** | new: one ply leaving both players with no numbered pieces is a draw |
| Inactivity | limit drops from **50 to 40** |
| Resignation, draw by agreement | published in the rules, not implemented here (see below) |

**Ordering.** Mutual attrition must be tested before single-side attrition, or a
mutual trade would be scored as a win for whoever moved last. Attrition and
inactivity cannot collide: attrition follows a capture, and every capture resets
the inactivity counter.

**The no-legal-move loss disappears, and nothing replaces it.** On an open board a
player holding at least one numbered piece always has a legal ply — if every
orthogonal neighbour of every one of a player's pieces were friendly or off-board,
that player would have to occupy the whole board. The engine should assert that
rather than branch on it: an empty ply list is now a bug, not a game ending.

**Resignation is deliberately not implemented**, following the precedent already
set by draw by agreement, which `rules.md` has published since major 1 and which
no code path produces. Both are declared by a player rather than read off the
board, and neither the runners nor any engine here has a seat that declares one.
The reason vocabulary in the rules covers them; the engine's does not need to.

### 7. Notation

- **The `=N` mark.** A square may carry `=N` immediately after it, meaning the
  piece that began the ply there survived and is now rank `N`. Every combat ply
  marks each of its two squares exactly once, with `x` or `=N` — never both, never
  neither.
- **`A2-A4x` always means a Flag capture**, since it is the only ply that leaves a
  source square unmarked while removing the destination piece.
- **The plain form is no longer a record form.** `A2A4` cannot carry `=N`, so it
  survives only as input notation in the text interface. It remains `CtfPly`'s
  identity string.
- **The position block loses `XXX` and `T`.** No lakes means no lake cell is ever
  rendered; no Tower means no `T` symbol exists.
- **An optional `[StartPosition "…"]` header tag** carries the position ID on a
  record. Optional means a reader must not require it, and it is redundant with
  the position block that follows.

Survival is read off the resulting board today, which is what keeps the annotation
from re-deriving a combat result; `=N` extends that — the survivor's new rank is
read from the same place.

### 8. Configuration and stamping

**Major 3 publishes no rule settings**, so `RULE_FLAGS` becomes empty and
`GameSetup` stops resolving flags: `BOARD_LAYOUT`, `ARMY_COMPOSITION` and
`TOWER_PLACEMENT` were published against a rules text that no longer exists, and
Appendix A goes away with it.

**The machinery around the registry stays.** `RulesetConfiguration`,
`resolve_flag`, `canonicalize`, `unsupported_aspects` and
`configuration_differences` are how artifacts are stamped and how a stamp is
refused, and they are already written against injected tables rather than against
the published ones — their tests supply flags and editions the registry does not
contain, which is what keeps them meaningful with an empty registry. The first
major 3 flag then has somewhere to land.

**A stamp from major 2 fails on two counts** — a historical edition, and flags
this build no longer carries — and both are reported, which is the right message
for whoever is holding the artifact.

`ACTIVE_RULESETS`, `DEFAULT_RULESET` and `setup_for_ruleset` survive with one
entry. The runners keep `--ruleset` with a single choice rather than dropping it:
the option is how a run says what it is stamping, and re-adding it later is worse
than leaving it in place.

### 9. The learned engine

**A new engine spec, `ENG_NN_4`, with its own document.** The input contract
changes, which is what
[`doc/neuralnetwork/README.md`](../../neuralnetwork/README.md) says increments the
number:

- the Tower presence planes have no subject;
- there is no rank 6, and rank 1 is now the weakest rather than the strongest, so
  every rank plane's meaning changes even where its index does not;
- the passability plane is constant on a board with no lakes;
- **the per-rank quantity planes are removed entirely** (see below).

**The action space does not change.** All twelve movement offsets — one- and
two-square orthogonal, and the four diagonals — still address every ply major 3
can make legal. The first-ply restriction and the open-path rule only remove
legality, which is never part of the spec's compatibility test.

**The quantity planes go, rather than being repaired.** Each of the twelve is a
per-rank census normalised by the army's starting count of that rank, so it reads
1.0 at full strength — and rank reduction breaks the normaliser outright, because a
rank's population can now exceed the count it started with. Rather than choose a
new divisor now, `ENG_NN_4` drops the planes: they were feature engineering
(story 26) rather than a faithfulness requirement, the presence planes they were
derived from still carry the same information positionally, and major 3 changes
enough about material — a mutable rank, a smaller board, an army that fills its
home rows — that the right form for a material summary is worth re-deciding on
evidence rather than porting.

**This is explicitly reversible and expected to be revisited.** Re-adding a
material feature later is a new spec and a new document, which is the normal cost
of a feature-engineering change and is what `doc/neuralnetwork/README.md` already
requires. Removing them now means the first major 3 network is trained without
them, so any later re-add has a baseline to be measured against — which the
current arrangement, where they have never been ablated, does not provide.

**No new plane is needed for White's first ply**, even though two positions with
identical boards can differ in whether the restriction applies. Reaching a
repeat of the starting arrangement takes non-capturing plies, which raise the
inactivity counter — and that is already encoded, so the two positions do encode
differently. This is worth stating in the spec document, because it is the kind of
thing that looks like a compatibility failure until the argument is written down.

**Checkpoints.** The spec stamp and the ruleset stamp both move; existing
checkpoints are rejected by either one alone. No migration path is written.

### 10. Runners, UI, and the rest of the stack

- **`match.py`** loses phase 1: `build_initial_position` generates a starting
  position instead of collecting two placements, and `MatchResult` loses its
  placement fields. **`CtfPositionFactory`** is the same seam for self-play and
  moves with it — it exists because the library's `position_factory` contract is
  zero-arg, which generation satisfies as readily as placement did.
- **`player.py`** loses `get_placement` from the `CtfPlayer` protocol and from
  both implementations, along with the placement dialogue and its clear-screen
  handling.
- **`game_view.py`'s captured summary** is computed as "starting count minus what
  is on the board", which rank reduction makes meaningless — a rank can gain
  members. It becomes a census of what is standing, with losses derived from the
  army total rather than per rank.
- **`game_ui.py`'s illegal-ply explanations** must cover the new restrictions: a
  diagonal onto an empty square, a diagonal whose path is closed, a two-square
  move that is encumbered *in that direction*, and White's first ply.
- **`game_runner.py` / `batch_runner.py` / `training_runner.py`** lose the
  placement options and gain the start-position ones; every `--ruleset` choice
  list collapses to one entry.
- **Tests.** `test_placement.py` and `test_placement_file.py` are replaced by
  start-position tests; `test_board`, `test_pieces`, `test_moves`, `test_combat`,
  `test_outcome`, `test_transitions`, `test_record`, `test_rendering`,
  `test_game_view` and the neural-network tests are all rewritten against major 3
  rather than adjusted.

## Out of scope

- **Training runs and strength.** No training run, no retuning, no strength
  comparison, and no claim that the network learns major 3 well. The requirement
  is that the learned engine builds, self-plays, trains and checkpoints under the
  new rules — not that it plays them well.
- **Migrating anything.** No conversion of records, runs or checkpoints stamped at
  major 2, and no compatibility shim for reading them.
- **A record reader, parser, or replay validator.** Still absent by design; this
  repository writes records and does not read them.
- **Resignation and draw by agreement in the engine**, per §6.
- **A second major 3 edition, or any rule flag.** Major 3 launches with no
  settings and this story adds none.
- **Renaming the ruleset.** `PRE-RELEASE` is retained deliberately (see above).
- **The front-end player application**, which consumes the published changelog and
  is not this repository's to change.

## Known risks and open items

- **Rank reduction's main risk is passivity.** Using your best piece costs you a
  rank, which may make strong pieces reluctant. It is the first thing to watch,
  and self-play under this story is the first opportunity to look at it.
- **40 plies is provisional**, in the same sense 50 always was, and is the first
  number to revisit once games have been played.
- **The removed quantity planes are an open question deferred, not settled**
  (§9). Whether a material summary earns its place in the input, and in what form
  now that a rank's population is unbounded, is to be decided on evidence from
  major 3 training rather than now.
- **Scale.** This is a rewrite of the rules layer rather than a change to it, and
  the test suite goes with it. The plan sequences it so that each step leaves the
  repository runnable, but there is no ordering under which the engine is playable
  at both majors at once, and no attempt is made to find one.

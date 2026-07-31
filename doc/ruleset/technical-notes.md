# Capture the Flag — Ruleset Technical Notes

Companion to [`rules.md`](rules.md). `rules.md` is deliberately kept clean enough
to hand to a player as-is, so anything that is really a developer- or
design-facing annotation lives here instead. Nothing in this file changes how the
game is played; it records metadata, provisional values, and cross-references to
the rest of the project.

## Rulesets, editions, and flags

- **Active editions:** `2-0:BATTLE` and `2-0:SKIRMISH`. The full list, active and
  historical, is [`rules.md`](rules.md) Appendix B; the revision history is
  [`changelog.md`](changelog.md).
- `rules.md` is the **single source of truth** for the ruleset: the engine
  implementation, tests, evaluators, and any external consumer are checked against
  it. If code and `rules.md` disagree, that is a bug, and `rules.md` is the
  reference.
- A **ruleset** is a mutable name (BATTLE, SKIRMISH); an **edition**
  (`<major>-<minor>:<Ruleset>`) is an immutable pairing of that name with a major
  baseline and a complete set of flag values; a **rule flag** is an enum-valued
  parameter whose default is always the behavior that predated it. The root
  [`CLAUDE.md`](../../CLAUDE.md) carries the definitions; `rules.md` says
  *variant* where this file says *flag*, for the same player-audience reason it
  says *move* where this file says *ply*.
- **Piece distribution is not an axis of an edition.** It is the resolved value
  of the `ARMY_COMPOSITION` flag, exactly like any other setting, so flags are
  the only thing an edition is made of. This was not always so — before major 2
  an edition carried a distribution alongside its flag values, which gave two
  things a claim on the army and required a rule to arbitrate between them. The
  arbitration rule is gone because the collision is.
- **The major names the baseline; flags parameterize within it.** Editions
  sharing a major are points in one flag space. Editions with different majors
  are not: a major bump republishes the rules text, so behavior can differ with
  no flag distinguishing it. Diagonal attack is baseline at major 2 and absent at
  major 1, under no flag, which is why `1-2:PRE-RELEASE` and `2-0:BATTLE` are not
  comparable by flag values despite naming the same board and army.
- **Minor is namespaced per ruleset; major is global.** `BATTLE` advancing to
  `2-1` leaves `SKIRMISH` at `2-0`. A notation break moves every live ruleset to
  the next major at once, since a major is a property of the notation and the
  baseline rather than of any one ruleset.
- The rules are also consumed by a separate front-end player application, which
  tracks the changelog to know when and how to update — a reason the edition
  registry and changelog are load-bearing, not decorative.

### What is guaranteed, and to whom

The old policy — *latest version only, nothing else supported* — is retired. It
protected nothing pre-release while making rule experimentation expensive: every
tweak spawned a near-duplicate frozen version. Two guarantees replace it, at
different strengths:

- **View-only replay is guaranteed for all records, forever.** A record can be
  read, its position block rendered, and its move sequence stepped through by
  notation-schema stability alone — no rules knowledge required. This holds for
  every record ever written, under any edition, and survives every minor bump.
- **Validated replay is guaranteed for published editions.** Confirming that each
  move in a record was *legal*, and that the outcomes it marks are the ones the
  rules produce, requires implementing that edition. That is guaranteed for
  editions published in Appendix B, which is why editions are immutable and are
  never removed from the table once published.

The second guarantee is about the *edition* staying implementable, not about any
one build implementing every edition ever published. **A build implements every
edition in the Active table, and the configuration is selected at run time.** A
training run or a game is launched against `BATTLE` or `SKIRMISH`, and every
artifact it writes is stamped with the configuration it was actually playing.

The edition table also retains the **historical** editions, so that a stamped
artifact still names something meaningful and the row it names is still there to
be read — not because the running code can play them. Validating a record written
under a historical edition therefore means checking out the build that
implemented it, and for a historical edition at an earlier *major* that build
also implemented different rules text, since `rules.md` carries only the current
major.

This is why a checkpoint stamped with a historical edition is *rejected* rather
than accepted on the strength of the table containing its id. The reason is that
the edition is **not Active** — it stopped being pointed at because the rules
changed, so a run resuming from it would train under rules its weights never saw.
It is not that a build can hold only one edition; it can hold several, and
rejects the ones it no longer plays.

The distinction is what lets rules change without breaking the front-end
application, whose contract is review, not validation.

### How a rules change lands

**Rule changes land as flags with preserving defaults**, not as edits to the core
rules text. A variant is proposed in
[`proposed-variants.md`](proposed-variants.md), implemented behind a flag whose
default is the current behavior, and graduated to `rules.md` Appendix A when its
branch merges. Because the default preserves existing behavior, adding a flag is
a no-op for every existing edition and every existing record.

This changes what a **minor bump** means: it marks *registry growth* — a new
edition pairing the ruleset with different flag values — not a semantic break.
Publishing a new edition means adding a row to Appendix B, moving the ruleset's
Active pointer to it, adding a changelog entry, and updating the set of active
editions in [`capture_the_flag/record.py`](../../capture_the_flag/record.py),
whose edition table is what stamps every record and every checkpoint. A stale
value silently mis-tags everything written after the change.

Editing the core rules text directly is still correct for a **clarification** —
better wording, a worked example, a resolved ambiguity. The test is behavioral:
if every game legal under the old wording is still legal under the new one and
resolves the same way, it is a clarification. If not, it is a rules change and
needs a flag or a new edition.

The one exception is a **major bump**, which republishes the baseline rules text
and can therefore carry a behavior change unflagged — see "What forces a major
bump" below. Diagonal attack landed this way at major 2. Do not read this as a
general escape hatch: a major bump is justified by a notation break, not by a
wish to avoid a flag, and behavior only rides one that is already happening.

#### Flags over army composition

A flag may vary anything the rules state, army composition included — and since
major 2, composition *is* a flag (`ARMY_COMPOSITION`) rather than a separate
axis. A finer-grained flag in the same territory, say `MILITIA_COUNT = 3 | 4 | 5`
defaulting to the current 3, is equally well-formed: enum-valued,
behavior-preserving by default, and testable on a branch without publishing an
edition per attempt.

Composition is the sharpest case for the checkpoint pin: the learned evaluator
normalizes its per-rank quantity features by `army_count`, so changing a count
changes what those inputs *mean* while leaving the tensor shape — and therefore
`ENGINE_SPEC_NAME` — untouched. A network trained at one composition would load
silently into another. The ruleset stamp is what refuses it.

**Board layout is sharper still.** `BOARD_LAYOUT` changes the spatial extent of
the input, so unlike a composition change it generally *does* move the tensor
shape and so is caught by `ENGINE_SPEC_NAME` as well. That makes it the one case
where the two stamps overlap — which is redundancy rather than a problem, and no
reason to lean on the spec stamp: a layout change that preserved the grid
dimensions while moving the lakes or the home-zone depth would leave the shape
untouched and needs the ruleset stamp to catch it.

**Not every flag combination is playable.** `BOARD_LAYOUT` and
`ARMY_COMPOSITION` are independent, so a configuration can name an army that does
not fit its board's home zone — `standard_battle` on `standard_64` puts 25 pieces
in 24 squares. Such a configuration is invalid for play and no published edition
uses one. This constrains playing rather than reading: a record carries the board
it was played on, and may start from a mid-game position that never had a
placement phase to be valid or invalid.

#### Diagonal attacks and lakes — a decision reserved for future layouts

`rules.md` states that a **lake corner does not block a diagonal attack**: a piece
may attack diagonally past the corner of a lake, and only the attacked square
itself must not be a lake. That case is live on both published boards — on Battle,
a piece on A6 attacking B5 passes the corner of the lake at B6.

A second case exists that `rules.md` deliberately does **not** address: a diagonal
whose **two flanking squares are both lakes**, source and destination open. Call
it the *squeeze*, as against the *skirt* above.

**The decision, recorded in advance: the squeeze is not allowed.** Lakes are
barriers, impassable by every other means, and a diagonal slipping between two of
them would sneak a piece through a wall. Permitting it because a diagonal step has
no intermediate square to clear would be a defensible rule in isolation, but it
would make the lakes' barrier property depend on the direction of travel, which is
not what a lake is for.

**Why this is not in `rules.md`.** The squeeze is **unreachable on both published
layouts**, so stating it there would burden the player-facing rules with a
hypothetical. Both flanking squares being lakes requires rows *r* and *r+1* to be
lake rows *and* columns *c* and *c+1* to be lake columns; with 2 × 2 lake blocks
all aligned to the same two rows, that forces the source and destination squares
to be lakes as well, so no legal attack can exist there. Any layout that breaks
that alignment makes it reachable — offset blocks touching corner to corner,
single-square lakes placed diagonally, or more than two lake rows.

Because no position can currently distinguish the two answers, this note changes
nothing about how either published edition is played, which is why it belongs in
this file. **When a `BOARD_LAYOUT` value that makes the squeeze reachable is first
published, this stops being true**: `rules.md` gains a sentence stating the rule,
and the changelog records it as a clarification rather than a rules change, since
this note settled it first.

### What forces a major bump

A major bump is a break in the **notation**, not in the rules — it is what the
front-end application cannot absorb, so it is worth stating exactly.

The notation marks survival on exactly the two squares of a ply (source and
destination), on a rectangular grid whose dimensions are read from the record's
position block. Within that envelope, the tape can express anything:

- any combat outcome, including new ones — who survives is marked per square;
- any piece distribution, including new ranks or symbols;
- any source→destination movement rule, however exotic the path — diagonal
  attacks needed no notation change at all;
- **any board size or lake arrangement**, up to 26 columns, which is where the
  single-letter column names run out.

None of those force a major bump. These do, because the tape has nowhere to put
them:

- **A third-square side effect** — a ply that changes a square other than its
  source and destination (an area attack, a piece pushed to a third square, a
  bystander removed).
- **A multi-piece ply** — one ply moving two pieces (castling-like, or a
  formation advancing together).
- **More than 26 columns** — the column names would need a second character, and
  every coordinate in every ply string changes width.

Any of those needs a new notation, a new major, and a coordinated front-end
change. Writing this down is what keeps a later story from breaking the
review-only contract by accident.

**Board size used to be on the second list.** Major 2 moved it to the first by
making the notation size-parametric, which is the whole reason that bump was
spent. The cost was paid once; no future layout — different dimensions, different
lakes, different home-zone depth — costs another major. What a new layout does
still cost is a **new `BOARD_LAYOUT` value**, because a layout has to be named
before a configuration can select it or an artifact can be stamped with it.

**A major bump also republishes the baseline rules text**, which is a second
thing it does and worth separating from the notation break. `rules.md` carries
one major at a time, so a behavior change can ride a major bump as baseline
rather than as a flag — diagonal attack did exactly this at major 2. That is the
*only* circumstance under which new behavior legitimately lands unflagged; absent
a major bump, "How a rules change lands" above applies without exception.

### Where a configuration is stamped

One representation serves every artifact: **an edition id plus the flags that
deviate from it**. It is written three places, in two forms.

| Artifact | Form | Purpose |
|---|---|---|
| Game record, `Ruleset` tag | rendered string | states the rules a stored game was played under |
| Checkpoint, `ruleset` key | nested mapping | pins the rules a network's weights were trained under |
| `run-config.json`, `ruleset` key | nested mapping | reproduces the rules a training run was conducted under |

The string form exists only because a record file is a text medium; everywhere
else the configuration is structured, following the precedent the architecture
stamp already set. Structure is what makes a rejection legible — "flag
`MOVABLE_TOWERS`: stamp says `on`, running code has no such flag" rather than two
opaque strings differing somewhere — and it removes any need for canonical
ordering when comparing.

**A checkpoint's stamp is a stricter statement than a compatible-rulesets list.**
Such a list is the *set* of rulesets an I/O contract can serve, many-to-one; a
checkpoint's tag is the single *point* in that set its weights actually occupy. A
network is only valid for the rules it was trained under, and the engine spec
stamp (`ENGINE_SPEC_NAME`) does not cover this — it names the tensor *shape*
contract, so a rules-only change leaves it untouched and the weights would load
cleanly into a network evaluating under rules they never saw.

On load, a checkpoint whose configuration the running code can implement is
**adopted**: a resumed run continues under the stamped configuration rather than
under current defaults, so a run trained with a flag on resumes with it on even
if the default has since changed. Adoption reaches the artifacts, not just the
decision to proceed — the checkpoints a resume appends are stamped with the
configuration it adopted, so a run's later generations are never re-tagged with
an edition they were not trained under. Rejection is reserved for a configuration
the running code cannot implement at all (which includes a *historical* edition,
per the guarantee above), and for one that is missing — an unstamped artifact
cannot say what it was trained under, and defaulting it would assert something
unknown.

A configuration is also **canonicalized when read**: a stamp that lists a flag at
the value it would resolve to anyway is normalised to one that omits it. The two
mean the same thing, but only the canonical one renders as the same string and
compares equal, and this code reads stamps it did not write.

### Known gap: nothing checks that play matches the stamp

**The stamp is asserted, not measured.** Nothing verifies that the rules the
engine actually played match the edition and flags it stamped into a record or a
checkpoint. If the engine's implementation drifts from `rules.md`, or a flag is
read in one code path and ignored in another, the artifacts will say so anyway.

One narrow part of this *is* checked: each active edition's resolved piece
distribution is asserted against the engine's roster for that edition, so the
roster cannot drift from what the edition claims. Other flag values have no
equivalent check. Note that this check became **per-edition** at major 2 — with
two active editions there is no single roster for it to compare against, and a
check that only covered one of them would leave the other unguarded.

This is accepted for now rather than closed, because closing it means building a
record *reader* — a parser and replay-validation path — which this repository
deliberately does not have: it produces records for the front-end application and
never consumes them. The natural mitigation is a corpus of kept records replayed
as regression tests, deferred to a later story.

## Terminology: "move" in the rules, "ply" everywhere else

`rules.md` is written for a non-technical player audience and uses **"move"** for a
single player's action throughout. Everywhere else in this project — code, tests,
plans, and design documents — the term is **"ply"**, per the project vocabulary in
the root `CLAUDE.md`. The two are the same concept: **one move = one ply.**
`rules.md` is the *only* document that prefers "move."

## Game notation and the record file format

The move notation in `rules.md` [Section 4.4](rules.md#44-recording-a-move) and
this file format share one coordinate frame and a common position-block
rendering. The engine emits the result-marking (extended) move form and the
from-placement record shape described below; mid-game records remain documented
as reserved for later use.

### Player colours

The first player to move is **White**; the second is **Black**, regardless of
the colour the tokens are physically rendered as (tokens are often **Red** for
White and **Blue** for Black). White and Black are the labels used in record
header tags and to identify the two sides in the position block.

### The position block

The full board, rendered from White's perspective: the highest-numbered row at
the top, row 1 at the bottom, column A at the left. Every square is a
fixed-width, 3-character cell, cells separated by a single space, one board row
per line. Because a position need not be a game start, a piece's side cannot be
inferred from which half of the board it stands on, so side is encoded explicitly
per cell:

- **White piece:** `[R]` — e.g. `[1]`, `[4]`, `[6]`, `[T]`, `[F]`
- **Black piece:** `*R*` — e.g. `*3*`, `*5*`, `*6*`, `*T*`, `*F*`
- **Empty square:** `---`
- **Lake square:** `XXX`

`R` is the piece symbol from `rules.md` [Section 2.2](rules.md#22-the-pieces):
`1`–`6` for the numbered ranks, `T` Tower, `F` Flag. The whole board — including
any empty buffer rows and the lake rows — is always shown. This is the same
string the engine's `render_position_block` produces and the library-facing
`text_board` reuses.

**The block is size-describing, not fully self-describing.** Since major 2 the
board is a rectangular grid of any size, and a reader recovers **dimensions** by
counting lines and cells, and the **lake layout** from the `XXX` cells — neither
needs to be told. What the block does *not* carry is the **home-zone row count**,
because a mid-game position does not reveal where home zones were. A viewer does
not need it: rendering and stepping a record never consults home zones. Anything
that does — placement validation, or checking whether an army fits its board —
reads it from the configuration's `BOARD_LAYOUT` value instead.

### Record file format

A record file has three sections, in order, separated by one or more blank
lines:

1. **Header tags**
2. **Position block** (the record's starting board)
3. **Move sequence**

**Header tags** use PGN tag syntax, `[Name "value"]`, one per line. The record
reuses PGN's Seven Tag Roster plus `ResultReason` and `Ruleset` tags: `Event`,
`Site`, `Date`, `Round`, `White`, `Black`, `Result`, `ResultReason`, `Ruleset`.
`Result`, `ResultReason`, and `Ruleset` are always written; the roster tags
(`Event`…`Black`) are optional/best-effort.

`Ruleset` records **which rules the game was played under**: the edition id,
followed by one `FLAG=value` token per flag deviating from that edition, space
separated — e.g. `2-0:SKIRMISH` (no deviations) or
`2-0:BATTLE MOVABLE_TOWERS=on`. Deviating flags are ordered alphabetically
by flag id, so a configuration always renders as the same string. Neither an
edition id nor a flag id or label contains a space, so the tokens split
unambiguously.

In practice both published editions render with **no deviations at all**, since
each sets `BOARD_LAYOUT` and `ARMY_COMPOSITION` explicitly and a flag at its
resolved value is omitted. A flag that exists, is authoritative, and never
appears in any artifact is a well-formed outcome under this model rather than a
sign something is wrong.

The edition id is always written in full and never abbreviated to a bare ruleset
name, which would only name a moving pointer. Flags at their resolved value are
**omitted**: an absent flag means the edition's value for it, falling back to the
flag's own default only for an edition published before the flag existed. Since
every default preserves the behavior that predated its flag, an omission can
never hide a rule the reader does not know about. `Result` uses PGN's
values: `1-0` (White wins), `0-1` (Black wins), `1/2-1/2` (draw), `*`
(ongoing/unknown). `ResultReason` is free text (e.g. `Flag Captured`,
`Inactivity`, `No Legal Move`), sourced from the terminal position's outcome
reason (`GamePosition.outcome_reason`, threaded through
`GameResult.result_reason`). `Date` uses PGN's `YYYY.MM.DD` form (`????.??.??`
when unknown).
Tag *values* are escaped as in PGN — a literal `\` is written `\\` and a
literal `"` is written `\"` — so a value containing either stays inside its
quotes; writers also collapse any newline in a value to a space, since a tag
occupies a single line.

**Position block** is exactly the format specified above: for a game started
from placement, the revealed initial position; for a mid-game record, the
resumption board.

**Move sequence**: rounds numbered from 1, each `N. WhiteMove BlackMove`,
multiple rounds one per line (or wrapped freely — parsing is
whitespace-insensitive within this section). A game ending on White's move
shows that round with only White's move.

Each move may use **either** notation form from `rules.md` Section 4.4: the
plain form (`L4L3`, source-then-destination, no separator) or the extended
result-marking form (`L4-L3`, with `x` marking a piece that did not survive).
A reader must accept both, and the two forms may even be mixed within one
file. The reference engine emits the **extended** form (rendered by
`CtfGameLogging.ply_annotation`), so a record it produces looks like:

```
20. L4-L3 H2-H1x
21. K3-K2
```

The same ending written in the plain form (equivalent, and also valid):

```
20. L4L3 H2H1
21. K3K2
```

**Mid-game records** (format-reserved, not yet implemented): a record whose
starting position has Black to move opens the move sequence with
`N... <blackmove>`. Side-to-move and the three clocks for a non-start
resumption would be carried in additional header tags (names TBD). The
current engine only produces from-placement starts (White to move, all
clocks at 0), so this is documented but unused for now.

**File conventions:** UTF-8 encoding. Files are *written* with `\n` (LF) line
endings; *readers* must accept both LF and CRLF. The header, position, and
move sections are separated by one or more blank lines.

## Intended outcomes and their priority

The intended resolution of a well-played game, in order:

1. **Flag capture** — the primary win condition.
2. **No legal moves** — an opponent with all pieces captured or all survivors boxed in.
3. **Draw** — by agreement in human play (Section 5.4), or by the inactivity counter
   (Section 5.3) in engine play.

The **inactivity counter** (Section 5.3, the 50-ply shared clock) is *not* meant
to be how a good game ends in practice. It is pressure to force resolution and a
safety bound against infinite play, not an outcome to play for.

## The inactivity counter — design

A single shared **inactivity counter** (Section 5.3) bounds the game length and
forces resolution: **50 plies with no piece captured → draw.**

The counter resets on any attack that removes a piece (a winning attack, mutual
loss, or tower destruction). Non-attacking plies increment the counter.

**Rationale:** This unified counter simplifies the endgame mechanics compared to
the prior dual-clock system, while still preventing infinite play. The threshold
is set to be extremely unlikely in normal play (50 non-capturing plies = 25 rounds
of pure maneuvering without a single engagement), making it a practical safety
bound rather than a typical game outcome. Against a genuinely evasive opponent,
the intended answer is to capture the Flag or gain board control to force
captures, not to win on the clock.

### Provisional values

The limit of **50 plies** is a first-playable starting value, expected to be tuned
once games are played. Changing it is a rules change, so under the model above it
is a natural first candidate for a flag: an enum over candidate limits, defaulting
to the current 50, which is exactly the kind of tuning that used to require a
version bump per attempt.

**Major 2 gave it two more reasons to be revisited, and deliberately acted on
neither.** The 50 was chosen for 25 pieces on 144 squares; `SKIRMISH` has 16
pieces on 64 squares with no buffer rows, so contact comes sooner and there is
far less board to maneuver on. Diagonal attack pushes the same way on both
boards, since evading a threat is no longer cheap and non-capturing sequences
should shorten. Both editions therefore carry 50 unchanged, and the value is
left alone until games have actually been watched — at which point the confound
is worth remembering: board size and the baseline change moved together.

## The Fair Play Rule (Section 7)

Deliberately left undefined in the rulebook. It is primarily a **human-vs-human**
sportsmanship backstop: the clocks bound game length mechanically, but a player who
knows they are lost can still drag things out within the clocks, and no crisp
definition of "unproductive" is worth the complexity for casual play.

For **engine play** we cannot lean on a fuzzy rule, and must keep the AI from
dithering *without* degrading its strength. The failure mode to watch (visible in
public chess engines): a repetition and its non-repeating alternative are
*value-equivalent* to the evaluator, so evaluation noise tips the choice either way
— the engine is not "trying" to repeat, it is indifferent, and will churn
2×-repetitions while still avoiding a 3×-repetition draw. The intended remedy is to
give non-progress a *tiny, strictly negative* signal so there is a gradient away
from dithering — e.g. feeding the clock counts to the nets as input features (the
phase-1 design already plans this) and/or a small shaping term — without distorting
genuine position evaluation. This is a phase-2 AI concern, recorded here so it is
not lost; it is not a rule.

## Clarifications trimmed from the rulebook

Statements removed from `rules.md` to keep it declarative, retained here:

- *No legal move (5.2):* this is rarer than it looks, since sacrificial attacks are
  always legal — any mobile piece adjacent to an enemy always has at least one
  legal move (it can sacrifice itself to clear a lane or reset the inactivity counter).
  Diagonal attacks make it rarer still: "adjacent" now covers all eight
  surrounding squares rather than four, so a boxed-in piece has twice as many
  directions in which an enemy might present a legal target. The one narrowing is
  that a piece hemmed in solely by Towers and the enemy Flag gains nothing, since
  neither may be attacked diagonally.
- *Sacrificial attacks (4.3):* typical uses are clearing a lane, freeing a
  boxed-in piece, or resetting the inactivity counter to prevent a draw.

## Rules history

- **"Unbreachable Flag" (Story 1.1)** was a win condition based on Flag enclosure
  and Sapper availability. It was removed in Story 1.2 as part of a broader
  simplification (removal of Sappers and special piece abilities). References to
  this rule in pre-1.2 design notes are obsolete.
- **Orthogonal-only attacks (major 1)** were the rule through
  `1-2:PRE-RELEASE`. Diagonal attack was added to the baseline at major 2 to make
  play more direct: under orthogonal-only attacks a threatened piece could step
  off the attacker's line and force it to spend plies re-establishing contact,
  which bled pressure out of the game. Closing the diagonal escapes also makes
  material superiority easier to convert, since a stronger piece can corner a
  weaker one. Restricting the diagonal to *attacks on movable pieces* is what
  keeps this a change to the geometry of contact rather than of maneuvering, and
  leaves the Flag's defensive perimeter — which the tower-adjacency placement
  rule was shaped around — untouched.
- **The single 12×12 board (major 1)** was the only board through
  `1-2:PRE-RELEASE`. Design notes written before major 2 treat the board
  dimensions, the lake pattern, and the 25-piece army as fixed properties of the
  game rather than as `BOARD_LAYOUT` and `ARMY_COMPOSITION` values.

## Related design background

Deeper rationale for these rules — why the piece counts, combat asymmetries, and
win conditions are shaped the way they are — lives in the offline design notes
(retained as history, not authoritative). Where those notes disagree with
`rules.md`, `rules.md` governs.

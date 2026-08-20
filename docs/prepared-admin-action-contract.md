# Prepared admin action contract

Status: structural foundation. The generic action dialog does not consume the
full review/result contract yet. Its visible integration remains gated on the
current signed-in RCON3 screenshots at 390, 768 and 1440 px.

## Problem proven in the current code

`ActionDialog.jsx` and `ActionForm.jsx` execute generic player actions directly
after form submission. They do not preserve a reviewed server/game snapshot,
do not show an explicit compatibility decision, close automatically after a
successful batch, and do not expose an audit link or a retry-failed-only path.
The dedicated squad-disband flow already implements those safeguards and is
the product reference to generalise.

The execution adapter also mutated the submitted payload in-place. That made a
future immutable review snapshot unreliable because `reason`, `message`,
`name`, VIP descriptions and administrator descriptions could change between
review, execution and audit presentation.

## Contract supplied by this milestone

Every generic player action now references one immutable action contract with:

- exact RCON and audit command;
- explicit HLL and HLL Vietnam compatibility decision;
- risk: low, medium, high or critical;
- reversibility: reversible, limited or irreversible;
- scope: current server, optional all servers, CRCON profile or blacklist;
- review fields that must be shown before execution;
- normal review or stronger second confirmation;
- per-target result and retry-failed-only requirements.

Bulk actions always escalate to the stronger confirmation path. Permanent ban,
blacklist and console-administrator assignment require it even for one target.
The existing dedicated squad-disband flow remains separate until both flows can
share the same rendered component without losing its squad-specific context.

## Compatibility matrix

| Action family | HLL | HLL Vietnam | Scope | Strong confirmation |
| --- | --- | --- | --- | --- |
| Message, watch, flags, comments | explicit | explicit | server/profile | bulk only |
| VIP add/remove | explicit | explicit | optional all servers | bulk only |
| Switch, punish, kick, squad removal | explicit | explicit | current server | bulk only |
| Temporary ban/unban | explicit | explicit | current/optional servers | bulk only |
| Permanent ban | explicit | explicit | optional all servers | always |
| Blacklist | explicit | explicit | selected blacklist | always |
| Console administrator | explicit | explicit | current server | always |

The matrix records a compatibility decision; it does not replace a real
two-game-server execution test. Any later protocol-specific exception must be
represented in the same contract and covered by HLL/HLLV fixtures.

## Automated gate

`npm run check:admin-actions` fails when:

- an action executes a command without attaching the matching contract;
- a contract is unused or missing;
- risk, reversibility, scope or confirmation values are invalid;
- HLL or HLL Vietnam compatibility is undecided;
- audit command, per-target results or retry-failed-only are missing;
- permanent ban, blacklist or console-administrator assignment lose their
  stronger confirmation;
- a multi-target action no longer escalates confirmation.

The pull-request workflow runs this gate before the browser suite. The action
adapter now copies and normalises a payload instead of mutating the reviewed
object.

## Required visible integration

The next vertical slice must consume this contract in the generic dialog and
prove the following with current before/after screenshots and deterministic
fixtures:

1. server name/number, game, CRCON state, game-server state and data age;
2. target, action, reason/message, duration/expiration, scope and reversibility;
3. a separate stronger confirmation for critical and bulk actions;
4. result and error per target, with only failed targets retried;
5. direct audit link, or a translated missing-permission explanation;
6. explicit unsupported/unknown-game and stale/offline blocking states;
7. HLL, HLL Vietnam, multiserver, limited-permission, keyboard, axe and 390 px
   verification.

This document does not authorize a merge, release, or production rollout.

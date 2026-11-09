# Report target matching: abbreviated names

Status: implemented and tested; not deployed. No moderation configuration or
existing incident outcome has been changed.

## Observed case

On RCON3 at 19:34 Europe/Berlin on October 27, 2026, the report
`!admin BLITZ_33 Sl no Voip` remained manual with `original_target_unresolved`.
The interpretation service successfully classified missing communication and
identified the reference as a player name. The actual player was `Blitz_33_1981`,
an allied helicopter logistics officer in Oscar squad.

The parser returned one fuzzy suggestion with similarity 0.7619. The independent
action resolver nevertheless counted the missing `_1981` suffix as five edits,
exceeding the full-name allowance of two for this reference. This was a local
identity-check limitation, not a model outage.

## Change

The resolver now also compares distinctive name prefixes ending at a separator.
Prefixes require at least six letters/digits and tolerate at most one edit;
full-name spelling mistakes retain the existing length-dependent allowance of
up to three edits. Arbitrary substrings and short fragments are not promoted.
The upstream parser must still supply a single suggestion.

Both full names and prefixes on both teams participate in the ambiguity check,
including competitors just outside their own acceptance budget. A runner-up
within one edit of the best match prevents automatic action. The accepted ID
must be the parser's suggested ID. Existing original/current roster, session,
team, role, evidence, administration and final execution checks remain in place.

This change is in the RCON resolver only; no central-service update is needed.
There are no migrations, new settings or permission changes.

## Verification

- A regression for `BLITZ_33` failed before the implementation and passed after it.
- All 423 report and admin-incident tests passed, covering existing full-name
  typos, communication policy, evidence, sessions and action safeguards.
- The expanded abbreviation suite passed all 28 cases, including four additional
  end-to-end typo-plus-abbreviation cases added after that broader run.
- Read-only comparison using the incident's original 98-player roster returned
  no target with the deployed resolver, and the correct original player ID and
  leadership position with the candidate resolver loaded only in an isolated
  diagnostic process. No service files were changed and no report was replayed.

The tests used mocked game actions. They do not claim that a live kick occurred.
The previously missed incident remains for manual handling.

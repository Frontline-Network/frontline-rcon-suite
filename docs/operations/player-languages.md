# Recipient language profiles and templates

The first phase routes moderation messages/reasons, Automods and Autobalancer
feedback by recipient. It adds no machine-translation request to an RCON action.
The interface is at `/settings/player-languages`, also linked from Templates.

The translation workspace shows localized rule and message names instead of
internal binding keys. Search matches the displayed name and original text;
area and translation-status filters narrow the list. Original and translation
are displayed together on desktop and stacked on smaller screens. Empty source
texts are marked unused. Player language profiles have their own tab, and new
moderation templates open in a separate dialog. Changing a template or filter
still protects unsaved translations; previews never send game commands.

## Preferences and identity

PC players use `!lang`, `!lang de`, `!lang en` or `!lang fr` (alias `!language`).
Discord's existing My language selector uses the same preference store. A Discord
choice applies to a game identity only after the existing challenge-based account
link has been verified. Console players can make that choice from Discord on a
phone. The RCON player profile also exposes language management to administrators
with the existing account-edit permission. A public Frontline purchase/account
website integration is outside this first-phase RCON interface.

The historical `voice_language_preference` and `voice_verified_identity` tables
remain authoritative: no preferences or verified links are copied or discarded.
Explicit choices beat report-language observations. If both are absent and
recipient routing is enabled, a cached public Steam country can supply a
provisional language default. The profile labels this source separately; it
does not create an explicit preference. Multilingual countries such as CH, BE
and CA use the English fallback. An unknown player defaults to English without
writing a preference row. Explicit bilingual choices remain readable and usable.
Vietnam profile refreshes query the stored Steam ID and validate the response
identity; game commands and ban lookups continue to use their existing IDs.
No Steam request occurs during message rendering. A nickname, the reporter's
language and an unverified Discord account are never attributed to a target.
EOS spelling is canonicalized; old uppercase preferences/links remain readable.

## Templates and compatibility

Existing manual Message and Reason templates remain editable in their original
editor. The central translation editor adds language variants by stable template
ID. Automation bindings point at the existing module message settings. Stock
Automod texts have reviewed DE/EN/FR variants; customized legacy text is preserved
and shown as untranslated until an administrator supplies variants. Autobalancer
uses its existing DE/EN/FR packs, including customer changes.

All translations must preserve named placeholders, conversions and formats.
Nested rule explanations use the outer message's language when a matching
translation exists. Changed source content (or changed Autobalancer language
packs) invalidates old variants for delivery and marks them for review. Previous
variants remain available to the administrator. Revision checks reject stale
editor saves. Arbitrary free text is not silently machine-translated.

Enable recipient routing explicitly after reviewing templates. The default is
off for upgrades, retaining existing module behavior. With routing enabled, a
known preference selects one variant. Unknown players and missing variants use
English where available, otherwise preserved original content. An explicitly
selected DE/EN preference still uses one combined bilingual packet.
Autobalancer sends one packet; disabled routing retains its legacy configured
pack behavior. A translation does not change an action, duration, eligibility,
round/session check, warning counter, or existing delivery reservation.

Manual single-player action forms show a recipient preview. Bulk actions resolve
the language independently at each dispatch. Message/reason text is resolved
before the existing game command; uncertain outcomes are recorded without
replaying it. The additional audit retains original text, delivered text,
language, template key and confirmed/rejected/uncertain outcome. Its profile view
loads only when opened, capped at ten records.

## Installation and validation

Apply Alembic `p261127lang01` before opening template management. It adds two
tables and case-insensitive lookup indexes; it does not rewrite existing player
data, templates, incidents, queues, or banlists. Application rollback can retain
the additive schema. Downgrade refuses to drop saved translations or audit data.
Permissions reuse template view/edit and player-profile/account-edit permissions;
changes are POST-only. Existing chat and Discord language choices remain usable.

Validate a fresh database and a populated upgrade, explicit vs detected choices,
verified vs unverified identities, EOS case variants, missing/stale translations,
placeholder rejection, permission boundaries, one Autobalancer packet, and all
moderation outcomes. Use an isolated game transport on RCON3 so no test warning,
kick or ban reaches a real player. Global welcome screens/broadcasts, campaigns,
VIP, map voting and end-match statistics remain separate follow-up integrations.

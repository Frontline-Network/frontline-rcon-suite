# CRCON Mobile Admin

Native Flutter client for per-admin CRCON pairing and incident response. The
app uses the existing Frontline visual language, defaults to German and can be
switched to English.

The context-v2 incident detail contains four operational tabs:

- report and reporter context;
- confirmed and suggested player/squad subjects;
- squad snapshot/current membership comparison;
- immutable incident timeline.

Administrative actions always require an explicitly selected confirmed player.
Kick and temporary bans additionally require a reason and confirmation. Read
data is encrypted locally; writes are never queued while offline.

## Development

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

Pair the build with a CRCON instance through **Mobile App** in the authenticated
CRCON web UI. Production builds accept only publicly reachable HTTPS URLs with
a valid certificate.

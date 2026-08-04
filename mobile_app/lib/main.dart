import 'dart:async';
import 'dart:io';
import 'dart:ui';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:share_plus/share_plus.dart';

import 'app_logger.dart';
import 'crcon_api.dart';
import 'frontline_theme.dart';
import 'live_updates.dart';
import 'models.dart';
import 'providers.dart';
import 'push_relay.dart';

final localeProvider = StateProvider<Locale>((ref) => const Locale('de'));
bool _firebaseAvailable = false;

extension FrontlineCopy on BuildContext {
  bool get isGerman => Localizations.localeOf(this).languageCode == 'de';
  String tr(String german, String english) => isGerman ? german : english;

  String incidentStatus(String value) => switch (value.toLowerCase()) {
    'new' => tr('Neu', 'New'),
    'claimed' => tr('Übernommen', 'Claimed'),
    'resolved' => tr('Erledigt', 'Resolved'),
    'dismissed' => tr('Abgewiesen', 'Dismissed'),
    _ => value,
  };

  String subjectState(String value) => switch (value.toLowerCase()) {
    'suggested' => tr('Vorschlag', 'Suggested'),
    'confirmed' => tr('Bestätigt', 'Confirmed'),
    'rejected' => tr('Verworfen', 'Rejected'),
    _ => value,
  };

  String teamName(String? value) => switch (value?.toLowerCase()) {
    'allies' || 'allied' => tr('Alliierte', 'Allies'),
    'axis' => tr('Achsenmächte', 'Axis'),
    _ => value ?? '—',
  };

  String squadTypeName(String? value) =>
      switch (value?.replaceAll(RegExp(r'[_ -]'), '').toLowerCase()) {
        'infantry' => tr('Infanterie', 'Infantry'),
        'recon' => tr('Aufklärung', 'Recon'),
        'armor' || 'armour' => tr('Panzer', 'Armor'),
        'commander' => tr('Kommandant', 'Commander'),
        'artillery' => tr('Artillerie', 'Artillery'),
        'squad' => tr('Squad', 'Squad'),
        _ => value ?? tr('Squad', 'Squad'),
      };

  String squadName(String? value) {
    final squad = value?.trim();
    if (squad == null || squad.isEmpty) return '—';
    return RegExp(r'^[a-z]+$').hasMatch(squad)
        ? '${squad[0].toUpperCase()}${squad.substring(1)}'
        : squad;
  }

  String roleName(String? value) =>
      switch (value?.replaceAll(RegExp(r'[_ -]'), '').toLowerCase()) {
        'officer' => tr('Squadleader', 'Squad leader'),
        'tankcommander' => tr('Panzerkommandant', 'Tank commander'),
        'spotter' => tr('Späher', 'Spotter'),
        'commander' => tr('Kommandant', 'Commander'),
        'rifleman' => tr('Schütze', 'Rifleman'),
        'assault' => tr('Sturmtrupp', 'Assault'),
        'automaticrifleman' => tr('MG-Schütze', 'Automatic rifleman'),
        'machinegunner' => tr('MG-Schütze', 'Machine gunner'),
        'medic' => tr('Sanitäter', 'Medic'),
        'support' => tr('Unterstützung', 'Support'),
        'engineer' => tr('Pionier', 'Engineer'),
        'antitank' => tr('Panzerabwehr', 'Anti-tank'),
        'crewman' => tr('Panzerbesatzung', 'Crewman'),
        _ => value ?? '—',
      };
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppLogger.instance.initialize();
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    AppLogger.instance.error(
      'flutter',
      details.exception,
      message: details.context?.toDescription(),
      stackTrace: details.stack,
    );
  };
  PlatformDispatcher.instance.onError = (error, stackTrace) {
    AppLogger.instance.error(
      'platform',
      error,
      message: 'Unhandled asynchronous error',
      stackTrace: stackTrace,
    );
    return false;
  };
  AppLogger.instance.info('app', 'Application started');
  if (PushRelay.baseUrl.isNotEmpty) {
    try {
      await Firebase.initializeApp();
      await FirebaseMessaging.instance.requestPermission();
      _firebaseAvailable = true;
    } catch (error) {
      AppLogger.instance.warning(
        'push',
        'Push relay is configured but Firebase could not start',
        error: error,
      );
    }
  } else {
    AppLogger.instance.info(
      'push',
      'Push is disabled for this build; no relay URL is configured',
    );
  }
  runApp(const ProviderScope(child: CrconMobileApp()));
}

final _router = GoRouter(
  initialLocation: '/inbox',
  routes: [
    GoRoute(path: '/connections', builder: (_, _) => const ConnectionsScreen()),
    GoRoute(path: '/pair', builder: (_, _) => const PairingScreen()),
    GoRoute(path: '/inbox', builder: (_, _) => const InboxScreen()),
    GoRoute(path: '/players', builder: (_, _) => const PlayerSearchScreen()),
    GoRoute(path: '/diagnostics', builder: (_, _) => const DiagnosticsScreen()),
    GoRoute(
      path: '/players/:connectionId/:playerId',
      builder: (_, state) => PlayerProfileScreen(
        connectionId: state.pathParameters['connectionId']!,
        playerId: state.pathParameters['playerId']!,
        serverNumber: int.tryParse(
          state.uri.queryParameters['server_number'] ?? '',
        ),
      ),
    ),
    GoRoute(
      path: '/squads/:connectionId/:serverNumber/:team/:squad',
      builder: (_, state) => SquadScreen(
        connectionId: state.pathParameters['connectionId']!,
        serverNumber: int.parse(state.pathParameters['serverNumber']!),
        team: state.pathParameters['team']!,
        squadName: state.pathParameters['squad']!,
      ),
    ),
    GoRoute(
      path: '/incidents/:connectionId/:incidentId',
      builder: (_, state) => IncidentScreen(
        connectionId: state.pathParameters['connectionId']!,
        incidentId: state.pathParameters['incidentId']!,
      ),
    ),
  ],
);

class CrconMobileApp extends ConsumerStatefulWidget {
  const CrconMobileApp({super.key});

  @override
  ConsumerState<CrconMobileApp> createState() => _CrconMobileAppState();
}

class _CrconMobileAppState extends ConsumerState<CrconMobileApp> {
  StreamSubscription<RemoteMessage>? _foregroundMessages;
  StreamSubscription<RemoteMessage>? _openedMessages;
  StreamSubscription<String>? _tokenChanges;
  final Map<String, CrconLiveUpdates> _liveConnections = {};

  @override
  void initState() {
    super.initState();
    unawaited(_restoreLanguage());
    if (!_firebaseAvailable) return;
    try {
      _foregroundMessages = FirebaseMessaging.onMessage.listen(_openIncident);
      _openedMessages = FirebaseMessaging.onMessageOpenedApp.listen(
        _openIncident,
      );
      unawaited(
        FirebaseMessaging.instance.getInitialMessage().then((message) {
          if (message != null && mounted) _openIncident(message);
        }),
      );
      _tokenChanges = FirebaseMessaging.instance.onTokenRefresh.listen(
        (_) => _rotatePushIdentity(),
      );
      unawaited(_rotatePushIdentity());
    } catch (error) {
      AppLogger.instance.warning(
        'push',
        'Firebase listeners are unavailable',
        error: error,
      );
      // No-op in self-hosted builds without Firebase configuration.
    }
  }

  Future<void> _restoreLanguage() async {
    final language = await ref.read(secureStoreProvider).readLanguage();
    if (!mounted || language == null) return;
    ref.read(localeProvider.notifier).state = Locale(language);
  }

  Future<void> _rotatePushIdentity() async {
    try {
      final identity = await PushRelay.register();
      if (identity == null) return;
      final profiles = await ref.read(connectionsProvider.future);
      for (final profile in profiles) {
        try {
          await CrconApi(
            profile,
            ref.read(secureStoreProvider),
          ).updatePushIdentity(identity.handle, identity.capability);
        } catch (error) {
          AppLogger.instance.warning(
            'push',
            'Could not update push identity for ${profile.baseUrl}',
            error: error,
          );
          // One unavailable CRCON connection must not block the others.
        }
      }
    } catch (error) {
      AppLogger.instance.warning(
        'push',
        'Push identity rotation failed',
        error: error,
      );
      // Push remains optional; no write is queued for a later automatic retry.
    }
  }

  void _openIncident(RemoteMessage message) {
    final connectionId = message.data['connection_key'];
    final incidentId = message.data['incident_id'];
    if (connectionId != null && incidentId != null) {
      ref.invalidate(inboxProvider);
      _router.go('/incidents/$connectionId/$incidentId');
    }
  }

  void _syncLiveConnections(List<ConnectionProfile> profiles) {
    final activeIds = profiles.map((profile) => profile.id).toSet();
    for (final id in _liveConnections.keys.toList()) {
      if (!activeIds.contains(id)) {
        unawaited(_liveConnections.remove(id)?.dispose());
      }
    }
    for (final profile in profiles) {
      if (_liveConnections.containsKey(profile.id)) continue;
      final live = CrconLiveUpdates(profile, ref.read(secureStoreProvider));
      _liveConnections[profile.id] = live;
      unawaited(
        live.start((incident) {
          if (!mounted) return;
          ref.read(liveIncidentUpdateProvider.notifier).state =
              LiveIncidentUpdate(connectionId: profile.id, incident: incident);
          ref.invalidate(inboxProvider);
        }),
      );
    }
  }

  @override
  void dispose() {
    _foregroundMessages?.cancel();
    _openedMessages?.cancel();
    _tokenChanges?.cancel();
    for (final live in _liveConnections.values) {
      unawaited(live.dispose());
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(connectionsProvider, (_, next) {
      next.whenData(_syncLiveConnections);
    });
    final locale = ref.watch(localeProvider);
    return MaterialApp.router(
      title: 'Frontline CRCON Admin',
      debugShowCheckedModeBanner: false,
      locale: locale,
      supportedLocales: const [Locale('de'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ],
      theme: FrontlineTheme.dark,
      routerConfig: _router,
    );
  }
}

class _LanguageButton extends ConsumerWidget {
  const _LanguageButton();

  @override
  Widget build(BuildContext context, WidgetRef ref) => PopupMenuButton<String>(
    tooltip: context.tr('Sprache', 'Language'),
    icon: const Icon(Icons.language),
    initialValue: ref.watch(localeProvider).languageCode,
    onSelected: (language) {
      // Let the popup route finish its teardown before replacing Localizations.
      // Rebuilding the inherited locale while the popup still had dependents
      // caused `_dependents.isEmpty` assertions on Android debug builds.
      unawaited(
        Future<void>.delayed(kThemeAnimationDuration, () {
          ref.read(localeProvider.notifier).state = Locale(language);
          return ref.read(secureStoreProvider).writeLanguage(language);
        }),
      );
    },
    itemBuilder: (_) => const [
      PopupMenuItem(value: 'de', child: Text('Deutsch')),
      PopupMenuItem(value: 'en', child: Text('English')),
    ],
  );
}

class DiagnosticsScreen extends StatelessWidget {
  const DiagnosticsScreen({super.key});

  Future<void> _copy(BuildContext context) async {
    await Clipboard.setData(
      ClipboardData(text: AppLogger.instance.exportText()),
    );
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            context.tr('Diagnoseprotokoll kopiert.', 'Diagnostics log copied.'),
          ),
        ),
      );
    }
  }

  Future<void> _share(BuildContext context) async {
    try {
      await SharePlus.instance.share(
        ShareParams(
          subject: 'Frontline CRCON Admin diagnostics',
          text: AppLogger.instance.exportText(),
        ),
      );
    } catch (error, stackTrace) {
      AppLogger.instance.error(
        'diagnostics',
        error,
        message: 'Sharing the diagnostics failed',
        stackTrace: stackTrace,
      );
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    }
  }

  Future<void> _clear(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(context.tr('Protokoll löschen?', 'Clear diagnostics?')),
        content: Text(
          context.tr(
            'Alle lokal gespeicherten Diagnoseeinträge werden entfernt.',
            'All locally stored diagnostic entries will be removed.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: Text(context.tr('Abbrechen', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(context.tr('Löschen', 'Clear')),
          ),
        ],
      ),
    );
    if (confirmed == true) await AppLogger.instance.clear();
  }

  Color _levelColor(AppLogLevel level) => switch (level) {
    AppLogLevel.info => FrontlineTheme.muted,
    AppLogLevel.warning => FrontlineTheme.warning,
    AppLogLevel.error => const Color(0xffe06f65),
  };

  IconData _levelIcon(AppLogLevel level) => switch (level) {
    AppLogLevel.info => Icons.info_outline,
    AppLogLevel.warning => Icons.warning_amber_outlined,
    AppLogLevel.error => Icons.error_outline,
  };

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(context.tr('Diagnoseprotokoll', 'Diagnostics log')),
      actions: [
        IconButton(
          tooltip: context.tr('Kopieren', 'Copy'),
          onPressed: () => _copy(context),
          icon: const Icon(Icons.copy_outlined),
        ),
        IconButton(
          tooltip: context.tr('Teilen', 'Share'),
          onPressed: () => _share(context),
          icon: const Icon(Icons.share_outlined),
        ),
        IconButton(
          tooltip: context.tr('Löschen', 'Clear'),
          onPressed: () => _clear(context),
          icon: const Icon(Icons.delete_outline),
        ),
      ],
    ),
    body: AnimatedBuilder(
      animation: AppLogger.instance.revision,
      builder: (context, _) {
        final entries = AppLogger.instance.entries;
        return Column(
          children: [
            Container(
              width: double.infinity,
              color: FrontlineTheme.surfaceHigh,
              padding: const EdgeInsets.all(12),
              child: Text(
                context.tr(
                  'Enthält lokale App-, Netzwerk- und Fehlerereignisse. Zugangsdaten und Pairing-Geheimnisse werden automatisch geschwärzt.',
                  'Contains local app, network and error events. Credentials and pairing secrets are automatically redacted.',
                ),
                style: const TextStyle(color: FrontlineTheme.muted),
              ),
            ),
            Expanded(
              child: entries.isEmpty
                  ? Center(
                      child: Text(
                        context.tr(
                          'Noch keine Diagnoseeinträge.',
                          'No diagnostic entries yet.',
                        ),
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.all(12),
                      itemCount: entries.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 6),
                      itemBuilder: (context, index) {
                        final entry = entries[index];
                        final time = TimeOfDay.fromDateTime(
                          entry.timestamp.toLocal(),
                        ).format(context);
                        return Card(
                          child: ExpansionTile(
                            leading: Icon(
                              _levelIcon(entry.level),
                              color: _levelColor(entry.level),
                            ),
                            title: Text(
                              entry.message,
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                            ),
                            subtitle: Text('$time · ${entry.category}'),
                            children: [
                              Padding(
                                padding: const EdgeInsets.fromLTRB(
                                  16,
                                  0,
                                  16,
                                  16,
                                ),
                                child: SelectableText(entry.formatted),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
          ],
        );
      },
    ),
  );
}

class ConnectionsScreen extends ConsumerWidget {
  const ConnectionsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profiles = ref.watch(connectionsProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('CRCON connections'),
        actions: [
          IconButton(
            tooltip: context.tr('Diagnoseprotokoll', 'Diagnostics log'),
            onPressed: () => context.push('/diagnostics'),
            icon: const Icon(Icons.bug_report_outlined),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/pair'),
        icon: const Icon(Icons.qr_code_scanner),
        label: const Text('Pair CRCON'),
      ),
      body: profiles.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorView(message: error.toString()),
        data: (items) => items.isEmpty
            ? const Center(child: Text('Pair your first CRCON installation.'))
            : ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: items.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (context, index) {
                  final item = items[index];
                  return _ConnectionCard(profile: item);
                },
              ),
      ),
    );
  }
}

class _ConnectionCard extends ConsumerStatefulWidget {
  const _ConnectionCard({required this.profile});
  final ConnectionProfile profile;

  @override
  ConsumerState<_ConnectionCard> createState() => _ConnectionCardState();
}

class _ConnectionCardState extends ConsumerState<_ConnectionCard> {
  bool? _notifications;
  bool _busy = false;

  CrconApi get _api => CrconApi(widget.profile, ref.read(secureStoreProvider));

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final bootstrap = await _api.bootstrap();
      final device = Map<String, dynamic>.from(bootstrap['device'] as Map);
      if (mounted) {
        setState(
          () => _notifications = device['notifications_enabled'] == true,
        );
      }
    } catch (_) {
      // The connection card remains usable for local removal while offline.
    }
  }

  Future<void> _setNotifications(bool enabled) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await _api.updateNotifications(enabled);
      if (mounted) setState(() => _notifications = enabled);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _remove() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Revoke this device?'),
        content: const Text(
          'CRCON will invalidate its access and refresh tokens immediately.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Revoke'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busy = true);
    try {
      await _api.revokeDevice();
      await (await ref.read(
        cacheProvider.future,
      )).deleteConnection(widget.profile.id);
      await ref.read(secureStoreProvider).removeConnection(widget.profile.id);
      ref.invalidate(connectionsProvider);
      ref.invalidate(inboxProvider);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Card(
    child: Column(
      children: [
        ListTile(
          leading: const Icon(Icons.dns),
          title: Text(widget.profile.name),
          subtitle: Text(
            '${widget.profile.username} · ${widget.profile.baseUrl}',
          ),
          trailing: IconButton(
            icon: const Icon(Icons.delete_outline),
            onPressed: _busy ? null : _remove,
          ),
        ),
        if (_notifications != null)
          SwitchListTile(
            title: const Text('Incident notifications'),
            value: _notifications!,
            onChanged: _busy ? null : _setNotifications,
          ),
      ],
    ),
  );
}

class PairingScreen extends ConsumerStatefulWidget {
  const PairingScreen({super.key});
  @override
  ConsumerState<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends ConsumerState<PairingScreen> {
  bool _busy = false;
  String? _error;
  PairingSession? _session;
  Timer? _poller;

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }

  Future<void> _scan(String raw) async {
    if (_busy || _session != null) return;
    setState(() => _busy = true);
    try {
      final payload = PairingPayload.parse(raw);
      PushRelayIdentity? relayIdentity;
      try {
        relayIdentity = await PushRelay.register();
        if (relayIdentity != null) {
          final profiles = await ref.read(connectionsProvider.future);
          for (final profile in profiles) {
            try {
              await CrconApi(
                profile,
                ref.read(secureStoreProvider),
              ).updatePushIdentity(
                relayIdentity.handle,
                relayIdentity.capability,
              );
            } catch (_) {
              // Existing offline installations can be refreshed manually later.
            }
          }
        }
      } catch (_) {
        // Pairing still works when push is unavailable.
      }
      final session = await CrconApi.scanPairing(
        payload,
        deviceName: Platform.localHostname.isEmpty
            ? 'CRCON phone'
            : Platform.localHostname,
        platform: Platform.isIOS ? 'ios' : 'android',
        pushHandle: relayIdentity?.handle ?? '',
        pushCapability: relayIdentity?.capability ?? '',
      );
      setState(() => _session = session);
      _poller = Timer.periodic(const Duration(seconds: 1), (_) => _exchange());
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _exchange() async {
    final session = _session;
    if (session == null || _busy) return;
    try {
      final profile = await CrconApi.exchangePairing(
        session,
        ref.read(secureStoreProvider),
      );
      if (profile == null || !mounted) return;
      _poller?.cancel();
      ref.invalidate(connectionsProvider);
      ref.invalidate(inboxProvider);
      context.go('/inbox');
    } on CrconApiException catch (error) {
      if (error.statusCode != 202 && mounted) {
        _poller?.cancel();
        setState(() => _error = error.message);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Pair CRCON')),
    body: _session == null
        ? Stack(
            children: [
              MobileScanner(
                onDetect: (capture) {
                  final value = capture.barcodes.firstOrNull?.rawValue;
                  if (value != null) _scan(value);
                },
              ),
              Align(
                alignment: Alignment.bottomCenter,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  color: Colors.black87,
                  child: Text(
                    _error ??
                        'Open Mobile App in CRCON, create a QR code, then scan it here.',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ],
          )
        : Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.phonelink_lock, size: 64),
                  const SizedBox(height: 20),
                  const Text('Compare this code with CRCON'),
                  const SizedBox(height: 12),
                  Text(
                    _session!.verificationCode,
                    style: Theme.of(
                      context,
                    ).textTheme.displayMedium?.copyWith(letterSpacing: 8),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Approve the phone in the CRCON browser to finish pairing.',
                  ),
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 16),
                      child: Text(
                        _error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
  );
}

class ManualIncidentDialog extends StatefulWidget {
  const ManualIncidentDialog({
    super.key,
    required this.profiles,
    required this.servers,
  });

  final List<ConnectionProfile> profiles;
  final Map<String, List<Map<String, dynamic>>> servers;

  @override
  State<ManualIncidentDialog> createState() => _ManualIncidentDialogState();
}

class _ManualIncidentDialogState extends State<ManualIncidentDialog> {
  final _reason = TextEditingController();
  late String _connectionId;
  late int _serverNumber;

  @override
  void initState() {
    super.initState();
    _connectionId = widget.profiles.first.id;
    _serverNumber = _firstServerNumber(_connectionId);
  }

  int _firstServerNumber(String connectionId) =>
      (widget.servers[connectionId]?.firstOrNull?['server_number'] as num?)
          ?.toInt() ??
      1;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final serverItems = widget.servers[_connectionId] ?? const [];
    return AlertDialog(
      scrollable: true,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      title: Text(context.tr('Vorfall erstellen', 'Create incident')),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              initialValue: _connectionId,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'CRCON'),
              items: widget.profiles
                  .map(
                    (profile) => DropdownMenuItem(
                      value: profile.id,
                      child: Text(
                        profile.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (value) {
                if (value == null) return;
                setState(() {
                  _connectionId = value;
                  _serverNumber = _firstServerNumber(value);
                });
              },
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<int>(
              key: ValueKey(_connectionId),
              initialValue: _serverNumber,
              isExpanded: true,
              decoration: InputDecoration(
                labelText: context.tr('Gameserver', 'Game server'),
              ),
              items: serverItems
                  .map(
                    (server) => DropdownMenuItem(
                      value: (server['server_number'] as num).toInt(),
                      child: Text(
                        server['name']?.toString() ??
                            'Server ${server['server_number']}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (value) {
                if (value != null) _serverNumber = value;
              },
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _reason,
              autofocus: true,
              minLines: 2,
              maxLines: 3,
              textInputAction: TextInputAction.done,
              decoration: InputDecoration(
                labelText: context.tr('Grund', 'Reason'),
              ),
              onChanged: (_) => setState(() {}),
              onSubmitted: (_) => _submit(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(context.tr('Abbrechen', 'Cancel')),
        ),
        FilledButton(
          onPressed: _reason.text.trim().isEmpty ? null : _submit,
          child: Text(context.tr('Erstellen', 'Create')),
        ),
      ],
    );
  }

  void _submit() {
    final reason = _reason.text.trim();
    if (reason.isEmpty) return;
    Navigator.pop(context, {
      'connection_id': _connectionId,
      'server_number': _serverNumber,
      'reason': reason,
    });
  }
}

Future<void> _createManualIncident(BuildContext context, WidgetRef ref) async {
  final profiles = await ref.read(connectionsProvider.future);
  if (!context.mounted) return;
  if (profiles.isEmpty) {
    context.push('/pair');
    return;
  }
  final servers = <String, List<Map<String, dynamic>>>{};
  try {
    for (final profile in profiles) {
      final bootstrap = await CrconApi(
        profile,
        ref.read(secureStoreProvider),
      ).bootstrap();
      servers[profile.id] = (bootstrap['servers'] as List<dynamic>? ?? const [])
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList();
    }
  } catch (error) {
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(error.toString())));
    }
    return;
  }
  if (!context.mounted) return;
  final submission = await showDialog<Map<String, dynamic>>(
    context: context,
    builder: (_) => ManualIncidentDialog(profiles: profiles, servers: servers),
  );
  if (submission == null || !context.mounted) return;
  try {
    final profile = profiles.firstWhere(
      (item) => item.id == submission['connection_id'],
    );
    final incident = await CrconApi(profile, ref.read(secureStoreProvider))
        .createIncident(
          serverNumber: submission['server_number'] as int,
          reason: submission['reason'] as String,
        );
    ref.invalidate(inboxProvider);
    if (context.mounted) {
      context.push('/incidents/${profile.id}/${incident['id']}');
    }
  } catch (error) {
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(error.toString())));
    }
  }
}

class InboxScreen extends ConsumerWidget {
  const InboxScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final inbox = ref.watch(inboxProvider);
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _createManualIncident(context, ref),
        icon: const Icon(Icons.add_alert),
        label: Text(context.tr('Neuer Vorfall', 'New incident')),
      ),
      appBar: AppBar(
        title: Text(context.tr('Vorfall-Inbox', 'Incident inbox')),
        actions: [
          const _LanguageButton(),
          IconButton(
            onPressed: () => ref.invalidate(inboxProvider),
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            onPressed: () => context.push('/players'),
            icon: const Icon(Icons.person_search),
          ),
          IconButton(
            onPressed: () => context.push('/connections'),
            icon: const Icon(Icons.dns),
          ),
          IconButton(
            tooltip: context.tr('Diagnoseprotokoll', 'Diagnostics log'),
            onPressed: () => context.push('/diagnostics'),
            icon: const Icon(Icons.bug_report_outlined),
          ),
        ],
      ),
      body: inbox.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorView(message: error.toString()),
        data: (items) => RefreshIndicator(
          onRefresh: () async => ref.refresh(inboxProvider.future),
          child: items.isEmpty
              ? ListView(
                  children: [
                    const SizedBox(height: 220),
                    Center(
                      child: Text(
                        context.tr('Keine Vorfälle.', 'No incidents.'),
                      ),
                    ),
                  ],
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final item = items[index];
                    final primary = item.primarySubject;
                    return Card(
                      child: InkWell(
                        onTap: () => context.push(
                          '/incidents/${item.connectionId}/${item.id}',
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(
                                    item.status == 'new'
                                        ? Icons.notification_important
                                        : Icons.assignment_ind,
                                    color: item.status == 'new'
                                        ? FrontlineTheme.warning
                                        : null,
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      item.reason,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: Theme.of(
                                        context,
                                      ).textTheme.titleMedium,
                                    ),
                                  ),
                                  if (item.stale)
                                    const Icon(Icons.cloud_off, size: 18)
                                  else
                                    Text(context.incidentStatus(item.status)),
                                ],
                              ),
                              const SizedBox(height: 10),
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: [
                                  Chip(
                                    label: Text('Server ${item.serverNumber}'),
                                  ),
                                  Chip(
                                    avatar: Icon(
                                      primary?.kind == 'squad'
                                          ? Icons.groups_2
                                          : primary == null
                                          ? Icons.support_agent
                                          : Icons.person,
                                      size: 17,
                                    ),
                                    label: Text(
                                      primary?.kind == 'squad'
                                          ? context.squadName(
                                              primary?.squadName ??
                                                  primary?.displayName,
                                            )
                                          : primary?.displayName ??
                                                context.tr(
                                                  'Allgemein',
                                                  'General',
                                                ),
                                    ),
                                  ),
                                  if (primary?.team != null)
                                    Chip(
                                      label: Text(
                                        context.teamName(primary!.team),
                                      ),
                                    ),
                                  if (primary?.squadName != null)
                                    Chip(
                                      label: Text(
                                        context.squadName(primary!.squadName),
                                      ),
                                    ),
                                  if (item.subjects.length > 1)
                                    Chip(
                                      label: Text(
                                        '+${item.subjects.length - 1}',
                                      ),
                                    ),
                                  if (item.suggestedCount > 0)
                                    Chip(
                                      avatar: const Icon(
                                        Icons.help_outline,
                                        color: FrontlineTheme.warning,
                                        size: 17,
                                      ),
                                      label: Text('${item.suggestedCount}'),
                                    ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                '${item.reporterName ?? context.tr('manuell', 'manual')}'
                                '${item.assignedTo == null ? '' : ' · ${item.assignedTo}'}',
                                style: const TextStyle(
                                  color: FrontlineTheme.muted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ),
    );
  }
}

class PlayerSearchScreen extends ConsumerStatefulWidget {
  const PlayerSearchScreen({super.key});

  @override
  ConsumerState<PlayerSearchScreen> createState() => _PlayerSearchScreenState();
}

class _PlayerSearchScreenState extends ConsumerState<PlayerSearchScreen> {
  final _query = TextEditingController();
  String? _connectionId;
  int? _serverNumber;
  List<Map<String, dynamic>> _results = const [];
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  Future<void> _search(List<ConnectionProfile> profiles) async {
    final term = _query.text.trim();
    if (term.isEmpty || _busy || profiles.isEmpty) return;
    final profile = profiles.firstWhere(
      (item) => item.id == (_connectionId ?? profiles.first.id),
    );
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = CrconApi(profile, ref.read(secureStoreProvider));
      final bootstrap = await api.bootstrap();
      _serverNumber ??= (bootstrap['server_number'] as num).toInt();
      final results = await api.searchPlayers(
        term,
        serverNumber: _serverNumber,
      );
      if (mounted) setState(() => _results = results);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final profiles = ref.watch(connectionsProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('Spielersuche', 'Player search')),
        actions: const [_LanguageButton()],
      ),
      body: profiles.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorView(message: error.toString()),
        data: (items) {
          if (items.isEmpty) {
            return Center(
              child: Text(
                context.tr(
                  'Verbinde zuerst eine CRCON-Installation.',
                  'Pair a CRCON connection first.',
                ),
              ),
            );
          }
          _connectionId ??= items.first.id;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              DropdownButtonFormField<String>(
                initialValue: _connectionId,
                decoration: InputDecoration(
                  labelText: context.tr('CRCON-Verbindung', 'CRCON connection'),
                ),
                items: items
                    .map(
                      (item) => DropdownMenuItem(
                        value: item.id,
                        child: Text(item.name),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setState(() {
                  _connectionId = value;
                  _serverNumber = null;
                }),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _query,
                decoration: InputDecoration(
                  labelText: context.tr(
                    'Name oder Spieler-ID',
                    'Name or player ID',
                  ),
                  suffixIcon: IconButton(
                    onPressed: () => _search(items),
                    icon: const Icon(Icons.search),
                  ),
                ),
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _search(items),
              ),
              if (_busy) const LinearProgressIndicator(),
              if (_error != null) _ErrorView(message: _error!),
              ..._results.map((player) {
                final playerId = player['player_id']?.toString() ?? '';
                return ListTile(
                  leading: const Icon(Icons.person),
                  title: Text(
                    player['player_name']?.toString() ??
                        player['name']?.toString() ??
                        context.tr('Unbekannt', 'Unknown'),
                  ),
                  subtitle: Text(
                    [
                      playerId,
                      player['online'] == true
                          ? context.tr('online', 'online')
                          : context.tr('historisch', 'history'),
                      context.teamName(player['team']?.toString()),
                      player['unit_name']?.toString(),
                    ].whereType<String>().join(' · '),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: playerId.isEmpty
                      ? null
                      : () => context.push(
                          '/players/$_connectionId/$playerId'
                          '?server_number=${_serverNumber ?? ''}',
                        ),
                );
              }),
            ],
          );
        },
      ),
    );
  }
}

class PlayerProfileScreen extends ConsumerWidget {
  const PlayerProfileScreen({
    super.key,
    required this.connectionId,
    required this.playerId,
    this.serverNumber,
  });

  final String connectionId;
  final String playerId;
  final int? serverNumber;

  Future<Map<String, dynamic>> _load(WidgetRef ref) async {
    final profiles = await ref.read(connectionsProvider.future);
    final profile = profiles.firstWhere((item) => item.id == connectionId);
    return CrconApi(
      profile,
      ref.read(secureStoreProvider),
    ).playerProfile(playerId, serverNumber: serverNumber);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    appBar: AppBar(title: Text(context.tr('Spielerprofil', 'Player profile'))),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _load(ref),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return _ErrorView(message: snapshot.error.toString());
        }
        final dossier = snapshot.data!;
        final profile = Map<String, dynamic>.from(
          dossier['history'] as Map? ?? const {},
        );
        final capabilities = Map<String, dynamic>.from(
          dossier['capabilities'] as Map? ?? const {},
        );
        final bans = profile['bans'] as List<dynamic>? ?? const [];
        final comments = profile['comments'] as List<dynamic>? ?? const [];
        final sessions = profile['sessions'] as List<dynamic>? ?? const [];
        final aliases = profile['aliases'] as List<dynamic>? ?? const [];
        final live = dossier['live'] == null
            ? null
            : Map<String, dynamic>.from(dossier['live'] as Map);
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              profile['player_name']?.toString() ??
                  profile['name']?.toString() ??
                  live?['name']?.toString() ??
                  context.tr('Unbekannter Spieler', 'Unknown player'),
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            SelectableText(dossier['player_id']?.toString() ?? playerId),
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: Icon(
                  live == null ? Icons.cloud_off : Icons.circle,
                  color: live == null ? null : FrontlineTheme.success,
                ),
                title: Text(
                  live == null
                      ? context.tr('Offline', 'Offline')
                      : context.tr('Jetzt online', 'Online now'),
                ),
                subtitle: live == null
                    ? null
                    : Text(
                        [
                              context.teamName(live['team']?.toString()),
                              live['unit_name']?.toString(),
                              context.roleName(live['role']?.toString()),
                              if (live['level'] != null) 'Lvl ${live['level']}',
                            ]
                            .whereType<String>()
                            .where((value) => value.isNotEmpty)
                            .join(' · '),
                      ),
              ),
            ),
            if (live != null) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _MetricChip(label: 'K', value: live['kills']),
                  _MetricChip(label: 'D', value: live['deaths']),
                  _MetricChip(label: 'TK', value: live['teamkills']),
                  _MetricChip(label: 'Combat', value: live['combat']),
                  _MetricChip(label: 'Support', value: live['support']),
                ],
              ),
            ],
            const Divider(height: 28),
            Text(
              context.tr('Admin-Übersicht', 'Admin overview'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            _ProfileCount(
              label: context.tr('Sitzungen', 'Sessions'),
              count: sessions.length,
            ),
            _ProfileCount(
              label: context.tr('Aliasse', 'Aliases'),
              count: aliases.length,
            ),
            if (capabilities['bans'] == true)
              _ProfileCount(
                label: context.tr('Sperren', 'Bans'),
                count: bans.length,
              ),
            if (capabilities['comments'] == true)
              _ProfileCount(
                label: context.tr('Admin-Kommentare', 'Admin comments'),
                count: comments.length,
              ),
            if (profile['flags'] is List)
              _ProfileCount(
                label: context.tr('Markierungen', 'Flags'),
                count: (profile['flags'] as List).length,
              ),
            if (comments.isNotEmpty) ...[
              const Divider(height: 32),
              Text(
                context.tr('Letzte Kommentare', 'Recent comments'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              ...comments
                  .take(20)
                  .map(
                    (comment) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.comment_outlined),
                      title: Text(
                        _commentText(comment).isEmpty
                            ? context.tr(
                                'Kein Kommentartext',
                                'No comment text',
                              )
                            : _commentText(comment),
                      ),
                      subtitle: _commentMeta(comment).isEmpty
                          ? null
                          : Text(_commentMeta(comment)),
                    ),
                  ),
            ],
          ],
        );
      },
    ),
  );
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label, required this.value});
  final String label;
  final Object? value;

  @override
  Widget build(BuildContext context) => Chip(
    label: Text('$label ${value ?? '—'}'),
    side: BorderSide(color: Theme.of(context).colorScheme.outline),
  );
}

String _commentText(Object? value) {
  if (value is! Map) return value?.toString().trim() ?? '';
  final comment = Map<String, dynamic>.from(value);
  return (comment['content'] ?? comment['comment'] ?? comment['message'] ?? '')
      .toString()
      .trim();
}

String _commentMeta(Object? value) {
  if (value is! Map) return '';
  final comment = Map<String, dynamic>.from(value);
  final author = (comment['by'] ?? comment['author'] ?? '').toString().trim();
  final rawTime = (comment['creation_time'] ?? comment['created_at'] ?? '')
      .toString()
      .trim();
  final timestamp = DateTime.tryParse(rawTime)?.toLocal();
  final formattedTime = timestamp == null
      ? rawTime
      : '${timestamp.day.toString().padLeft(2, '0')}.'
            '${timestamp.month.toString().padLeft(2, '0')}.'
            '${timestamp.year} '
            '${timestamp.hour.toString().padLeft(2, '0')}:'
            '${timestamp.minute.toString().padLeft(2, '0')}';
  return [formattedTime, author].where((part) => part.isNotEmpty).join(' · ');
}

class _ProfileCount extends StatelessWidget {
  const _ProfileCount({required this.label, required this.count});
  final String label;
  final int count;
  @override
  Widget build(BuildContext context) => ListTile(
    contentPadding: EdgeInsets.zero,
    title: Text(label),
    trailing: Text('$count', style: Theme.of(context).textTheme.titleLarge),
  );
}

class SquadScreen extends ConsumerWidget {
  const SquadScreen({
    super.key,
    required this.connectionId,
    required this.serverNumber,
    required this.team,
    required this.squadName,
  });

  final String connectionId;
  final int serverNumber;
  final String team;
  final String squadName;

  Future<Map<String, dynamic>> _load(WidgetRef ref) async {
    final profiles = await ref.read(connectionsProvider.future);
    final profile = profiles.firstWhere((item) => item.id == connectionId);
    return CrconApi(
      profile,
      ref.read(secureStoreProvider),
    ).squad(serverNumber, team, squadName);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    appBar: AppBar(
      title: Text(
        '${context.teamName(team)} · ${context.squadName(squadName)}',
      ),
    ),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _load(ref),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return _ErrorView(message: snapshot.error.toString());
        }
        final squad = snapshot.data!;
        final players = squad['players'] as List<dynamic>? ?? const [];
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.squadName(
                        squad['squad_name']?.toString() ?? squadName,
                      ),
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${context.teamName(squad['team']?.toString() ?? team)} · '
                      '${context.squadTypeName(squad['type']?.toString())} · '
                      '${players.length} ${context.tr('Mitglieder', 'members')}',
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Icon(
                          squad['has_leader'] == true
                              ? Icons.verified_user
                              : Icons.warning_amber,
                          color: squad['has_leader'] == true
                              ? FrontlineTheme.success
                              : FrontlineTheme.warning,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          squad['has_leader'] == true
                              ? context.tr(
                                  'Squad Leader aktiv',
                                  'Squad leader active',
                                )
                              : context.tr(
                                  'Kein Squad Leader',
                                  'No squad leader',
                                ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              context.tr('Mitglieder', 'Members'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            ...players.map((value) {
              final player = Map<String, dynamic>.from(value as Map);
              final playerId = player['player_id']?.toString() ?? '';
              return Card(
                child: ListTile(
                  leading: Icon(
                    _isSquadLeader(player['role']?.toString())
                        ? Icons.shield
                        : Icons.person_outline,
                  ),
                  title: Text(player['name']?.toString() ?? playerId),
                  subtitle: Text(
                    [
                      context.roleName(player['role']?.toString()),
                      if (player['level'] != null) 'Lvl ${player['level']}',
                      'K ${player['kills'] ?? '—'} / D ${player['deaths'] ?? '—'}',
                    ].whereType<String>().join(' · '),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: playerId.isEmpty
                      ? null
                      : () => context.push(
                          '/players/$connectionId/$playerId'
                          '?server_number=$serverNumber',
                        ),
                ),
              );
            }),
          ],
        );
      },
    ),
  );
}

bool _isSquadLeader(String? role) => {
  'officer',
  'tankcommander',
  'spotter',
}.contains(role?.replaceAll(' ', '').toLowerCase());

class IncidentScreen extends ConsumerStatefulWidget {
  const IncidentScreen({
    super.key,
    required this.connectionId,
    required this.incidentId,
  });
  final String connectionId;
  final String incidentId;
  @override
  ConsumerState<IncidentScreen> createState() => _IncidentScreenState();
}

class _IncidentScreenState extends ConsumerState<IncidentScreen> {
  AdminIncident? _incident;
  String? _error;
  bool _busy = true;

  Future<CrconApi> _api() async {
    final profiles = await ref.read(connectionsProvider.future);
    final profile = profiles.firstWhere(
      (item) => item.id == widget.connectionId,
    );
    return CrconApi(profile, ref.read(secureStoreProvider));
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final payload = await (await _api()).incident(widget.incidentId);
      if (mounted) {
        setState(
          () =>
              _incident = AdminIncident.fromJson(payload, widget.connectionId),
        );
      }
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _mutate(
    String operation, [
    Map<String, dynamic> payload = const {},
  ]) async {
    final incident = _incident;
    if (incident == null || _busy) return;
    setState(() => _busy = true);
    try {
      final response = await (await _api()).mutateIncident(
        incident.id,
        operation: operation,
        revision: incident.revision,
        payload: payload,
      );
      setState(
        () => _incident = AdminIncident.fromJson(response, widget.connectionId),
      );
      ref.invalidate(inboxProvider);
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _mutateSubject(IncidentSubject subject, String operation) async {
    final incident = _incident;
    if (incident == null || _busy) return;
    setState(() => _busy = true);
    try {
      final response = await (await _api()).mutateIncidentSubject(
        incident.id,
        subject.id,
        revision: incident.revision,
        operation: operation,
      );
      if (mounted) {
        setState(
          () =>
              _incident = AdminIncident.fromJson(response, widget.connectionId),
        );
      }
      ref.invalidate(inboxProvider);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addNote() async {
    final incident = _incident;
    if (incident == null || _busy) return;
    final controller = TextEditingController();
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add private admin note'),
        content: TextField(
          controller: controller,
          autofocus: true,
          maxLines: 4,
          decoration: const InputDecoration(labelText: 'Note'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    final note = controller.text.trim();
    controller.dispose();
    if (submit != true || note.isEmpty) return;
    setState(() => _busy = true);
    try {
      final payload = await (await _api()).addNote(
        incident.id,
        revision: incident.revision,
        note: note,
      );
      setState(
        () => _incident = AdminIncident.fromJson(payload, widget.connectionId),
      );
      ref.invalidate(inboxProvider);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _linkTarget() async {
    final id = TextEditingController();
    final name = TextEditingController();
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Link target player'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'Player name'),
            ),
            TextField(
              controller: id,
              decoration: const InputDecoration(labelText: 'Player ID'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Link'),
          ),
        ],
      ),
    );
    final playerId = id.text.trim();
    final playerName = name.text.trim();
    id.dispose();
    name.dispose();
    if (submit != true || playerId.isEmpty || playerName.isEmpty) return;
    await _mutate('link_target', {
      'target_id': playerId,
      'target_name': playerName,
    });
  }

  Future<void> _reassign() async {
    final controller = TextEditingController();
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Reassign incident'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'CRCON username'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Reassign'),
          ),
        ],
      ),
    );
    final username = controller.text.trim();
    controller.dispose();
    if (submit != true || username.isEmpty) return;
    await _mutate('reassign', {'assigned_to': username});
  }

  Future<void> _action(
    String action, {
    IncidentSubject? subject,
    Map<String, dynamic>? selectedPlayer,
  }) async {
    final incident = _incident;
    subject ??= incident?.primarySubject;
    final playerId =
        selectedPlayer?['player_id']?.toString() ?? subject?.actionPlayerId;
    final playerName =
        selectedPlayer?['name']?.toString() ??
        (subject?.kind == 'player'
            ? subject?.displayName
            : subject?.leaderName);
    if (incident == null || subject == null || playerId == null) return;
    final controller = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(switch (action) {
          'temp_ban' => context.tr('Temporäre Sperre', 'Temporary ban'),
          'perma_ban' => context.tr('Permanente Sperre', 'Permanent ban'),
          'kick' => context.tr('Spieler kicken', 'Kick player'),
          'punish' => context.tr('Spieler bestrafen', 'Punish player'),
          'message' => context.tr('Nachricht senden', 'Send message'),
          'comment' => context.tr('Admin-Kommentar', 'Admin comment'),
          _ => action,
        }),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(
            labelText: action == 'message'
                ? 'Message'
                : action == 'comment'
                ? 'Admin comment'
                : 'Required reason',
          ),
          maxLines: 3,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
    if (confirmed != true || controller.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await (await _api()).runAction(incident.id, {
        'action': action,
        'subject_id': subject.id,
        'player_id': playerId,
        'player_name': ?playerName,
        action == 'message'
            ? 'message'
            : action == 'comment'
            ? 'comment'
            : 'reason': controller.text
            .trim(),
        if (action == 'kick' || action == 'temp_ban' || action == 'perma_ban')
          'confirmed': true,
        if (action == 'temp_ban') 'duration_hours': 2,
      });
      await _load();
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _openPlayer(String playerId) => context.push(
    '/players/${widget.connectionId}/$playerId'
    '?server_number=${_incident!.serverNumber}',
  );

  Map<String, dynamic>? _liveSubject(IncidentSubject subject) {
    final subjects = _incident?.liveContext['subjects'] as Map?;
    final value = subjects?[subject.id];
    return value is Map ? Map<String, dynamic>.from(value) : null;
  }

  String _contextLine(Map<String, dynamic> value) =>
      [
            context.teamName(value['team']?.toString()),
            value['unit_name']?.toString() ?? value['squad_name']?.toString(),
            context.roleName(value['role']?.toString()),
          ]
          .whereType<String>()
          .where((item) => item.isNotEmpty && item != '—')
          .join(' · ');

  Widget _workflow(AdminIncident incident) => Wrap(
    spacing: 8,
    runSpacing: 8,
    children: [
      if (incident.status == 'new')
        FilledButton(
          onPressed: _busy ? null : () => _mutate('claim'),
          child: Text(context.tr('Übernehmen', 'Claim')),
        ),
      if (incident.status == 'claimed')
        OutlinedButton(
          onPressed: _busy ? null : () => _mutate('unclaim'),
          child: Text(context.tr('Freigeben', 'Release')),
        ),
      if (!{'resolved', 'dismissed'}.contains(incident.status))
        OutlinedButton(
          onPressed: _busy ? null : _reassign,
          child: Text(context.tr('Neu zuweisen', 'Reassign')),
        ),
      if (!{'resolved', 'dismissed'}.contains(incident.status)) ...[
        FilledButton.tonal(
          onPressed: _busy ? null : () => _mutate('resolved'),
          child: Text(context.tr('Erledigt', 'Resolve')),
        ),
        OutlinedButton(
          onPressed: _busy ? null : () => _mutate('dismissed'),
          child: Text(context.tr('Abweisen', 'Dismiss')),
        ),
      ] else
        FilledButton(
          onPressed: _busy ? null : () => _mutate('reopen'),
          child: Text(context.tr('Wieder öffnen', 'Reopen')),
        ),
    ],
  );

  Widget _messageTab(AdminIncident incident) {
    final liveReporterValue = incident.liveContext['reporter'];
    final liveReporter = liveReporterValue is Map
        ? Map<String, dynamic>.from(liveReporterValue)
        : null;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          context.tr('Originalmeldung', 'Original report'),
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        SelectableText(incident.rawMessage ?? incident.reason),
        const Divider(height: 32),
        Text(
          context.tr('Melder', 'Reporter'),
          style: Theme.of(context).textTheme.titleLarge,
        ),
        Card(
          child: ListTile(
            leading: const Icon(Icons.campaign_outlined),
            title: Text(
              incident.reporterName ?? context.tr('Unbekannt', 'Unknown'),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _contextLine(incident.reporterContext).isEmpty
                      ? context.tr(
                          'Kein Meldesnapshot verfügbar',
                          'No report snapshot available',
                        )
                      : '${context.tr('Damals', 'Then')}: '
                            '${_contextLine(incident.reporterContext)}',
                ),
                Text(
                  liveReporter == null
                      ? context.tr(
                          'Jetzt: offline oder nicht gefunden',
                          'Now: offline or not found',
                        )
                      : '${context.tr('Jetzt', 'Now')}: '
                            '${_contextLine(liveReporter)}',
                  style: const TextStyle(color: FrontlineTheme.muted),
                ),
              ],
            ),
            trailing: incident.reporterId == null
                ? null
                : const Icon(Icons.chevron_right),
            onTap: incident.reporterId == null
                ? null
                : () => _openPlayer(incident.reporterId!),
          ),
        ),
        const Divider(height: 28),
        _workflow(incident),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: _busy ? null : _addNote,
          icon: const Icon(Icons.note_add_outlined),
          label: Text(context.tr('Notiz hinzufügen', 'Add note')),
        ),
      ],
    );
  }

  Widget _targetsTab(AdminIncident incident) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      if (incident.subjects.isEmpty)
        Text(
          context.tr(
            'Noch kein Spieler oder Squad erkannt.',
            'No player or squad has been recognized yet.',
          ),
        ),
      ...incident.subjects.map((subject) {
        final live = _liveSubject(subject);
        final thenLine = subject.kind == 'player'
            ? _contextLine(subject.snapshot)
            : [
                context.teamName(subject.team),
                context.squadName(subject.squadName),
                context.squadTypeName(subject.squadType),
              ].whereType<String>().join(' · ');
        final nowLine = live == null ? '' : _contextLine(live);
        final percent = subject.confidence == null
            ? null
            : (subject.confidence! * 100).round();
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(
                    subject.kind == 'squad' ? Icons.groups_2 : Icons.person,
                    color: subject.state == 'confirmed'
                        ? FrontlineTheme.success
                        : subject.state == 'rejected'
                        ? Theme.of(context).disabledColor
                        : FrontlineTheme.warning,
                  ),
                  title: Text(
                    subject.kind == 'squad'
                        ? context.squadName(
                            subject.squadName ?? subject.displayName,
                          )
                        : subject.displayName,
                  ),
                  subtitle: Text(
                    [
                      subject.kind == 'squad'
                          ? context.tr('Squad', 'Squad')
                          : context.tr('Spieler', 'Player'),
                      context.subjectState(subject.state),
                      subject.matchMethod,
                      if (percent != null) '$percent %',
                    ].whereType<String>().join(' · '),
                  ),
                  trailing: subject.isPrimary
                      ? const Icon(Icons.star, color: FrontlineTheme.gold)
                      : null,
                  onTap: subject.kind == 'player' && subject.playerId != null
                      ? () => _openPlayer(subject.playerId!)
                      : subject.kind == 'squad' &&
                            subject.team != null &&
                            subject.squadName != null
                      ? () => context.push(
                          '/squads/${widget.connectionId}/${incident.serverNumber}/'
                          '${Uri.encodeComponent(subject.team!)}/'
                          '${Uri.encodeComponent(subject.squadName!)}',
                        )
                      : null,
                ),
                if (thenLine.isNotEmpty)
                  Text('${context.tr('Damals', 'Then')}: $thenLine'),
                Text(
                  live == null
                      ? context.tr(
                          'Jetzt: offline oder nicht gefunden',
                          'Now: offline or not found',
                        )
                      : '${context.tr('Jetzt', 'Now')}: $nowLine',
                  style: TextStyle(
                    color: live == null ? FrontlineTheme.muted : null,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    if (subject.state == 'suggested') ...[
                      FilledButton.tonal(
                        onPressed: _busy
                            ? null
                            : () => _mutateSubject(subject, 'confirm'),
                        child: Text(context.tr('Bestätigen', 'Confirm')),
                      ),
                      OutlinedButton(
                        onPressed: _busy
                            ? null
                            : () => _mutateSubject(subject, 'reject'),
                        child: Text(context.tr('Verwerfen', 'Reject')),
                      ),
                    ],
                    if (subject.state == 'confirmed' && !subject.isPrimary)
                      OutlinedButton(
                        onPressed: _busy
                            ? null
                            : () => _mutateSubject(subject, 'set_primary'),
                        child: Text(
                          context.tr('Als Hauptziel', 'Make primary'),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        );
      }),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        onPressed: _busy ? null : _linkTarget,
        icon: const Icon(Icons.person_add_alt),
        label: Text(
          context.tr('Spieler manuell hinzufügen', 'Add player manually'),
        ),
      ),
    ],
  );

  Widget _squadTab(AdminIncident incident) {
    final squads = incident.subjects.where(
      (subject) => subject.kind == 'squad',
    );
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (squads.isEmpty)
          Text(
            context.tr(
              'Kein Squad in dieser Meldung.',
              'No squad in this report.',
            ),
          ),
        ...squads.map((subject) {
          final snapshot = subject.snapshot;
          final oldPlayers = snapshot['players'] as List<dynamic>? ?? const [];
          final live = _liveSubject(subject);
          final livePlayers = live?['players'] as List<dynamic>? ?? const [];
          final liveIds = livePlayers
              .map((player) => (player as Map)['player_id']?.toString())
              .toSet();
          final oldIds = oldPlayers
              .map((player) => (player as Map)['player_id']?.toString())
              .toSet();
          final joinedPlayers = livePlayers.where(
            (player) =>
                !oldIds.contains((player as Map)['player_id']?.toString()),
          );
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Card(
                child: ListTile(
                  leading: const Icon(Icons.groups_2),
                  title: Text(
                    '${context.teamName(subject.team)} · '
                    '${context.squadName(subject.squadName)}',
                  ),
                  subtitle: Text(
                    '${context.squadTypeName(subject.squadType)} · '
                    '${oldPlayers.length} ${context.tr('damals', 'then')} · '
                    '${livePlayers.length} ${context.tr('jetzt', 'now')}',
                  ),
                ),
              ),
              ...oldPlayers.map((value) {
                final player = Map<String, dynamic>.from(value as Map);
                final playerId = player['player_id']?.toString() ?? '';
                final onlineInSquad = liveIds.contains(playerId);
                return ListTile(
                  leading: Icon(
                    _isSquadLeader(player['role']?.toString())
                        ? Icons.shield
                        : Icons.person_outline,
                  ),
                  title: Text(player['name']?.toString() ?? playerId),
                  subtitle: Text(
                    '${context.roleName(player['role']?.toString())} · '
                    '${onlineInSquad ? context.tr('unverändert', 'unchanged') : context.tr('offline/gewechselt', 'offline/moved')}',
                  ),
                  trailing: subject.state != 'confirmed' || playerId.isEmpty
                      ? const Icon(Icons.lock_outline)
                      : PopupMenuButton<String>(
                          onSelected: (action) {
                            if (action == 'profile') {
                              _openPlayer(playerId);
                            } else {
                              _action(
                                action,
                                subject: subject,
                                selectedPlayer: player,
                              );
                            }
                          },
                          itemBuilder: (_) => [
                            PopupMenuItem(
                              value: 'profile',
                              child: Text(
                                context.tr('Profil öffnen', 'Open profile'),
                              ),
                            ),
                            PopupMenuItem(
                              value: 'message',
                              child: Text(context.tr('Nachricht', 'Message')),
                            ),
                            PopupMenuItem(
                              value: 'punish',
                              child: Text(context.tr('Bestrafen', 'Punish')),
                            ),
                            PopupMenuItem(
                              value: 'kick',
                              child: Text(context.tr('Kicken', 'Kick')),
                            ),
                            PopupMenuItem(
                              value: 'temp_ban',
                              child: Text(
                                context.tr('Temporär sperren', 'Temporary ban'),
                              ),
                            ),
                            PopupMenuItem(
                              value: 'perma_ban',
                              child: Text(
                                context.tr(
                                  'Permanent sperren',
                                  'Permanent ban',
                                ),
                              ),
                            ),
                          ],
                        ),
                );
              }),
              ...joinedPlayers.map((value) {
                final player = Map<String, dynamic>.from(value as Map);
                final playerId = player['player_id']?.toString() ?? '';
                return ListTile(
                  leading: const Icon(
                    Icons.person_add_alt_1,
                    color: FrontlineTheme.success,
                  ),
                  title: Text(player['name']?.toString() ?? playerId),
                  subtitle: Text(
                    '${context.roleName(player['role']?.toString())} · '
                    '${context.tr('seit der Meldung beigetreten', 'joined since report')}',
                  ),
                  trailing: playerId.isEmpty
                      ? null
                      : IconButton(
                          tooltip: context.tr('Profil öffnen', 'Open profile'),
                          onPressed: () => _openPlayer(playerId),
                          icon: const Icon(Icons.chevron_right),
                        ),
                );
              }),
              const Divider(height: 28),
            ],
          );
        }),
      ],
    );
  }

  Widget _timelineTab(AdminIncident incident) => ListView(
    padding: const EdgeInsets.all(16),
    children: incident.events.reversed
        .map(
          (event) => ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.history),
            title: Text(event['event_type']?.toString() ?? 'event'),
            subtitle: Text(
              [
                event['actor']?.toString() ?? 'system',
                if (event['event_type'] == 'note')
                  (event['payload'] as Map?)?['note']?.toString() ?? '',
              ].where((value) => value.isNotEmpty).join(' · '),
            ),
          ),
        )
        .toList(),
  );

  Widget _primaryActions(AdminIncident incident) {
    final subject = incident.primarySubject;
    if (subject == null || subject.actionPlayerId == null) {
      return SafeArea(
        top: false,
        child: Container(
          width: double.infinity,
          color: FrontlineTheme.surfaceHigh,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Text(
            context.tr(
              'Bestätige und wähle zuerst einen Spieler für Maßnahmen.',
              'Confirm and select a player before running an action.',
            ),
            style: const TextStyle(color: FrontlineTheme.muted),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return SafeArea(
      child: Container(
        color: FrontlineTheme.surfaceHigh,
        padding: const EdgeInsets.all(10),
        child: Row(
          children: [
            Expanded(
              child: Text(
                subject.kind == 'player'
                    ? subject.displayName
                    : subject.leaderName ?? subject.displayName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            IconButton(
              tooltip: context.tr('Nachricht', 'Message'),
              onPressed: _busy
                  ? null
                  : () => _action('message', subject: subject),
              icon: const Icon(Icons.message_outlined),
            ),
            IconButton(
              tooltip: context.tr('Bestrafen', 'Punish'),
              onPressed: _busy
                  ? null
                  : () => _action('punish', subject: subject),
              icon: const Icon(Icons.gavel_outlined),
            ),
            PopupMenuButton<String>(
              onSelected: (action) => _action(action, subject: subject),
              itemBuilder: (_) => [
                PopupMenuItem(
                  value: 'comment',
                  child: Text(context.tr('Kommentar', 'Comment')),
                ),
                PopupMenuItem(
                  value: 'kick',
                  child: Text(context.tr('Kicken', 'Kick')),
                ),
                PopupMenuItem(
                  value: 'temp_ban',
                  child: Text(context.tr('Temporär sperren', 'Temporary ban')),
                ),
                PopupMenuItem(
                  value: 'perma_ban',
                  child: Text(context.tr('Permanent sperren', 'Permanent ban')),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(liveIncidentUpdateProvider, (_, next) {
      if (next?.connectionId == widget.connectionId &&
          next?.incident['id']?.toString() == widget.incidentId &&
          !_busy) {
        _load();
      }
    });
    final incident = _incident;
    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('Vorfall', 'Incident')),
        actions: [
          IconButton(
            onPressed: _busy ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
          const _LanguageButton(),
        ],
      ),
      body: _busy && incident == null
          ? const Center(child: CircularProgressIndicator())
          : incident == null
          ? _ErrorView(
              message:
                  _error ??
                  context.tr('Vorfall nicht verfügbar', 'Incident unavailable'),
            )
          : DefaultTabController(
              length: 4,
              child: Column(
                children: [
                  if (_busy) const LinearProgressIndicator(minHeight: 2),
                  if (_error != null) _ErrorView(message: _error!),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              incident.reason,
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                Chip(
                                  label: Text(
                                    'Server ${incident.serverNumber}',
                                  ),
                                ),
                                Chip(
                                  label: Text(
                                    context.incidentStatus(incident.status),
                                  ),
                                ),
                                if (incident.primarySubject != null)
                                  Chip(
                                    avatar: Icon(
                                      incident.primarySubject!.kind == 'squad'
                                          ? Icons.groups_2
                                          : Icons.person,
                                      size: 18,
                                    ),
                                    label: Text(
                                      incident.primarySubject!.kind == 'squad'
                                          ? context.squadName(
                                              incident
                                                      .primarySubject!
                                                      .squadName ??
                                                  incident
                                                      .primarySubject!
                                                      .displayName,
                                            )
                                          : incident
                                                .primarySubject!
                                                .displayName,
                                    ),
                                  ),
                                if (incident.suggestedCount > 0)
                                  Chip(
                                    avatar: const Icon(
                                      Icons.help_outline,
                                      size: 18,
                                      color: FrontlineTheme.warning,
                                    ),
                                    label: Text(
                                      '${incident.suggestedCount} '
                                      '${context.tr('offen', 'pending')}',
                                    ),
                                  ),
                              ],
                            ),
                            Text(
                              '${context.tr('Zugewiesen', 'Assigned')}: '
                              '${incident.assignedTo ?? '—'}',
                              style: const TextStyle(
                                color: FrontlineTheme.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  TabBar(
                    isScrollable: true,
                    tabs: [
                      Tab(text: context.tr('Meldung', 'Report')),
                      Tab(text: context.tr('Ziele', 'Subjects')),
                      Tab(text: context.tr('Squad', 'Squad')),
                      Tab(text: context.tr('Verlauf', 'Timeline')),
                    ],
                  ),
                  Expanded(
                    child: TabBarView(
                      children: [
                        _messageTab(incident),
                        _targetsTab(incident),
                        _squadTab(incident),
                        _timelineTab(incident),
                      ],
                    ),
                  ),
                ],
              ),
            ),
      bottomNavigationBar: incident == null ? null : _primaryActions(incident),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message});
  final String message;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(20),
    child: Text(
      message,
      textAlign: TextAlign.center,
      style: TextStyle(color: Theme.of(context).colorScheme.error),
    ),
  );
}


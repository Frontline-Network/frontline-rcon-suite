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
import 'package:url_launcher/url_launcher.dart';

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

Map<String, dynamic> _mapValue(Object? value) =>
    value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};

Map<String, dynamic>? _nullableMapValue(Object? value) =>
    value is Map ? Map<String, dynamic>.from(value) : null;

List<Object?> _listValue(Object? value) => value is List ? value : const [];

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
    GoRoute(
      path: '/autobalancer',
      builder: (_, _) => const AutobalancerScreen(),
    ),
    GoRoute(path: '/watchlist', builder: (_, _) => const WatchlistScreen()),
    GoRoute(path: '/live-status', builder: (_, _) => const LiveStatusScreen()),
    GoRoute(path: '/diagnostics', builder: (_, _) => const DiagnosticsScreen()),
    GoRoute(
      path: '/players/:connectionId/:playerId',
      builder: (_, state) => PlayerProfileScreen(
        connectionId: state.pathParameters['connectionId']!,
        playerId: state.pathParameters['playerId']!,
        incidentContext: state.extra is PlayerIncidentContext
            ? state.extra! as PlayerIncidentContext
            : null,
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
        title: Text(context.tr('Mehr', 'More')),
        actions: [
          IconButton(
            tooltip: context.tr('Diagnoseprotokoll', 'Diagnostics log'),
            onPressed: () => context.push('/diagnostics'),
            icon: const Icon(Icons.bug_report_outlined),
          ),
        ],
      ),
      bottomNavigationBar: const _FrontlineBottomBar(currentIndex: 2),
      body: profiles.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorView(message: error.toString()),
        data: (items) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            Text(
              context.tr('Verbindungen', 'Connections'),
              style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Text(
              context.tr(
                'Gekoppelte CRCON-Installationen und dieses Gerät.',
                'Paired CRCON installations and this device.',
              ),
              style: const TextStyle(color: FrontlineTheme.muted),
            ),
            const SizedBox(height: 18),
            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.balance_outlined,
                  color: FrontlineTheme.gold,
                ),
                title: Text(
                  context.tr('Fair Autobalancer', 'Fair Autobalancer'),
                ),
                subtitle: Text(
                  context.tr(
                    'Live-Stand aller Teams ansehen',
                    'View the live state of all teams',
                  ),
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push('/autobalancer'),
              ),
            ),
            if (items.isNotEmpty) ...[
              const SizedBox(height: 12),
              _MoreOperations(profile: items.first),
            ],
            const SizedBox(height: 12),
            if (items.isEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    context.tr(
                      'Kopple zuerst eine CRCON-Installation.',
                      'Pair your first CRCON installation.',
                    ),
                  ),
                ),
              )
            else
              ...items.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _ConnectionCard(profile: item),
                ),
              ),
            const SizedBox(height: 6),
            OutlinedButton.icon(
              onPressed: () => context.push('/pair'),
              icon: const Icon(Icons.qr_code_scanner),
              label: Text(context.tr('CRCON koppeln', 'Pair CRCON')),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MoreOperations extends ConsumerWidget {
  const _MoreOperations({required this.profile});

  final ConnectionProfile profile;

  @override
  Widget build(BuildContext context, WidgetRef ref) => FutureBuilder(
    future: CrconApi(profile, ref.read(secureStoreProvider)).bootstrap(),
    builder: (context, snapshot) {
      if (!snapshot.hasData) return const SizedBox.shrink();
      final configuration = _mapValue(snapshot.data!['mobile_configuration']);
      final playerOperations = configuration['player_operations'] == true;
      final liveStatus = configuration['live_status'] == true;
      if (!playerOperations && !liveStatus) return const SizedBox.shrink();
      return Column(
        children: [
          if (playerOperations)
            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.visibility_outlined,
                  color: FrontlineTheme.gold,
                ),
                title: Text(context.tr('Beobachtungsliste', 'Watchlist')),
                subtitle: Text(
                  context.tr(
                    'Beobachtete Spieler und letzter Kontakt',
                    'Watched players and last contact',
                  ),
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push('/watchlist'),
              ),
            ),
          if (playerOperations && liveStatus) const SizedBox(height: 12),
          if (liveStatus)
            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.radar_outlined,
                  color: FrontlineTheme.gold,
                ),
                title: Text(context.tr('Server-Lage', 'Server situation')),
                subtitle: Text(
                  context.tr(
                    'Karte, Teams, Warteschlange und Admins',
                    'Map, teams, queue and admins',
                  ),
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push('/live-status'),
              ),
            ),
        ],
      );
    },
  );
}

class WatchlistScreen extends ConsumerStatefulWidget {
  const WatchlistScreen({super.key});

  @override
  ConsumerState<WatchlistScreen> createState() => _WatchlistScreenState();
}

class _WatchlistScreenState extends ConsumerState<WatchlistScreen> {
  ConnectionProfile? _profile;
  List<Map<String, dynamic>> _servers = const [];
  List<Map<String, dynamic>> _players = const [];
  int? _serverNumber;
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    unawaited(_initialize());
  }

  Future<void> _initialize() async {
    try {
      final profiles = await ref.read(connectionsProvider.future);
      if (profiles.isEmpty) return;
      final profile = profiles.first;
      final bootstrap = await CrconApi(
        profile,
        ref.read(secureStoreProvider),
      ).bootstrap();
      final servers = _listValue(
        bootstrap['servers'],
      ).map(_mapValue).where((value) => value['server_number'] is num).toList();
      if (mounted) {
        setState(() {
          _profile = profile;
          _servers = servers;
          _serverNumber = servers.isNotEmpty
              ? (servers.first['server_number'] as num).toInt()
              : (bootstrap['server_number'] as num?)?.toInt();
        });
      }
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _load() async {
    final profile = _profile;
    if (profile == null) return;
    setState(() => _loading = true);
    try {
      final players = await CrconApi(
        profile,
        ref.read(secureStoreProvider),
      ).watchlist(serverNumber: _serverNumber);
      if (mounted) setState(() => _players = players);
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(context.tr('Beobachtungsliste', 'Watchlist')),
      actions: [
        IconButton(
          onPressed: _loading ? null : _load,
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    bottomNavigationBar: const _FrontlineBottomBar(currentIndex: 2),
    body: _error != null
        ? _ErrorView(message: _error.toString())
        : _loading && _profile == null
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (_servers.length > 1)
                DropdownButtonFormField<int>(
                  initialValue: _serverNumber,
                  decoration: InputDecoration(
                    labelText: context.tr('Server', 'Server'),
                  ),
                  items: _servers.map((server) {
                    final number = (server['server_number'] as num).toInt();
                    return DropdownMenuItem(
                      value: number,
                      child: Text(
                        server['name']?.toString() ?? 'Server $number',
                      ),
                    );
                  }).toList(),
                  onChanged: (value) {
                    if (value == null) {
                      return;
                    }
                    setState(() => _serverNumber = value);
                    unawaited(_load());
                  },
                ),
              if (_servers.length > 1) const SizedBox(height: 14),
              if (_loading) const LinearProgressIndicator(),
              if (_players.isEmpty && !_loading)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Text(
                      context.tr(
                        'Keine Spieler werden aktuell beobachtet.',
                        'No players are currently watched.',
                      ),
                    ),
                  ),
                ),
              ..._players.map((player) {
                final id = player['player_id']?.toString() ?? '';
                final modified = player['modified']?.toString();
                return Card(
                  child: ListTile(
                    leading: Icon(
                      player['online'] == true
                          ? Icons.visibility
                          : Icons.visibility_outlined,
                      color: player['online'] == true
                          ? FrontlineTheme.success
                          : FrontlineTheme.gold,
                    ),
                    title: Text(player['name']?.toString() ?? id),
                    subtitle: Text(
                      [
                            player['reason']?.toString(),
                            if (player['by'] case final by?)
                              '${context.tr('von', 'by')} $by',
                            modified ?? '',
                            '${player['count'] ?? 0} ${context.tr('Sichtungen', 'sightings')}',
                          ]
                          .whereType<String>()
                          .where((value) => value.isNotEmpty)
                          .join(' · '),
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: id.isEmpty || _profile == null
                        ? null
                        : () => context.push(
                            '/players/${_profile!.id}/$id?server_number=${_serverNumber ?? ''}',
                          ),
                  ),
                );
              }),
            ],
          ),
  );
}

class LiveStatusScreen extends ConsumerStatefulWidget {
  const LiveStatusScreen({super.key});

  @override
  ConsumerState<LiveStatusScreen> createState() => _LiveStatusScreenState();
}

class _LiveStatusScreenState extends ConsumerState<LiveStatusScreen> {
  ConnectionProfile? _profile;
  List<Map<String, dynamic>> _servers = const [];
  int? _serverNumber;
  Map<String, dynamic>? _status;
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    unawaited(_initialize());
  }

  Future<void> _initialize() async {
    try {
      final profiles = await ref.read(connectionsProvider.future);
      if (profiles.isEmpty) return;
      final profile = profiles.first;
      final bootstrap = await CrconApi(
        profile,
        ref.read(secureStoreProvider),
      ).bootstrap();
      final servers = _listValue(bootstrap['servers']).map(_mapValue).toList();
      if (mounted) {
        setState(() {
          _profile = profile;
          _servers = servers;
          _serverNumber = servers.isNotEmpty
              ? (servers.first['server_number'] as num?)?.toInt()
              : (bootstrap['server_number'] as num?)?.toInt();
        });
      }
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _load() async {
    if (_profile == null || _serverNumber == null) return;
    setState(() => _loading = true);
    try {
      final value = await CrconApi(
        _profile!,
        ref.read(secureStoreProvider),
      ).liveStatus(_serverNumber!);
      if (mounted) setState(() => _status = value);
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final status = _mapValue(_status?['status']);
    final match = _mapValue(_status?['match']);
    final counts = _mapValue(match['team_counts']);
    final scores = _mapValue(match['team_scores']);
    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('Server-Lage', 'Server situation')),
        actions: [
          IconButton(
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      bottomNavigationBar: const _FrontlineBottomBar(currentIndex: 2),
      body: _error != null
          ? _ErrorView(message: _error.toString())
          : _loading && _status == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_servers.length > 1)
                  DropdownButtonFormField<int>(
                    initialValue: _serverNumber,
                    decoration: InputDecoration(
                      labelText: context.tr('Server', 'Server'),
                    ),
                    items: _servers.map((server) {
                      final number = (server['server_number'] as num).toInt();
                      return DropdownMenuItem(
                        value: number,
                        child: Text(
                          server['name']?.toString() ?? 'Server $number',
                        ),
                      );
                    }).toList(),
                    onChanged: (value) {
                      if (value == null) {
                        return;
                      }
                      setState(() => _serverNumber = value);
                      unawaited(_load());
                    },
                  ),
                if (_servers.length > 1) const SizedBox(height: 14),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          status['name']?.toString() ??
                              'Server ${_serverNumber ?? '—'}',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 12),
                        _LiveStatusRow(
                          label: context.tr('Aktuelle Karte', 'Current map'),
                          value: _liveMapName(
                            match['current_map'] ?? status['map'],
                          ),
                        ),
                        if (_status?['next_map'] != null)
                          _LiveStatusRow(
                            label: context.tr('Nächste Karte', 'Next map'),
                            value: _liveMapName(_status?['next_map']),
                          ),
                        if (match['time_remaining'] != null)
                          _LiveStatusRow(
                            label: context.tr('Restzeit', 'Time remaining'),
                            value: match['time_remaining'].toString(),
                          ),
                        if (status.isNotEmpty)
                          _LiveStatusRow(
                            label: context.tr('Spieler', 'Players'),
                            value:
                                '${status['current_players'] ?? '—'} / ${status['max_players'] ?? '—'}',
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.tr('Teams & Betrieb', 'Teams & operations'),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 10),
                        if (counts.isNotEmpty)
                          _LiveStatusRow(
                            label: context.tr(
                              'Alliierte / Achse',
                              'Allies / Axis',
                            ),
                            value:
                                '${counts['allies'] ?? '—'} / ${counts['axis'] ?? '—'}',
                          ),
                        if (scores.isNotEmpty)
                          _LiveStatusRow(
                            label: context.tr('Punkte', 'Scores'),
                            value:
                                '${scores['allies'] ?? '—'} / ${scores['axis'] ?? '—'}',
                          ),
                        if (_status?['queue_length'] != null)
                          _LiveStatusRow(
                            label: context.tr('Warteschlange', 'Queue'),
                            value: _status!['queue_length'].toString(),
                          ),
                        if (_status?['ingame_admin_count'] != null)
                          _LiveStatusRow(
                            label: context.tr(
                              'Ingame-Admins',
                              'In-game admins',
                            ),
                            value: _status!['ingame_admin_count'].toString(),
                          ),
                        if (_status?['crcon_admin_count'] != null)
                          _LiveStatusRow(
                            label: context.tr('CRCON-Admins', 'CRCON admins'),
                            value: _status!['crcon_admin_count'].toString(),
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => context.push('/autobalancer'),
                  icon: const Icon(Icons.balance_outlined),
                  label: Text(
                    context.tr(
                      'Fair Autobalancer öffnen',
                      'Open Fair Autobalancer',
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

String _liveMapName(dynamic value) {
  if (value is Map) {
    return value['pretty_name']?.toString() ??
        value['name']?.toString() ??
        value['id']?.toString() ??
        '—';
  }
  return value?.toString() ?? '—';
}

class _LiveStatusRow extends StatelessWidget {
  const _LiveStatusRow({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(color: FrontlineTheme.muted),
          ),
        ),
        Text(value),
      ],
    ),
  );
}

class AutobalancerScreen extends ConsumerStatefulWidget {
  const AutobalancerScreen({super.key});

  @override
  ConsumerState<AutobalancerScreen> createState() => _AutobalancerScreenState();
}

class _AutobalancerScreenState extends ConsumerState<AutobalancerScreen> {
  ConnectionProfile? _profile;
  List<Map<String, dynamic>> _servers = const [];
  int? _serverNumber;
  Map<String, dynamic>? _status;
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    unawaited(_initialize());
  }

  Future<void> _initialize() async {
    try {
      final profiles = await ref.read(connectionsProvider.future);
      if (profiles.isEmpty) {
        if (mounted) setState(() => _loading = false);
        return;
      }
      final profile = profiles.first;
      final bootstrap = await CrconApi(
        profile,
        ref.read(secureStoreProvider),
      ).bootstrap();
      final servers = _listValue(bootstrap['servers'])
          .map(_mapValue)
          .where((server) => server['server_number'] is num)
          .toList();
      final fallback = (bootstrap['server_number'] as num?)?.toInt();
      if (mounted) {
        setState(() {
          _profile = profile;
          _servers = servers.isEmpty && fallback != null
              ? [
                  <String, dynamic>{'server_number': fallback},
                ]
              : servers;
          _serverNumber = _servers.isNotEmpty
              ? (_servers.first['server_number'] as num).toInt()
              : fallback;
        });
      }
      await _load();
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = error;
          _loading = false;
        });
      }
    }
  }

  Future<void> _load() async {
    final profile = _profile;
    final serverNumber = _serverNumber;
    if (profile == null || serverNumber == null) {
      if (mounted) setState(() => _loading = false);
      return;
    }
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final status = await CrconApi(
        profile,
        ref.read(secureStoreProvider),
      ).autobalancerStatus(serverNumber);
      if (mounted) setState(() => _status = status);
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  int _teamCount(Map<String, dynamic> counts, String team) {
    final value = counts[team] ?? counts[team == 'allies' ? 'Allies' : 'Axis'];
    return value is num
        ? value.toInt()
        : int.tryParse(value?.toString() ?? '') ?? 0;
  }

  String _serverLabel(BuildContext context, Map<String, dynamic> server) {
    final number = (server['server_number'] as num).toInt();
    return server['name']?.toString() ??
        context.tr('Server $number', 'Server $number');
  }

  String _phase(BuildContext context, String phase) => switch (phase) {
    'idle' => context.tr('Ausgeglichen', 'Balanced'),
    'armed' => context.tr('Beobachtet', 'Monitoring'),
    'proposed' => context.tr('Vorschlag aktiv', 'Proposal active'),
    'volunteer' => context.tr('Freiwillige gesucht', 'Seeking volunteers'),
    'verifying' => context.tr('Wechsel wird geprüft', 'Checking switch'),
    'cooldown' => context.tr('Abkühlphase', 'Cooldown'),
    'blocked' => context.tr('Pausiert', 'Paused'),
    _ => phase.isEmpty ? '—' : phase,
  };

  @override
  Widget build(BuildContext context) {
    final status = _status;
    final counts = _mapValue(status?['team_counts']);
    final allies = _teamCount(counts, 'allies');
    final axis = _teamCount(counts, 'axis');
    final total = allies + axis;
    final hasLiveTeamCounts = counts.isNotEmpty;
    final phase = status?['phase']?.toString() ?? 'idle';
    final required = (status?['required_switches'] as num?)?.toInt() ?? 0;
    final warnings = _listValue(status?['warnings'])
        .map((value) => value?.toString() ?? '')
        .where((value) => value.isNotEmpty)
        .toList();
    final blocks = _listValue(status?['block_reasons'])
        .map((value) => value?.toString() ?? '')
        .where((value) => value.isNotEmpty)
        .toList();
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Image.asset('assets/fln_logo.png', width: 20, height: 20),
            const SizedBox(width: 8),
            Text(context.tr('Fair Autobalancer', 'Fair Autobalancer')),
          ],
        ),
        actions: [
          IconButton(
            tooltip: context.tr('Aktualisieren', 'Refresh'),
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      bottomNavigationBar: const _FrontlineBottomBar(currentIndex: 2),
      body: _loading && status == null
          ? const Center(child: CircularProgressIndicator())
          : _profile == null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  context.tr(
                    'Kopple zuerst eine CRCON-Installation.',
                    'Pair a CRCON installation first.',
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 24),
              children: [
                if (_servers.isNotEmpty)
                  DropdownButtonFormField<int>(
                    key: ValueKey(_serverNumber),
                    initialValue: _serverNumber,
                    isExpanded: true,
                    decoration: InputDecoration(
                      labelText: context.tr('Spielserver', 'Game server'),
                      prefixIcon: const Icon(Icons.dns_outlined),
                    ),
                    items: _servers
                        .map(
                          (server) => DropdownMenuItem(
                            value: (server['server_number'] as num).toInt(),
                            child: Text(
                              _serverLabel(context, server),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(),
                    selectedItemBuilder: (context) => _servers
                        .map(
                          (server) => Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              _serverLabel(context, server),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: _loading
                        ? null
                        : (value) {
                            if (value == null) return;
                            setState(() => _serverNumber = value);
                            unawaited(_load());
                          },
                  ),
                const SizedBox(height: 14),
                if (_error != null) _ErrorView(message: _error.toString()),
                if (status != null) ...[
                  _AutobalancerHero(
                    phase: _phase(context, phase),
                    mode: status['mode']?.toString() ?? 'disabled',
                    requiredSwitches: required,
                    updatedAt: status['updated_at']?.toString(),
                  ),
                  const SizedBox(height: 12),
                  _AutobalancerTeamsCard(
                    allies: allies,
                    axis: axis,
                    total: total,
                    hasLiveTeamCounts: hasLiveTeamCounts,
                    difference: hasLiveTeamCounts
                        ? status['team_difference']
                        : null,
                  ),
                  const SizedBox(height: 12),
                  _AutobalancerDataCard(status: status),
                  if (blocks.isNotEmpty || warnings.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _AutobalancerMessages(blocks: blocks, warnings: warnings),
                  ],
                ],
                const SizedBox(height: 14),
                Text(
                  context.tr(
                    'Diese mobile Ansicht ist nur lesend. Entscheidungen, Konfiguration und Eingriffe bleiben in CRCON.',
                    'This mobile view is read-only. Decisions, configuration, and interventions remain in CRCON.',
                  ),
                  style: const TextStyle(
                    color: FrontlineTheme.muted,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
    );
  }
}

class _AutobalancerHero extends StatelessWidget {
  const _AutobalancerHero({
    required this.phase,
    required this.mode,
    required this.requiredSwitches,
    this.updatedAt,
  });

  final String phase;
  final String mode;
  final int requiredSwitches;
  final String? updatedAt;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      gradient: const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xff22281b), FrontlineTheme.surface],
      ),
      border: Border.all(color: FrontlineTheme.gold),
      borderRadius: BorderRadius.circular(4),
    ),
    child: Row(
      children: [
        const Icon(
          Icons.balance_outlined,
          color: FrontlineTheme.gold,
          size: 34,
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                phase,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                [
                  mode,
                  if (requiredSwitches > 0)
                    context.tr(
                      '$requiredSwitches Wechsel nötig',
                      '$requiredSwitches switch${requiredSwitches == 1 ? '' : 'es'} needed',
                    )
                  else
                    context.tr('Kein Wechsel nötig', 'No switch needed'),
                ].join(' · '),
                style: const TextStyle(color: FrontlineTheme.muted),
              ),
              if (updatedAt != null) ...[
                const SizedBox(height: 5),
                Text(
                  '${context.tr('Stand', 'Updated')} ${_compactAutobalancerTime(updatedAt!)}',
                  style: const TextStyle(
                    color: FrontlineTheme.muted,
                    fontSize: 12,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    ),
  );
}

class _AutobalancerTeamsCard extends StatelessWidget {
  const _AutobalancerTeamsCard({
    required this.allies,
    required this.axis,
    required this.total,
    required this.hasLiveTeamCounts,
    required this.difference,
  });

  final int allies;
  final int axis;
  final int total;
  final bool hasLiveTeamCounts;
  final Object? difference;

  @override
  Widget build(BuildContext context) {
    final share = total == 0 ? .5 : allies / total;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: FrontlineTheme.surface,
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.tr('Teamstärke', 'Team strength'),
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 14),
          if (!hasLiveTeamCounts)
            Row(
              children: [
                const Icon(
                  Icons.sensors_off_outlined,
                  color: FrontlineTheme.muted,
                  size: 22,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    context.tr(
                      'Noch keine Live-Teamzählung verfügbar.',
                      'Live team counts are not available yet.',
                    ),
                    style: const TextStyle(color: FrontlineTheme.muted),
                  ),
                ),
              ],
            )
          else ...[
            Row(
              children: [
                Expanded(
                  child: _AutobalancerTeamCount(
                    label: context.tr('Alliierte', 'Allies'),
                    count: allies,
                    color: const Color(0xff5d8ebf),
                    alignEnd: false,
                  ),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: _AutobalancerTeamCount(
                    label: context.tr('Achsenmächte', 'Axis'),
                    count: axis,
                    color: const Color(0xffb55c52),
                    alignEnd: true,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: SizedBox(
                height: 12,
                child: Row(
                  children: [
                    Expanded(
                      flex: (share * 100).round().clamp(1, 99),
                      child: const ColoredBox(color: Color(0xff5d8ebf)),
                    ),
                    Expanded(
                      flex: ((1 - share) * 100).round().clamp(1, 99),
                      child: const ColoredBox(color: Color(0xffb55c52)),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 10),
            Text(
              '${context.tr('Differenz', 'Difference')}: ${difference ?? '—'} ${context.tr('Spieler', 'players')}',
              style: const TextStyle(color: FrontlineTheme.muted),
            ),
          ],
        ],
      ),
    );
  }
}

class _AutobalancerTeamCount extends StatelessWidget {
  const _AutobalancerTeamCount({
    required this.label,
    required this.count,
    required this.color,
    required this.alignEnd,
  });

  final String label;
  final int count;
  final Color color;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: alignEnd
        ? CrossAxisAlignment.end
        : CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.w600),
      ),
      const SizedBox(height: 2),
      Text(
        '$count',
        style: const TextStyle(fontSize: 31, fontWeight: FontWeight.w700),
      ),
    ],
  );
}

class _AutobalancerDataCard extends StatelessWidget {
  const _AutobalancerDataCard({required this.status});
  final Map<String, dynamic> status;

  @override
  Widget build(BuildContext context) {
    final confidence = status['data_confidence'];
    final strategy = status['strategy']?.toString();
    final native = _mapValue(status['native_autobalance']);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: FrontlineTheme.surface,
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.tr('Bewertungsbasis', 'Assessment basis'),
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 11),
          _AutobalancerDataRow(
            icon: Icons.psychology_outlined,
            label: context.tr('Datenvertrauen', 'Data confidence'),
            value: confidence is num ? '${(confidence * 100).round()} %' : '—',
          ),
          if (strategy != null && strategy.isNotEmpty) ...[
            const SizedBox(height: 8),
            _AutobalancerDataRow(
              icon: Icons.account_tree_outlined,
              label: context.tr('Strategie', 'Strategy'),
              value: strategy,
            ),
          ],
          const SizedBox(height: 8),
          _AutobalancerDataRow(
            icon: Icons.settings_input_component_outlined,
            label: context.tr('HLL-Autobalance', 'HLL autobalance'),
            value: native['enabled'] == true
                ? context.tr('aktiv', 'enabled')
                : context.tr('inaktiv', 'disabled'),
          ),
        ],
      ),
    );
  }
}

class _AutobalancerDataRow extends StatelessWidget {
  const _AutobalancerDataRow({
    required this.icon,
    required this.label,
    required this.value,
  });
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Icon(icon, color: FrontlineTheme.gold, size: 20),
      const SizedBox(width: 10),
      Expanded(
        child: Text(label, style: const TextStyle(color: FrontlineTheme.muted)),
      ),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
    ],
  );
}

class _AutobalancerMessages extends StatelessWidget {
  const _AutobalancerMessages({required this.blocks, required this.warnings});
  final List<String> blocks;
  final List<String> warnings;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: const Color(0xff292519),
      border: Border.all(color: FrontlineTheme.warning),
      borderRadius: BorderRadius.circular(4),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final block in blocks)
          _AutobalancerMessage(icon: Icons.pause_circle_outline, text: block),
        for (final warning in warnings)
          _AutobalancerMessage(
            icon: Icons.warning_amber_outlined,
            text: warning,
          ),
      ],
    ),
  );
}

class _AutobalancerMessage extends StatelessWidget {
  const _AutobalancerMessage({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: FrontlineTheme.warning, size: 20),
        const SizedBox(width: 9),
        Expanded(child: Text(text)),
      ],
    ),
  );
}

String _compactAutobalancerTime(String raw) {
  final value = DateTime.tryParse(raw)?.toLocal();
  if (value == null) return raw;
  return '${value.day.toString().padLeft(2, '0')}.${value.month.toString().padLeft(2, '0')} ${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
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
      final device = _mapValue(bootstrap['device']);
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
        title: Text(context.tr('Gerät widerrufen?', 'Revoke this device?')),
        content: Text(
          context.tr(
            'CRCON entwertet Zugriffs- und Erneuerungstoken sofort.',
            'CRCON will invalidate its access and refresh tokens immediately.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.tr('Abbrechen', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.tr('Widerrufen', 'Revoke')),
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
          leading: const Icon(Icons.dns_outlined, color: FrontlineTheme.gold),
          title: Text(widget.profile.name),
          subtitle: Text(widget.profile.baseUrl),
          trailing: _busy
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const _OnlineBadge(label: 'Verbunden'),
        ),
        const Divider(height: 1),
        if (_notifications != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    context.tr(
                      'Vorfallbenachrichtigungen',
                      'Incident notifications',
                    ),
                  ),
                ),
                Switch(
                  value: _notifications!,
                  onChanged: _busy ? null : _setNotifications,
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: _busy ? null : _remove,
                ),
              ],
            ),
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
  DesktopAuthorizationSession? _desktopSession;
  final _desktopUrl = TextEditingController();
  Timer? _poller;

  @override
  void dispose() {
    _poller?.cancel();
    _desktopUrl.dispose();
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

  Future<void> _startDesktopAuthorization() async {
    if (_busy || _desktopSession != null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final session = await CrconApi.startDesktopAuthorization(
        _desktopUrl.text,
        deviceName: Platform.localHostname.isEmpty
            ? 'CRCON Windows app'
            : Platform.localHostname,
      );
      if (!mounted) return;
      setState(() => _desktopSession = session);
      _poller = Timer.periodic(session.interval, (_) => _exchangeDesktop());
      await _openDesktopBrowser();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openDesktopBrowser() async {
    final session = _desktopSession;
    if (session == null) return;
    final opened = await launchUrl(
      session.verificationUri,
      mode: LaunchMode.externalApplication,
    );
    if (!opened && mounted) {
      setState(
        () => _error = context.tr(
          'Browser konnte nicht geöffnet werden. Öffne die CRCON-Adresse manuell und gib den Gerätecode ein.',
          'The browser could not be opened. Open the CRCON address manually and enter the device code.',
        ),
      );
    }
  }

  Future<void> _exchangeDesktop() async {
    final session = _desktopSession;
    if (session == null || _busy) return;
    try {
      final profile = await CrconApi.exchangeDesktopAuthorization(
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

  Widget _desktopPairing(BuildContext context) {
    final session = _desktopSession;
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(
                    Icons.desktop_windows_outlined,
                    size: 48,
                    color: FrontlineTheme.gold,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    context.tr('Windows-App verbinden', 'Connect Windows app'),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 10),
                  Text(
                    session == null
                        ? context.tr(
                            'Gib die öffentliche HTTPS-Adresse deines CRCON ein. Anschließend öffnet sich der Browser zur sicheren Freigabe.',
                            'Enter the public HTTPS address of your CRCON. The browser will then open for secure approval.',
                          )
                        : context.tr(
                            'Bestätige diesen Code im CRCON-Browser mit deinem eigenen Konto. Die Windows-App verbindet sich danach automatisch.',
                            'Confirm this code in the CRCON browser with your own account. The Windows app will then connect automatically.',
                          ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  if (session == null) ...[
                    TextField(
                      controller: _desktopUrl,
                      keyboardType: TextInputType.url,
                      autofillHints: const [AutofillHints.url],
                      decoration: InputDecoration(
                        labelText: context.tr('CRCON-Adresse', 'CRCON address'),
                        hintText: 'https://crcon.example.org',
                        prefixIcon: const Icon(Icons.language_outlined),
                      ),
                      onSubmitted: (_) => _startDesktopAuthorization(),
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _busy ? null : _startDesktopAuthorization,
                      icon: const Icon(Icons.open_in_browser),
                      label: Text(
                        context.tr(
                          'Browser öffnen und verbinden',
                          'Open browser and connect',
                        ),
                      ),
                    ),
                  ] else ...[
                    Semantics(
                      label: context.tr('Gerätecode', 'Device code'),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 20),
                        decoration: BoxDecoration(
                          border: Border.all(color: FrontlineTheme.gold),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          session.userCode,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineMedium
                              ?.copyWith(
                                letterSpacing: 3,
                                color: FrontlineTheme.gold,
                                fontWeight: FontWeight.w700,
                              ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: () => Clipboard.setData(
                        ClipboardData(text: session.userCode),
                      ),
                      icon: const Icon(Icons.copy_outlined),
                      label: Text(context.tr('Code kopieren', 'Copy code')),
                    ),
                    const SizedBox(height: 8),
                    FilledButton.tonalIcon(
                      onPressed: _openDesktopBrowser,
                      icon: const Icon(Icons.open_in_browser),
                      label: Text(
                        context.tr(
                          'Browser erneut öffnen',
                          'Open browser again',
                        ),
                      ),
                    ),
                  ],
                  if (_error != null) ...[
                    const SizedBox(height: 16),
                    Text(
                      _error!,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(context.tr('CRCON koppeln', 'Pair CRCON')),
      actions: const [_LanguageButton()],
    ),
    body: Platform.isWindows
        ? _desktopPairing(context)
        : _session == null
        ? Stack(
            children: [
              MobileScanner(
                onDetect: (capture) {
                  final value = capture.barcodes.firstOrNull?.rawValue;
                  if (value != null) _scan(value);
                },
              ),
              Positioned(
                left: 16,
                right: 16,
                bottom: 24,
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const Icon(
                          Icons.qr_code_scanner,
                          color: FrontlineTheme.gold,
                          size: 32,
                        ),
                        const SizedBox(height: 10),
                        Text(
                          _error ??
                              context.tr(
                                'Öffne in CRCON die Mobile App, erstelle einen QR-Code und scanne ihn hier.',
                                'Open Mobile App in CRCON, create a QR code, then scan it here.',
                              ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          )
        : Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.phonelink_lock,
                        size: 46,
                        color: FrontlineTheme.gold,
                      ),
                      const SizedBox(height: 20),
                      Text(
                        context.tr(
                          'Vergleiche diesen Code mit CRCON',
                          'Compare this code with CRCON',
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        _session!.verificationCode,
                        style: Theme.of(context).textTheme.displayMedium
                            ?.copyWith(
                              letterSpacing: 8,
                              color: FrontlineTheme.gold,
                            ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        context.tr(
                          'Bestätige das Telefon im CRCON-Browser, um die Kopplung abzuschließen.',
                          'Approve the phone in the CRCON browser to finish pairing.',
                        ),
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
      servers[profile.id] = _listValue(bootstrap['servers'])
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
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

class _FrontlineBottomBar extends StatelessWidget {
  const _FrontlineBottomBar({required this.currentIndex});
  final int currentIndex;

  @override
  Widget build(BuildContext context) {
    final entries = <(IconData, String, String)>[
      (Icons.inbox_outlined, context.tr('Inbox', 'Inbox'), '/inbox'),
      (Icons.person_outline, context.tr('Spieler', 'Players'), '/players'),
      (Icons.more_horiz, context.tr('Mehr', 'More'), '/connections'),
    ];
    return SafeArea(
      top: false,
      child: Container(
        height: 74,
        decoration: BoxDecoration(
          color: FrontlineTheme.surface,
          border: Border(
            top: BorderSide(color: Theme.of(context).colorScheme.outline),
          ),
        ),
        child: Row(
          children: List.generate(entries.length, (index) {
            final entry = entries[index];
            final active = index == currentIndex;
            return Expanded(
              child: InkWell(
                onTap: active ? null : () => context.go(entry.$3),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    if (active)
                      const Align(
                        alignment: Alignment.topCenter,
                        child: SizedBox(
                          height: 2,
                          width: 88,
                          child: ColoredBox(color: FrontlineTheme.gold),
                        ),
                      ),
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          entry.$1,
                          color: active
                              ? FrontlineTheme.gold
                              : FrontlineTheme.muted,
                        ),
                        const SizedBox(height: 5),
                        Text(
                          entry.$2,
                          style: TextStyle(
                            color: active
                                ? FrontlineTheme.gold
                                : FrontlineTheme.muted,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }),
        ),
      ),
    );
  }
}

class InboxScreen extends ConsumerStatefulWidget {
  const InboxScreen({super.key});

  @override
  ConsumerState<InboxScreen> createState() => _InboxScreenState();
}

class _InboxScreenState extends ConsumerState<InboxScreen> {
  int? _serverNumber;

  List<AdminIncident> _filtered(List<AdminIncident> items) =>
      items.where((item) {
        if (_serverNumber != null && item.serverNumber != _serverNumber) {
          return false;
        }
        return true;
      }).toList();

  @override
  Widget build(BuildContext context) {
    final inbox = ref.watch(inboxProvider);

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 20,
        toolbarHeight: 54,
        title: Row(
          children: [
            Image.asset('assets/fln_logo.png', width: 20, height: 20),
            const SizedBox(width: 8),
            Text(
              context.tr('Leitstelle', 'Command center'),
              style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w500),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Tooltip(
              message: context.tr('Neuer Vorfall', 'New incident'),
              child: SizedBox(
                width: 42,
                height: 42,
                child: OutlinedButton(
                  onPressed: () => _createManualIncident(context, ref),
                  style: OutlinedButton.styleFrom(
                    padding: EdgeInsets.zero,
                    foregroundColor: FrontlineTheme.gold,
                    side: const BorderSide(color: FrontlineTheme.gold),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(5),
                    ),
                  ),
                  child: const Icon(Icons.add, size: 29),
                ),
              ),
            ),
          ),
          const SizedBox(width: 6),
          PopupMenuButton<String>(
            tooltip: context.tr('Weitere Bereiche', 'More areas'),
            onSelected: (value) {
              if (value == 'connections') context.push('/connections');
              if (value == 'diagnostics') context.push('/diagnostics');
              if (value == 'de' || value == 'en') {
                ref.read(localeProvider.notifier).state = Locale(value);
                unawaited(ref.read(secureStoreProvider).writeLanguage(value));
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'connections',
                child: Text(
                  context.tr('CRCON-Verbindungen', 'CRCON connections'),
                ),
              ),
              PopupMenuItem(
                value: 'diagnostics',
                child: Text(context.tr('Diagnoseprotokoll', 'Diagnostics log')),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem(value: 'de', child: Text('Deutsch')),
              const PopupMenuItem(value: 'en', child: Text('English')),
            ],
          ),
        ],
      ),
      bottomNavigationBar: const _FrontlineBottomBar(currentIndex: 0),
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(-.45, -.22),
            radius: 1.2,
            colors: [Color(0xff151911), FrontlineTheme.background],
          ),
        ),
        child: inbox.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => _ErrorView(message: error.toString()),
          data: (items) {
            final filtered = _filtered(items);
            final servers =
                items.map((incident) => incident.serverNumber).toSet().toList()
                  ..sort();
            final openCount = items
                .where(
                  (item) => !{'resolved', 'dismissed'}.contains(item.status),
                )
                .length;
            final claimedCount = items
                .where((item) => item.status == 'claimed')
                .length;
            return RefreshIndicator(
              onRefresh: () async => ref.refresh(inboxProvider.future),
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
                children: [
                  _serverSelector(context, servers),
                  const SizedBox(height: 22),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.circle,
                        color: FrontlineTheme.gold,
                        size: 10,
                      ),
                      const SizedBox(width: 10),
                      Text(
                        context.tr('$openCount offen', '$openCount open'),
                        style: const TextStyle(
                          fontSize: 17,
                          color: FrontlineTheme.chalk,
                        ),
                      ),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 10),
                        child: Text('·'),
                      ),
                      Text(
                        context.tr(
                          '$claimedCount übernommen',
                          '$claimedCount claimed',
                        ),
                        style: const TextStyle(
                          fontSize: 17,
                          color: FrontlineTheme.muted,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Divider(height: 1),
                  const SizedBox(height: 18),
                  if (filtered.isEmpty)
                    _InboxEmptyState(
                      message: items.isEmpty
                          ? context.tr('Keine Vorfälle.', 'No incidents.')
                          : context.tr(
                              'Keine Meldungen in diesem Filter.',
                              'No reports in this filter.',
                            ),
                    )
                  else
                    _IncidentList(items: filtered),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _serverSelector(BuildContext context, List<int> servers) =>
      PopupMenuButton<int?>(
        onSelected: (value) => setState(() => _serverNumber = value),
        itemBuilder: (context) => [
          PopupMenuItem<int?>(
            value: null,
            child: Text(context.tr('Alle Server', 'All servers')),
          ),
          ...servers.map(
            (server) => PopupMenuItem<int?>(
              value: server,
              child: Text(context.tr('Server $server', 'Server $server')),
            ),
          ),
        ],
        child: Container(
          height: 48,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xff25291e), FrontlineTheme.surfaceHigh],
            ),
            border: Border.all(color: Theme.of(context).colorScheme.outline),
            borderRadius: BorderRadius.circular(3),
          ),
          child: Row(
            children: [
              const Icon(Icons.dns_outlined, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _serverNumber == null
                      ? context.tr('Alle Server', 'All servers')
                      : context.tr(
                          'Server $_serverNumber',
                          'Server $_serverNumber',
                        ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const Icon(Icons.expand_more),
            ],
          ),
        ),
      );
}

class _OnlineBadge extends StatelessWidget {
  const _OnlineBadge({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    height: 48,
    padding: const EdgeInsets.symmetric(horizontal: 12),
    decoration: BoxDecoration(
      color: FrontlineTheme.surfaceHigh,
      border: Border.all(color: Theme.of(context).colorScheme.outline),
      borderRadius: BorderRadius.circular(3),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.circle, size: 10, color: FrontlineTheme.success),
        const SizedBox(width: 7),
        Text(label),
      ],
    ),
  );
}

class _IncidentList extends StatelessWidget {
  const _IncidentList({required this.items});
  final List<AdminIncident> items;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      for (var index = 0; index < items.length; index++) ...[
        _IncidentRow(item: items[index], featured: index == 0),
        if (index < items.length - 1) const SizedBox(height: 12),
      ],
    ],
  );
}

class _IncidentRow extends StatelessWidget {
  const _IncidentRow({required this.item, required this.featured});
  final AdminIncident item;
  final bool featured;

  @override
  Widget build(BuildContext context) {
    final primary = item.primarySubject;
    final isSquad = primary?.kind == 'squad';
    final targetName = primary == null
        ? context.tr('Allgemein', 'General')
        : isSquad
        ? context.squadName(primary.squadName ?? primary.displayName)
        : primary.displayName;
    final targetType = primary == null
        ? context.tr('Meldung', 'Report')
        : isSquad
        ? context.tr('Squad', 'Squad')
        : context.tr('Spieler', 'Player');
    final snapshotPlayers = primary?.snapshot['players'];
    final memberCount = snapshotPlayers is List ? snapshotPlayers.length : null;
    final facts = <(IconData, String)>[
      (
        Icons.dns_outlined,
        context.tr(
          'Server ${item.serverNumber}',
          'Server ${item.serverNumber}',
        ),
      ),
      if (isSquad)
        (
          Icons.groups_2_outlined,
          [
            if (primary?.team != null) context.teamName(primary?.team),
            if (primary?.squadType != null)
              context.squadTypeName(primary?.squadType),
          ].join(' · '),
        )
      else if (primary?.squadName != null)
        (Icons.gps_fixed, context.squadName(primary?.squadName)),
      if (isSquad && memberCount != null)
        (
          Icons.person_outline,
          context.tr(
            '$memberCount ${memberCount == 1 ? 'Mitglied' : 'Mitglieder'} aktiv',
            '$memberCount ${memberCount == 1 ? 'member' : 'members'} active',
          ),
        )
      else if (!isSquad && primary?.role != null)
        (Icons.military_tech_outlined, context.roleName(primary?.role)),
    ]..removeWhere((item) => item.$2.isEmpty);
    final reporter = item.reporterName ?? context.tr('manuell', 'manual');

    return InkWell(
      onTap: () => context.push('/incidents/${item.connectionId}/${item.id}'),
      child: Container(
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xff1b2017), FrontlineTheme.surface],
          ),
          border: Border.all(
            color: featured
                ? FrontlineTheme.gold
                : Theme.of(context).colorScheme.outline,
            width: featured ? 1.5 : 1,
          ),
          borderRadius: BorderRadius.circular(3),
        ),
        padding: const EdgeInsets.fromLTRB(13, 12, 12, 11),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _IncidentTargetGlyph(
              squad: isSquad,
              general: primary == null,
              accent: featured,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    targetType.toUpperCase(),
                    style: TextStyle(
                      color: featured
                          ? FrontlineTheme.gold
                          : FrontlineTheme.muted,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: .5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    targetName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 24,
                      height: 1.08,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (final fact in facts) ...[
                              Row(
                                children: [
                                  Icon(
                                    fact.$1,
                                    size: 16,
                                    color: FrontlineTheme.chalk,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      fact.$2,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: 13,
                                        height: 1.05,
                                        color: FrontlineTheme.chalk,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 2),
                            ],
                          ],
                        ),
                      ),
                      const Padding(
                        padding: EdgeInsets.only(top: 17),
                        child: Icon(
                          Icons.chevron_right,
                          size: 30,
                          color: FrontlineTheme.gold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  const Divider(height: 1),
                  const SizedBox(height: 8),
                  Text(
                    _incidentExcerpt(item, primary),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 15, height: 1.35),
                  ),
                  const SizedBox(height: 8),
                  const Divider(height: 1),
                  const SizedBox(height: 7),
                  RichText(
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    text: TextSpan(
                      style: const TextStyle(
                        color: FrontlineTheme.muted,
                        fontSize: 13,
                      ),
                      children: [
                        TextSpan(
                          text: context.tr('gemeldet von ', 'reported by '),
                        ),
                        TextSpan(
                          text: reporter,
                          style: const TextStyle(color: FrontlineTheme.gold),
                        ),
                        TextSpan(
                          text:
                              ' · ${_relativeIncidentTime(context, item.createdAt)}',
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _IncidentTargetGlyph extends StatelessWidget {
  const _IncidentTargetGlyph({
    required this.squad,
    required this.general,
    required this.accent,
  });
  final bool squad;
  final bool general;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final color = accent ? FrontlineTheme.gold : FrontlineTheme.chalk;
    return SizedBox(
      width: 62,
      height: 78,
      child: Center(
        child: CustomPaint(
          size: const Size.square(58),
          painter: _IncidentTargetGlyphPainter(
            color: color,
            squad: squad,
            general: general,
          ),
        ),
      ),
    );
  }
}

class _IncidentTargetGlyphPainter extends CustomPainter {
  const _IncidentTargetGlyphPainter({
    required this.color,
    required this.squad,
    required this.general,
  });

  final Color color;
  final bool squad;
  final bool general;

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.65
      ..strokeCap = StrokeCap.square
      ..strokeJoin = StrokeJoin.miter
      ..isAntiAlias = true;
    final center = Offset(size.width / 2, size.height / 2);
    const inset = 4.5;
    const corner = 13.5;

    final corners = Path()
      ..moveTo(inset, inset + corner)
      ..lineTo(inset, inset)
      ..lineTo(inset + corner, inset)
      ..moveTo(size.width - inset - corner, inset)
      ..lineTo(size.width - inset, inset)
      ..lineTo(size.width - inset, inset + corner)
      ..moveTo(inset, size.height - inset - corner)
      ..lineTo(inset, size.height - inset)
      ..lineTo(inset + corner, size.height - inset)
      ..moveTo(size.width - inset - corner, size.height - inset)
      ..lineTo(size.width - inset, size.height - inset)
      ..lineTo(size.width - inset, size.height - inset - corner);
    canvas.drawPath(corners, stroke);

    if (squad) {
      _paintSquad(canvas, center, stroke);
    } else if (general) {
      _paintReport(canvas, center, stroke);
    } else {
      _paintPlayer(canvas, center, stroke);
    }
  }

  void _paintSquad(Canvas canvas, Offset center, Paint stroke) {
    canvas.drawCircle(center, 11.5, stroke);
    canvas.drawLine(
      Offset(center.dx - 17, center.dy),
      Offset(center.dx + 17, center.dy),
      stroke,
    );
    canvas.drawLine(
      Offset(center.dx, center.dy - 17),
      Offset(center.dx, center.dy + 17),
      stroke,
    );
    final dot = Paint()
      ..color = color
      ..style = PaintingStyle.fill
      ..isAntiAlias = true;
    canvas.drawCircle(center, 3.25, dot);
  }

  void _paintPlayer(Canvas canvas, Offset center, Paint stroke) {
    canvas.drawCircle(Offset(center.dx, center.dy - 9), 6.2, stroke);
    final shoulders = Path()
      ..moveTo(center.dx - 13, center.dy + 14)
      ..quadraticBezierTo(
        center.dx - 12,
        center.dy + 2,
        center.dx,
        center.dy + 2,
      )
      ..quadraticBezierTo(
        center.dx + 12,
        center.dy + 2,
        center.dx + 13,
        center.dy + 14,
      )
      ..lineTo(center.dx + 13, center.dy + 17)
      ..lineTo(center.dx - 13, center.dy + 17)
      ..close();
    canvas.drawPath(shoulders, stroke);
  }

  void _paintReport(Canvas canvas, Offset center, Paint stroke) {
    final flag = Path()
      ..moveTo(center.dx - 10, center.dy + 15)
      ..lineTo(center.dx - 10, center.dy - 15)
      ..lineTo(center.dx + 12, center.dy - 11)
      ..lineTo(center.dx + 5, center.dy)
      ..lineTo(center.dx + 12, center.dy + 7)
      ..lineTo(center.dx - 10, center.dy + 5);
    canvas.drawPath(flag, stroke);
  }

  @override
  bool shouldRepaint(_IncidentTargetGlyphPainter oldDelegate) =>
      oldDelegate.color != color ||
      oldDelegate.squad != squad ||
      oldDelegate.general != general;
}

class _InboxEmptyState extends StatelessWidget {
  const _InboxEmptyState({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 80),
    decoration: BoxDecoration(
      color: FrontlineTheme.surface,
      border: Border.all(color: Theme.of(context).colorScheme.outline),
      borderRadius: BorderRadius.circular(3),
    ),
    child: Center(child: Text(message, textAlign: TextAlign.center)),
  );
}

String _incidentExcerpt(AdminIncident incident, IncidentSubject? primary) {
  var text = (incident.rawMessage ?? incident.reason).trim();
  text = text
      .replaceFirst(RegExp(r'^!admin\b', caseSensitive: false), '')
      .trim();
  final target = primary == null
      ? ''
      : primary.kind == 'squad'
      ? primary.squadName ?? primary.displayName
      : primary.displayName;
  if (target.isNotEmpty) {
    text = text
        .replaceFirst(
          RegExp('^${RegExp.escape(target)}\\b', caseSensitive: false),
          '',
        )
        .trim();
  }
  return text.isEmpty ? incident.reason : text;
}

class _ContextChip extends StatelessWidget {
  const _ContextChip({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
    decoration: BoxDecoration(
      color: FrontlineTheme.surfaceHigh,
      border: Border.all(color: Theme.of(context).colorScheme.outline),
      borderRadius: BorderRadius.circular(5),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 15, color: FrontlineTheme.chalk),
        const SizedBox(width: 5),
        Text(label),
      ],
    ),
  );
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
  List<Map<String, dynamic>> _servers = const [];
  List<Map<String, dynamic>> _livePlayers = const [];
  List<Map<String, dynamic>> _results = const [];
  String? _error;
  bool _busy = false;
  bool _loaded = false;
  bool _showAll = false;

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  Future<void> _search(List<ConnectionProfile> profiles) async {
    final term = _query.text.trim();
    if (_busy || profiles.isEmpty) return;
    if (term.isEmpty) {
      setState(() => _results = const []);
      return;
    }
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
      final availableServers = _listValue(bootstrap['servers'])
          .map(_mapValue)
          .map((server) => (server['server_number'] as num?)?.toInt())
          .whereType<int>()
          .toList();
      final fallback = (bootstrap['server_number'] as num?)?.toInt();
      final targetServers = _serverNumber == null
          ? (availableServers.isEmpty && fallback != null
                ? [fallback]
                : availableServers)
          : [_serverNumber!];
      final groupedResults = await Future.wait(
        targetServers.map(
          (serverNumber) async => (await api.searchPlayers(
            term,
            serverNumber: serverNumber,
          )).map((player) => {...player, 'server_number': serverNumber}),
        ),
      );
      final unique = <String, Map<String, dynamic>>{};
      for (final player in groupedResults.expand((players) => players)) {
        final key =
            '${player['server_number']}:${player['player_id'] ?? player['name'] ?? player['player_name']}';
        unique[key] = player;
      }
      if (mounted) setState(() => _results = unique.values.toList());
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _loadDirectory(List<ConnectionProfile> profiles) async {
    if (_busy || profiles.isEmpty) return;
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
      final servers = _listValue(bootstrap['servers'])
          .map(_mapValue)
          .where((server) => server['server_number'] is num)
          .toList();
      final fallback = (bootstrap['server_number'] as num?)?.toInt();
      final effectiveServers = servers.isEmpty && fallback != null
          ? [
              <String, dynamic>{'server_number': fallback},
            ]
          : servers;
      final selectedServers = _serverNumber == null
          ? effectiveServers
          : effectiveServers.where(
              (server) =>
                  (server['server_number'] as num?)?.toInt() == _serverNumber,
            );
      final rosters = await Future.wait(
        selectedServers.map((server) async {
          final serverNumber = (server['server_number'] as num).toInt();
          final roster = await api.roster(serverNumber);
          return _playersFromRoster(roster, serverNumber);
        }),
      );
      if (!mounted) return;
      setState(() {
        _servers = effectiveServers;
        _livePlayers = rosters.expand((players) => players).toList()
          ..sort(
            (left, right) => (left['name']?.toString() ?? '').compareTo(
              right['name']?.toString() ?? '',
            ),
          );
        _loaded = true;
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = error.toString();
          _loaded = true;
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  List<Map<String, dynamic>> _playersFromRoster(
    Map<String, dynamic> roster,
    int serverNumber,
  ) {
    final players = <Map<String, dynamic>>[];
    final teams = _mapValue(roster['teams']);
    for (final entry in teams.entries) {
      if (entry.key == 'fail_count') continue;
      final team = _mapValue(entry.value);
      final commander = _nullableMapValue(team['commander']);
      if (commander != null) {
        players.add({
          ...commander,
          'server_number': serverNumber,
          'team': commander['team'] ?? entry.key,
          'role': commander['role'] ?? 'commander',
        });
      }
      final squads = _mapValue(team['squads']);
      for (final squadEntry in squads.entries) {
        final squad = _mapValue(squadEntry.value);
        for (final value in _listValue(squad['players'])) {
          final player = _mapValue(value);
          final playerId = player['player_id']?.toString() ?? '';
          if (playerId.isEmpty) continue;
          players.add({
            ...player,
            'server_number': serverNumber,
            'team': player['team'] ?? entry.key,
            'unit_name': player['unit_name'] ?? squadEntry.key,
            'squad_type': player['squad_type'] ?? squad['type'],
          });
        }
      }
    }
    return players;
  }

  Future<void> _chooseServer(List<ConnectionProfile> profiles) async {
    final choices = [
      <String, dynamic>{
        'server_number': null,
        'name': context.tr('Alle Server', 'All servers'),
      },
      ..._servers,
    ];
    final result = await showModalBottomSheet<int?>(
      context: context,
      backgroundColor: FrontlineTheme.surface,
      builder: (sheetContext) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: choices.map((server) {
            final value = (server['server_number'] as num?)?.toInt();
            final selected = value == _serverNumber;
            return ListTile(
              leading: Icon(
                value == null ? Icons.dns_outlined : Icons.storage_outlined,
                color: selected ? FrontlineTheme.gold : FrontlineTheme.chalk,
              ),
              title: Text(
                value == null
                    ? context.tr('Alle Server', 'All servers')
                    : '${context.tr('Server', 'Server')} $value',
              ),
              trailing: selected
                  ? const Icon(Icons.check, color: FrontlineTheme.gold)
                  : null,
              onTap: () => Navigator.pop(sheetContext, value),
            );
          }).toList(),
        ),
      ),
    );
    if (!mounted || result == _serverNumber) return;
    setState(() {
      _serverNumber = result;
      _results = const [];
    });
    await _loadDirectory(profiles);
  }

  List<Map<String, dynamic>> _visiblePlayers() {
    final query = _query.text.trim().toLowerCase();
    final source = _results.isNotEmpty || query.isNotEmpty
        ? _results
        : _livePlayers;
    return source.where((player) {
      final isOnline = player['online'] != false;
      if (!_showAll && !isOnline) return false;
      if (query.isEmpty || _results.isNotEmpty) return true;
      return '${player['name'] ?? player['player_name'] ?? ''} ${player['player_id'] ?? ''}'
          .toLowerCase()
          .contains(query);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final profiles = ref.watch(connectionsProvider);
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 20,
        toolbarHeight: 54,
        title: Row(
          children: [
            Image.asset('assets/fln_logo.png', width: 20, height: 20),
            const SizedBox(width: 8),
            Text(
              context.tr('Spieler', 'Players'),
              style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w500),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: context.tr('Aktualisieren', 'Refresh'),
            onPressed: _busy
                ? null
                : () => _loadDirectory(
                    ref.read(connectionsProvider).valueOrNull ?? const [],
                  ),
            icon: const Icon(Icons.refresh),
          ),
          const _LanguageButton(),
        ],
      ),
      bottomNavigationBar: const _FrontlineBottomBar(currentIndex: 1),
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
          if (!_loaded && !_busy) {
            WidgetsBinding.instance.addPostFrameCallback(
              (_) => _loadDirectory(items),
            );
          }
          final players = _visiblePlayers();
          final activeServerLabel = _serverNumber == null
              ? context.tr('Alle Server', 'All servers')
              : '${context.tr('Server', 'Server')} $_serverNumber';
          return LayoutBuilder(
            builder: (context, constraints) => Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: ListView(
                  padding: EdgeInsets.fromLTRB(
                    constraints.maxWidth < 420 ? 16 : 20,
                    8,
                    constraints.maxWidth < 420 ? 16 : 20,
                    18,
                  ),
                  children: [
                    OutlinedButton.icon(
                      onPressed: _busy ? null : () => _chooseServer(items),
                      icon: const Icon(Icons.dns_outlined),
                      label: Align(
                        alignment: Alignment.centerLeft,
                        child: Text(activeServerLabel),
                      ),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size.fromHeight(62),
                        foregroundColor: FrontlineTheme.chalk,
                        side: const BorderSide(color: Color(0xff5d5d4c)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _query,
                      onChanged: (_) => setState(() {
                        if (_query.text.trim().isEmpty) _results = const [];
                      }),
                      decoration: InputDecoration(
                        hintText: context.tr(
                          'Spielername oder Steam-ID suchen',
                          'Search player name or Steam ID',
                        ),
                        prefixIcon: const Icon(Icons.search),
                        suffixIcon: IconButton(
                          onPressed: () => _search(items),
                          icon: const Icon(Icons.arrow_forward),
                          tooltip: context.tr('Suchen', 'Search'),
                        ),
                      ),
                      textInputAction: TextInputAction.search,
                      onSubmitted: (_) => _search(items),
                    ),
                    if (_busy) ...[
                      const SizedBox(height: 10),
                      const LinearProgressIndicator(),
                    ],
                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      _ErrorView(message: _error!),
                    ],
                    const SizedBox(height: 20),
                    Wrap(
                      alignment: WrapAlignment.spaceBetween,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        Text(
                          _results.isNotEmpty
                              ? context.tr('Suchergebnisse', 'Search results')
                              : context.tr(
                                  'Spieler im Einsatz',
                                  'Players in action',
                                ),
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            TextButton(
                              onPressed: () => setState(() => _showAll = false),
                              style: TextButton.styleFrom(
                                foregroundColor: !_showAll
                                    ? FrontlineTheme.gold
                                    : FrontlineTheme.muted,
                              ),
                              child: Text(context.tr('Online', 'Online')),
                            ),
                            TextButton(
                              onPressed: () => setState(() => _showAll = true),
                              style: TextButton.styleFrom(
                                foregroundColor: _showAll
                                    ? FrontlineTheme.gold
                                    : FrontlineTheme.muted,
                              ),
                              child: Text(context.tr('Alle', 'All')),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    if (_loaded && players.isEmpty)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 28),
                        child: Center(
                          child: Text(
                            context.tr(
                              'Keine Spieler gefunden.',
                              'No players found.',
                            ),
                            style: const TextStyle(color: FrontlineTheme.muted),
                          ),
                        ),
                      ),
                    ...players.map(
                      (player) => PlayerDirectoryRow(
                        player: player,
                        onTap: () {
                          final playerId =
                              player['player_id']?.toString() ?? '';
                          if (playerId.isEmpty) return;
                          final server =
                              (player['server_number'] as num?)?.toInt() ??
                              _serverNumber;
                          context.push(
                            '/players/$_connectionId/$playerId?server_number=${server ?? ''}',
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class PlayerDirectoryRow extends StatelessWidget {
  const PlayerDirectoryRow({
    super.key,
    required this.player,
    required this.onTap,
  });
  final Map<String, dynamic> player;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final playerId = player['player_id']?.toString() ?? '';
    final name =
        player['name']?.toString() ??
        player['player_name']?.toString() ??
        context.tr('Unbekannt', 'Unknown');
    final serverNumber = (player['server_number'] as num?)?.toInt();
    final online = player['online'] != false;
    final role = player['role']?.toString();
    final isLeader = _isSquadLeader(role);
    final details = [
      if (serverNumber != null)
        '${context.tr('Server', 'Server')} $serverNumber',
      context.teamName(player['team']?.toString()),
      context.squadName(player['unit_name']?.toString()),
      context.roleName(role),
    ].where((value) => value != '—').join(' · ');
    return InkWell(
      onTap: playerId.isEmpty ? null : onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 15),
        decoration: const BoxDecoration(
          color: FrontlineTheme.surface,
          border: Border(bottom: BorderSide(color: Color(0xff48493b))),
        ),
        child: Row(
          children: [
            Container(
              width: 43,
              height: 43,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                border: Border.all(color: const Color(0xff7d7960)),
              ),
              child: Icon(
                isLeader ? Icons.shield_outlined : Icons.person_outline,
                color: FrontlineTheme.chalk,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      if (online) ...[
                        const Icon(
                          Icons.circle,
                          size: 9,
                          color: FrontlineTheme.success,
                        ),
                        const SizedBox(width: 7),
                      ],
                      Expanded(
                        child: Text(
                          name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    details,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: FrontlineTheme.muted),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: FrontlineTheme.muted),
          ],
        ),
      ),
    );
  }
}

class PlayerIncidentContext {
  const PlayerIncidentContext({
    required this.incidentId,
    required this.subjectId,
    required this.subjectState,
    required this.serverNumber,
    required this.report,
    required this.reporterName,
    required this.reportedAt,
    required this.canRunActions,
  });

  final String incidentId;
  final String subjectId;
  final String subjectState;
  final int serverNumber;
  final String report;
  final String? reporterName;
  final DateTime? reportedAt;
  final bool canRunActions;
}

class PlayerProfileScreen extends ConsumerWidget {
  const PlayerProfileScreen({
    super.key,
    required this.connectionId,
    required this.playerId,
    this.serverNumber,
    this.incidentContext,
  });

  final String connectionId;
  final String playerId;
  final int? serverNumber;
  final PlayerIncidentContext? incidentContext;

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
    appBar: AppBar(
      title: Row(
        children: [
          Image.asset('assets/fln_logo.png', width: 23, height: 23),
          const SizedBox(width: 9),
          Text(context.tr('Spielerprofil', 'Player profile')),
        ],
      ),
      actions: const [_LanguageButton()],
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
        return PlayerProfileDossier(
          dossier: snapshot.data!,
          playerId: playerId,
          incidentContext: incidentContext,
          connectionId: connectionId,
          serverNumber: serverNumber,
        );
      },
    ),
    bottomNavigationBar: _PlayerProfileActionBar(
      incidentContext: incidentContext,
      connectionId: connectionId,
      playerId: playerId,
    ),
  );
}

class PlayerProfileDossier extends StatelessWidget {
  const PlayerProfileDossier({
    super.key,
    required this.dossier,
    required this.playerId,
    required this.incidentContext,
    this.connectionId = '',
    this.serverNumber,
  });

  final Map<String, dynamic> dossier;
  final String playerId;
  final PlayerIncidentContext? incidentContext;
  final String connectionId;
  final int? serverNumber;

  @override
  Widget build(BuildContext context) {
    final history = _mapValue(dossier['history']);
    final live = _nullableMapValue(dossier['live']);
    final soldier = _mapValue(history['soldier']);
    final identifiers = _mapValue(dossier['identifiers']);
    final name = _playerProfileName(history, live, soldier, context);
    final kills = _profileFirstValue(live ?? const {}, ['kills', 'kill_count']);
    final deaths = _profileFirstValue(live ?? const {}, [
      'deaths',
      'death_count',
    ]);
    final teamkills = _profileFirstValue(live ?? const {}, [
      'teamkills',
      'team_kills',
    ]);
    final actions = _listValue(history['received_actions']);
    final bans = _listValue(history['bans']);
    final flags = _listValue(history['flags']);
    final comments = _listValue(history['comments']);
    final sessions = _listValue(history['sessions']);
    final capabilities = _mapValue(dossier['capabilities']);

    return LayoutBuilder(
      builder: (context, constraints) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: ListView(
            padding: EdgeInsets.fromLTRB(
              constraints.maxWidth < 420 ? 14 : 20,
              16,
              constraints.maxWidth < 420 ? 14 : 20,
              106,
            ),
            children: [
              _PlayerIdentityHeader(name: name, live: live, soldier: soldier),
              if (incidentContext != null) ...[
                const SizedBox(height: 14),
                _PlayerIncidentReport(context: incidentContext!),
              ],
              if (capabilities['watch_view'] == true ||
                  capabilities['watch_add'] == true ||
                  capabilities['watch_remove'] == true) ...[
                const SizedBox(height: 14),
                _PlayerWatchCard(
                  connectionId: connectionId,
                  playerId: playerId,
                  playerName: name,
                  serverNumber: serverNumber,
                  incidentId: incidentContext?.incidentId,
                  watch: _nullableMapValue(history['watchlist']),
                  capabilities: capabilities,
                ),
              ],
              if (incidentContext != null &&
                  capabilities['incident_context'] == true) ...[
                const SizedBox(height: 14),
                _PlayerContextExcerpt(
                  connectionId: connectionId,
                  incidentId: incidentContext!.incidentId,
                  playerId: playerId,
                ),
              ],
              const SizedBox(height: 14),
              _PlayerProfileStats(
                kills: kills,
                deaths: deaths,
                teamkills: teamkills,
              ),
              const SizedBox(height: 14),
              _PlayerActivityTimeline(
                incidentContext: incidentContext,
                actions: actions,
                sessions: sessions,
                playerName: name,
              ),
              const SizedBox(height: 14),
              _PlayerIdentifiers(
                steamId: identifiers['steam_id']?.toString(),
                eosId: identifiers['eos_id']?.toString(),
                platformPlayerId: identifiers['platform_player_id']?.toString(),
                fallbackPlayerId: dossier['player_id']?.toString() ?? playerId,
              ),
              if (flags.isNotEmpty ||
                  bans.isNotEmpty ||
                  comments.isNotEmpty) ...[
                const SizedBox(height: 14),
                _PlayerAdminSummary(
                  flags: flags,
                  bans: bans,
                  comments: comments,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _PlayerWatchCard extends ConsumerStatefulWidget {
  const _PlayerWatchCard({
    required this.connectionId,
    required this.playerId,
    required this.playerName,
    required this.serverNumber,
    required this.incidentId,
    required this.watch,
    required this.capabilities,
  });

  final String connectionId;
  final String playerId;
  final String playerName;
  final int? serverNumber;
  final String? incidentId;
  final Map<String, dynamic>? watch;
  final Map<String, dynamic> capabilities;

  @override
  ConsumerState<_PlayerWatchCard> createState() => _PlayerWatchCardState();
}

class _PlayerWatchCardState extends ConsumerState<_PlayerWatchCard> {
  bool _busy = false;
  late Map<String, dynamic>? _watch = widget.watch;

  Future<CrconApi> _api() async {
    final profiles = await ref.read(connectionsProvider.future);
    final profile = profiles.firstWhere(
      (item) => item.id == widget.connectionId,
    );
    return CrconApi(profile, ref.read(secureStoreProvider));
  }

  Future<void> _watchPlayer() async {
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => _TextInputDialog(
        title: context.tr('Spieler beobachten', 'Watch player'),
        label: context.tr('Pflichtgrund', 'Required reason'),
        confirmLabel: context.tr('Beobachten', 'Watch'),
        maxLines: 3,
      ),
    );
    if (reason == null || reason.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await (await _api()).watchPlayer(
        widget.playerId,
        reason: reason.trim(),
        playerName: widget.playerName,
        serverNumber: widget.serverNumber,
        incidentId: widget.incidentId,
      );
      if (mounted) {
        setState(() {
          _watch = {
            'reason': reason.trim(),
            'by': null,
            'modified': DateTime.now().toIso8601String(),
            'count': 0,
            'is_watched': true,
          };
        });
      }
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

  Future<void> _unwatchPlayer() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(context.tr('Beobachtung beenden?', 'End watch?')),
        content: Text(
          context.tr(
            'Der Spieler wird aus der CRCON-Watchlist entfernt.',
            'The player will be removed from CRCON\'s watchlist.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.tr('Abbrechen', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.tr('Beenden', 'End watch')),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busy = true);
    try {
      await (await _api()).unwatchPlayer(
        widget.playerId,
        serverNumber: widget.serverNumber,
        incidentId: widget.incidentId,
      );
      if (mounted) setState(() => _watch = null);
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
  Widget build(BuildContext context) {
    final watched = _watch?['is_watched'] == true;
    final canAdd = widget.capabilities['watch_add'] == true;
    final canRemove = widget.capabilities['watch_remove'] == true;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  watched ? Icons.visibility : Icons.visibility_off_outlined,
                  color: watched
                      ? FrontlineTheme.success
                      : FrontlineTheme.muted,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    context.tr('Beobachtung', 'Watch'),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                Text(
                  watched
                      ? context.tr('aktiv', 'active')
                      : context.tr('inaktiv', 'inactive'),
                  style: TextStyle(
                    color: watched
                        ? FrontlineTheme.success
                        : FrontlineTheme.muted,
                  ),
                ),
              ],
            ),
            if (watched) ...[
              const SizedBox(height: 10),
              Text(_watch?['reason']?.toString() ?? '—'),
              const SizedBox(height: 4),
              Text(
                [
                  if (_watch?['by'] != null)
                    '${context.tr('gesetzt von', 'set by')} ${_watch?['by']}',
                  if (_watch?['modified'] != null)
                    _watch?['modified'].toString(),
                  '${_watch?['count'] ?? 0} ${context.tr('Sichtungen', 'sightings')}',
                ].join(' · '),
                style: const TextStyle(color: FrontlineTheme.muted),
              ),
            ],
            const SizedBox(height: 12),
            if (!watched && canAdd)
              OutlinedButton.icon(
                onPressed: _busy ? null : _watchPlayer,
                icon: const Icon(Icons.visibility_outlined),
                label: Text(context.tr('Beobachten', 'Watch')),
              ),
            if (watched && canRemove)
              OutlinedButton.icon(
                onPressed: _busy ? null : _unwatchPlayer,
                icon: const Icon(Icons.visibility_off_outlined),
                label: Text(context.tr('Beobachtung beenden', 'End watch')),
              ),
          ],
        ),
      ),
    );
  }
}

class _PlayerContextExcerpt extends ConsumerWidget {
  const _PlayerContextExcerpt({
    required this.connectionId,
    required this.incidentId,
    required this.playerId,
  });
  final String connectionId;
  final String incidentId;
  final String playerId;

  @override
  Widget build(BuildContext context, WidgetRef ref) =>
      FutureBuilder<Map<String, dynamic>>(
        future: () async {
          final profiles = await ref.read(connectionsProvider.future);
          final profile = profiles.firstWhere(
            (item) => item.id == connectionId,
          );
          return CrconApi(
            profile,
            ref.read(secureStoreProvider),
          ).playerContext(incidentId, playerId);
        }(),
        builder: (context, snapshot) {
          if (snapshot.hasError || !snapshot.hasData) {
            return const SizedBox.shrink();
          }
          final events = _listValue(
            snapshot.data!['events'],
          ).map(_mapValue).toList();
          if (events.isEmpty) return const SizedBox.shrink();
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.tr('Ereignisse zum Vorfall', 'Incident events'),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  ...events.map(
                    (event) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: Icon(_eventIcon(event['type']?.toString())),
                      title: Text(_eventLabel(context, event)),
                      subtitle: Text(
                        event['message']?.toString() ??
                            event['occurred_at']?.toString() ??
                            '',
                      ),
                    ),
                  ),
                  if ((snapshot.data!['total'] as num? ?? events.length) >
                      events.length)
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => _openAll(context, ref),
                        child: Text(context.tr('Alle anzeigen', 'Show all')),
                      ),
                    ),
                ],
              ),
            ),
          );
        },
      );

  void _openAll(BuildContext context, WidgetRef ref) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => FutureBuilder<Map<String, dynamic>>(
        future: () async {
          final profiles = await ref.read(connectionsProvider.future);
          final profile = profiles.firstWhere(
            (item) => item.id == connectionId,
          );
          return CrconApi(
            profile,
            ref.read(secureStoreProvider),
          ).playerContext(incidentId, playerId, limit: 50);
        }(),
        builder: (context, snapshot) => SafeArea(
          child: SizedBox(
            height: MediaQuery.sizeOf(context).height * .72,
            child: snapshot.hasData
                ? ListView(
                    children: [
                      for (final value in _listValue(
                        snapshot.data!['events'],
                      ).map(_mapValue))
                        ListTile(
                          leading: Icon(_eventIcon(value['type']?.toString())),
                          title: Text(_eventLabel(context, value)),
                          subtitle: Text(
                            value['message']?.toString() ??
                                value['occurred_at']?.toString() ??
                                '',
                          ),
                        ),
                    ],
                  )
                : const Center(child: CircularProgressIndicator()),
          ),
        ),
      ),
    );
  }
}

IconData _eventIcon(String? value) => switch (value) {
  'chat' => Icons.chat_bubble_outline,
  'kill' => Icons.gps_fixed,
  'teamkill' => Icons.warning_amber_outlined,
  'join' => Icons.login,
  'leave' => Icons.logout,
  _ => Icons.history,
};

String _eventLabel(BuildContext context, Map<String, dynamic> event) {
  final actor =
      event['actor_name']?.toString() ?? context.tr('Spieler', 'Player');
  final other = event['other_name']?.toString();
  return switch (event['type']?.toString()) {
    'chat' => context.tr(
      '$actor schrieb im Chat',
      '$actor sent a chat message',
    ),
    'kill' =>
      other == null
          ? context.tr('$actor tötete einen Spieler', '$actor killed a player')
          : context.tr('$actor tötete $other', '$actor killed $other'),
    'teamkill' =>
      other == null
          ? context.tr(
              '$actor teamkillte einen Spieler',
              '$actor teamkilled a player',
            )
          : context.tr('$actor teamkillte $other', '$actor teamkilled $other'),
    'join' => context.tr('$actor ist beigetreten', '$actor joined'),
    'leave' => context.tr(
      '$actor hat den Server verlassen',
      '$actor left the server',
    ),
    _ => context.tr('Ereignis', 'Event'),
  };
}

class _PlayerIdentityHeader extends StatelessWidget {
  const _PlayerIdentityHeader({
    required this.name,
    required this.live,
    required this.soldier,
  });

  final String name;
  final Map<String, dynamic>? live;
  final Map<String, dynamic> soldier;

  @override
  Widget build(BuildContext context) {
    final squad =
        live?['unit_name']?.toString() ?? live?['squad_name']?.toString();
    final role = live?['role']?.toString();
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: FrontlineTheme.surface,
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 78,
            height: 78,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: FrontlineTheme.surfaceHigh,
              border: Border.all(color: const Color(0xff555647)),
              borderRadius: BorderRadius.circular(2),
            ),
            child: const Icon(Icons.person_outline, size: 45),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 30,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(
                      Icons.circle,
                      color: live == null
                          ? FrontlineTheme.muted
                          : FrontlineTheme.success,
                      size: 12,
                    ),
                    const SizedBox(width: 7),
                    Text(
                      live == null
                          ? context.tr('Offline', 'Offline')
                          : context.tr('Online', 'Online'),
                      style: TextStyle(
                        color: live == null
                            ? FrontlineTheme.muted
                            : FrontlineTheme.success,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _ProfileFact(
                  icon: Icons.dns_outlined,
                  text: 'Server ${live?['server_number'] ?? '—'}',
                ),
                if (live?['team'] != null) ...[
                  const SizedBox(height: 5),
                  _ProfileFact(
                    icon: Icons.flag_outlined,
                    text: context.teamName(live!['team']?.toString()),
                  ),
                ],
                if (squad != null && squad.isNotEmpty) ...[
                  const SizedBox(height: 5),
                  _ProfileFact(
                    icon: Icons.gps_fixed,
                    text: context.squadName(squad),
                  ),
                ],
                if (role != null && role.isNotEmpty) ...[
                  const SizedBox(height: 5),
                  _ProfileFact(
                    icon: Icons.military_tech_outlined,
                    text: context.roleName(role),
                  ),
                ] else if (soldier['level'] != null) ...[
                  const SizedBox(height: 5),
                  _ProfileFact(
                    icon: Icons.military_tech_outlined,
                    text: '${context.tr('Level', 'Level')} ${soldier['level']}',
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileFact extends StatelessWidget {
  const _ProfileFact({required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) => Row(
    children: [
      Icon(icon, size: 18, color: FrontlineTheme.chalk),
      const SizedBox(width: 8),
      Expanded(child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis)),
    ],
  );
}

class _PlayerIncidentReport extends StatelessWidget {
  const _PlayerIncidentReport({required this.context});
  final PlayerIncidentContext context;
  @override
  Widget build(BuildContext buildContext) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: const Color(0xff1c1e16),
      border: Border.all(color: FrontlineTheme.gold, width: 1.5),
      borderRadius: BorderRadius.circular(3),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(
          Icons.warning_amber_rounded,
          color: FrontlineTheme.gold,
          size: 33,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                buildContext.tr('Meldung', 'Report').toUpperCase(),
                style: const TextStyle(
                  color: FrontlineTheme.gold,
                  letterSpacing: .5,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                context.report,
                style: const TextStyle(fontSize: 19, height: 1.25),
              ),
              const SizedBox(height: 10),
              Text.rich(
                TextSpan(
                  style: const TextStyle(color: FrontlineTheme.muted),
                  children: [
                    TextSpan(
                      text: buildContext.tr('gemeldet von ', 'reported by '),
                    ),
                    TextSpan(
                      text:
                          context.reporterName ??
                          buildContext.tr('unbekannt', 'unknown'),
                      style: const TextStyle(color: FrontlineTheme.gold),
                    ),
                    TextSpan(
                      text:
                          ' · ${_relativeProfileTime(buildContext, context.reportedAt)}',
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _PlayerProfileStats extends StatelessWidget {
  const _PlayerProfileStats({
    required this.kills,
    required this.deaths,
    required this.teamkills,
  });
  final Object? kills;
  final Object? deaths;
  final Object? teamkills;

  @override
  Widget build(BuildContext context) {
    final values = <(String, String, IconData, Color)>[
      (
        context.tr('Kills', 'Kills'),
        _profileNumberText(kills),
        Icons.gps_fixed,
        FrontlineTheme.gold,
      ),
      (
        context.tr('Tode', 'Deaths'),
        _profileNumberText(deaths),
        Icons.close,
        FrontlineTheme.chalk,
      ),
      (
        context.tr('Teamkills', 'Teamkills'),
        _profileNumberText(teamkills),
        Icons.groups_2_outlined,
        (_profileNumber(teamkills) ?? 0) > 0
            ? FrontlineTheme.warning
            : FrontlineTheme.chalk,
      ),
    ];
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14),
      decoration: BoxDecoration(
        color: FrontlineTheme.surface,
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Row(
        children: [
          for (var index = 0; index < values.length; index++)
            Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                decoration: BoxDecoration(
                  border: index == 0
                      ? null
                      : const Border(
                          left: BorderSide(color: Color(0xff414337)),
                        ),
                ),
                child: Column(
                  children: [
                    Icon(values[index].$3, size: 23, color: values[index].$4),
                    const SizedBox(height: 7),
                    Text(
                      values[index].$2,
                      style: TextStyle(
                        fontSize: 25,
                        fontWeight: FontWeight.w700,
                        color: values[index].$4,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      values[index].$1,
                      style: const TextStyle(color: FrontlineTheme.muted),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _PlayerActivityTimeline extends StatelessWidget {
  const _PlayerActivityTimeline({
    required this.incidentContext,
    required this.actions,
    required this.sessions,
    required this.playerName,
  });
  final PlayerIncidentContext? incidentContext;
  final List<Object?> actions;
  final List<Object?> sessions;
  final String playerName;

  @override
  Widget build(BuildContext context) {
    final entries = <_ProfileTimelineEntry>[];
    if (incidentContext != null) {
      entries.add(
        _ProfileTimelineEntry(
          icon: Icons.warning_amber_rounded,
          title: incidentContext!.report,
          subtitle: context.tr('Meldung eingegangen', 'Report received'),
          time: incidentContext!.reportedAt,
          accent: FrontlineTheme.gold,
        ),
      );
    }
    for (final raw in actions.whereType<Map>().take(3)) {
      final action = Map<String, dynamic>.from(raw);
      entries.add(
        _ProfileTimelineEntry(
          icon: Icons.gavel_outlined,
          title: _profileActionTitle(context, action),
          subtitle:
              action['reason']?.toString() ?? action['by']?.toString() ?? '—',
          time: _profileDate(action['time']),
          accent: FrontlineTheme.warning,
        ),
      );
    }
    if (entries.isEmpty && sessions.isNotEmpty) {
      entries.add(
        _ProfileTimelineEntry(
          icon: Icons.login,
          title: context.tr('Letzte Sitzung', 'Last session'),
          subtitle: playerName,
          time: _profileDate(_mapValue(sessions.first)['created']),
          accent: FrontlineTheme.chalk,
        ),
      );
    }
    if (entries.isEmpty) {
      entries.add(
        _ProfileTimelineEntry(
          icon: Icons.info_outline,
          title: context.tr(
            'Keine weiteren Ereignisse verfügbar',
            'No further events available',
          ),
          subtitle: context.tr(
            'Live-Daten werden bei Verfügbarkeit ergänzt.',
            'Live data is added when available.',
          ),
          time: null,
          accent: FrontlineTheme.muted,
        ),
      );
    }
    return Container(
      decoration: BoxDecoration(
        color: FrontlineTheme.surface,
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 11),
            child: Text(
              context
                  .tr('Verlauf dieser Runde', 'Round timeline')
                  .toUpperCase(),
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                letterSpacing: .4,
              ),
            ),
          ),
          const Divider(height: 1),
          for (var index = 0; index < entries.length; index++)
            _ProfileTimelineRow(
              entry: entries[index],
              isLast: index == entries.length - 1,
            ),
        ],
      ),
    );
  }
}

class _ProfileTimelineEntry {
  const _ProfileTimelineEntry({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.time,
    required this.accent,
  });
  final IconData icon;
  final String title;
  final String subtitle;
  final DateTime? time;
  final Color accent;
}

class _ProfileTimelineRow extends StatelessWidget {
  const _ProfileTimelineRow({required this.entry, required this.isLast});
  final _ProfileTimelineEntry entry;
  final bool isLast;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 38,
          child: Column(
            children: [
              Container(
                width: 30,
                height: 30,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: entry.accent),
                ),
                child: Icon(entry.icon, color: entry.accent, size: 18),
              ),
              if (!isLast)
                Container(width: 1, height: 44, color: const Color(0xff555647)),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (entry.time != null)
                Text(
                  _profileClock(entry.time!),
                  style: TextStyle(
                    color: entry.accent,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              if (entry.time != null) const SizedBox(height: 4),
              Text(
                entry.title,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                entry.subtitle,
                style: const TextStyle(color: FrontlineTheme.muted),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _PlayerIdentifiers extends StatelessWidget {
  const _PlayerIdentifiers({
    required this.steamId,
    required this.eosId,
    required this.platformPlayerId,
    required this.fallbackPlayerId,
  });
  final String? steamId;
  final String? eosId;
  final String? platformPlayerId;
  final String fallbackPlayerId;

  @override
  Widget build(BuildContext context) {
    final values = <(String, String, IconData)>[
      if (steamId != null && steamId!.isNotEmpty)
        ('SteamID', steamId!, Icons.sports_esports_outlined),
      if (eosId != null && eosId!.isNotEmpty)
        ('EOS-ID', eosId!, Icons.videogame_asset_outlined),
      if (platformPlayerId != null && platformPlayerId!.isNotEmpty)
        (
          context.tr('Plattform-ID', 'Platform ID'),
          platformPlayerId!,
          Icons.badge_outlined,
        ),
      if ((steamId == null || steamId!.isEmpty) &&
          (eosId == null || eosId!.isEmpty) &&
          (platformPlayerId == null || platformPlayerId!.isEmpty))
        (
          context.tr('Spieler-ID', 'Player ID'),
          fallbackPlayerId,
          Icons.badge_outlined,
        ),
    ];
    return Container(
      decoration: BoxDecoration(
        color: FrontlineTheme.surface,
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 13, 10, 12),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    context.tr('Kennungen', 'Identifiers').toUpperCase(),
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      letterSpacing: .4,
                    ),
                  ),
                ),
                const Icon(Icons.expand_less, color: FrontlineTheme.muted),
              ],
            ),
          ),
          const Divider(height: 1),
          for (var index = 0; index < values.length; index++) ...[
            _IdentifierRow(
              label: values[index].$1,
              value: values[index].$2,
              icon: values[index].$3,
            ),
            if (index != values.length - 1) const Divider(height: 1),
          ],
        ],
      ),
    );
  }
}

class _IdentifierRow extends StatelessWidget {
  const _IdentifierRow({
    required this.label,
    required this.value,
    required this.icon,
  });
  final String label;
  final String value;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
    child: Row(
      children: [
        Icon(icon, size: 21, color: FrontlineTheme.muted),
        const SizedBox(width: 10),
        SizedBox(
          width: 92,
          child: Text(
            label,
            style: const TextStyle(color: FrontlineTheme.chalk),
          ),
        ),
        Expanded(
          child: SelectableText(
            value,
            textAlign: TextAlign.end,
            style: const TextStyle(color: FrontlineTheme.muted),
          ),
        ),
        const SizedBox(width: 8),
        const Icon(Icons.copy_outlined, size: 18, color: FrontlineTheme.muted),
      ],
    ),
  );
}

class _PlayerAdminSummary extends StatelessWidget {
  const _PlayerAdminSummary({
    required this.flags,
    required this.bans,
    required this.comments,
  });
  final List<Object?> flags;
  final List<Object?> bans;
  final List<Object?> comments;

  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(
      color: FrontlineTheme.surface,
      border: Border.all(color: Theme.of(context).colorScheme.outline),
      borderRadius: BorderRadius.circular(3),
    ),
    child: Column(
      children: [
        _ProfileSummaryRow(
          icon: Icons.flag_outlined,
          label: context.tr('Markierungen', 'Flags'),
          value: '${flags.length}',
          accent: flags.isEmpty ? FrontlineTheme.chalk : FrontlineTheme.warning,
        ),
        const Divider(height: 1),
        _ProfileSummaryRow(
          icon: Icons.gavel_outlined,
          label: context.tr('Sperren', 'Bans'),
          value: '${bans.length}',
          accent: bans.isEmpty
              ? FrontlineTheme.success
              : FrontlineTheme.warning,
        ),
        const Divider(height: 1),
        _ProfileSummaryRow(
          icon: Icons.comment_outlined,
          label: context.tr('Admin-Kommentare', 'Admin comments'),
          value: '${comments.length}',
          accent: FrontlineTheme.chalk,
        ),
      ],
    ),
  );
}

class _ProfileSummaryRow extends StatelessWidget {
  const _ProfileSummaryRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.accent,
  });
  final IconData icon;
  final String label;
  final String value;
  final Color accent;
  @override
  Widget build(BuildContext context) => ListTile(
    dense: true,
    leading: Icon(icon, color: accent),
    title: Text(label),
    trailing: Text(
      value,
      style: TextStyle(
        color: accent,
        fontSize: 18,
        fontWeight: FontWeight.w700,
      ),
    ),
  );
}

class _PlayerProfileActionBar extends ConsumerWidget {
  const _PlayerProfileActionBar({
    required this.incidentContext,
    required this.connectionId,
    required this.playerId,
  });
  final PlayerIncidentContext? incidentContext;
  final String connectionId;
  final String playerId;

  Future<void> _runAction(
    BuildContext context,
    WidgetRef ref,
    String action,
  ) async {
    final incident = incidentContext;
    if (incident == null) return;
    final message = action == 'message';
    final profiles = await ref.read(connectionsProvider.future);
    if (!context.mounted) return;
    final profile = profiles.firstWhere((item) => item.id == connectionId);
    final api = CrconApi(profile, ref.read(secureStoreProvider));
    final templates = await _loadActionTemplates(api, action, context);
    if (!context.mounted) return;
    final value = await showDialog<String>(
      context: context,
      builder: (_) => _TextInputDialog(
        title: message
            ? context.tr('Nachricht an Spieler', 'Message player')
            : switch (action) {
                'punish' => context.tr('Spieler bestrafen', 'Punish player'),
                'kick' => context.tr('Spieler kicken', 'Kick player'),
                'temp_ban' => context.tr('Temporär sperren', 'Temporary ban'),
                'perma_ban' => context.tr('Permanent sperren', 'Permanent ban'),
                _ => context.tr('Maßnahme', 'Action'),
              },
        label: message
            ? context.tr('Nachricht', 'Message')
            : context.tr('Pflichtgrund', 'Required reason'),
        confirmLabel: context.tr('Ausführen', 'Run action'),
        maxLines: 3,
        templates: templates,
      ),
    );
    if (value == null || value.trim().isEmpty || !context.mounted) return;
    try {
      await api.runAction(incident.incidentId, {
        'action': action,
        'subject_id': incident.subjectId,
        'player_id': playerId,
        if (incident.subjectState == 'suggested')
          'confirm_subject_id': incident.subjectId,
        message ? 'message' : 'reason': value.trim(),
        if (action == 'kick' || action == 'temp_ban' || action == 'perma_ban')
          'confirmed': true,
        if (action == 'temp_ban') 'duration_hours': 2,
      });
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(context.tr('Maßnahme ausgeführt', 'Action executed')),
          ),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$error')));
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (incidentContext == null || !incidentContext!.canRunActions) {
      return const _FrontlineBottomBar(currentIndex: 1);
    }
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 9, 12, 9),
        decoration: const BoxDecoration(
          color: FrontlineTheme.surfaceHigh,
          border: Border(top: BorderSide(color: Color(0xff414337))),
        ),
        child: Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _runAction(context, ref, 'message'),
                icon: const Icon(Icons.message_outlined),
                label: Text(context.tr('Nachricht', 'Message')),
              ),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: PopupMenuButton<String>(
                onSelected: (action) => _runAction(context, ref, action),
                itemBuilder: (_) => [
                  PopupMenuItem(
                    value: 'punish',
                    child: Text(context.tr('Punish', 'Punish')),
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
                      context.tr('Permanent sperren', 'Permanent ban'),
                    ),
                  ),
                ],
                child: Container(
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    border: Border.all(color: FrontlineTheme.gold, width: 1.5),
                    borderRadius: BorderRadius.circular(3),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.shield_outlined,
                        color: FrontlineTheme.gold,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        context.tr('Maßnahme', 'Action'),
                        style: const TextStyle(
                          color: FrontlineTheme.gold,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String _playerProfileName(
  Map<String, dynamic> history,
  Map<String, dynamic>? live,
  Map<String, dynamic> soldier,
  BuildContext context,
) {
  final aliases = _listValue(history['names']);
  final alias = aliases
      .whereType<Map>()
      .map((value) => value['name']?.toString())
      .firstWhere(
        (value) => value != null && value.isNotEmpty,
        orElse: () => null,
      );
  return live?['name']?.toString() ??
      soldier['name']?.toString() ??
      alias ??
      history['player_name']?.toString() ??
      history['name']?.toString() ??
      context.tr('Unbekannter Spieler', 'Unknown player');
}

Object? _profileFirstValue(Map<String, dynamic> value, List<String> keys) {
  for (final key in keys) {
    if (value[key] != null) return value[key];
  }
  return null;
}

double? _profileNumber(Object? value) => switch (value) {
  num value => value.toDouble(),
  String value => double.tryParse(value),
  _ => null,
};

String _profileNumberText(Object? value) {
  final number = _profileNumber(value);
  if (number == null) return '—';
  return number == number.roundToDouble()
      ? '${number.toInt()}'
      : number.toStringAsFixed(1);
}

DateTime? _profileDate(Object? value) =>
    DateTime.tryParse(value?.toString() ?? '')?.toLocal();

String _profileClock(DateTime value) =>
    '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';

String _relativeProfileTime(BuildContext context, DateTime? value) {
  if (value == null) return context.tr('unbekannt', 'unknown');
  final difference = DateTime.now().difference(value).abs();
  if (difference.inMinutes < 1) {
    return context.tr('gerade eben', 'just now');
  }
  if (difference.inHours < 1) {
    return context.tr(
      'vor ${difference.inMinutes} Min.',
      '${difference.inMinutes} min ago',
    );
  }
  if (difference.inDays < 1) {
    return context.tr(
      'vor ${difference.inHours} Std.',
      '${difference.inHours} h ago',
    );
  }
  return '${value.day.toString().padLeft(2, '0')}.${value.month.toString().padLeft(2, '0')}.${value.year}';
}

String _profileActionTitle(BuildContext context, Map<String, dynamic> value) {
  final action = value['action_type']?.toString().toLowerCase() ?? 'action';
  return switch (action) {
    'punish' => context.tr('Punish ausgeführt', 'Punish executed'),
    'kick' => context.tr('Spieler gekickt', 'Player kicked'),
    'tempban' ||
    'temp_ban' => context.tr('Temporär gesperrt', 'Temporarily banned'),
    'permaban' ||
    'perma_ban' => context.tr('Permanent gesperrt', 'Permanently banned'),
    _ => context.tr('Admin-Maßnahme', 'Admin action'),
  };
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
      title: Text(context.tr('Squad', 'Squad')),
      actions: const [_LanguageButton()],
    ),
    bottomNavigationBar: const _FrontlineBottomBar(currentIndex: 1),
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
        final players = _listValue(squad['players']);
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: FrontlineTheme.surface,
                border: Border.all(
                  color: Theme.of(context).colorScheme.outline,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.squadName(
                      squad['squad_name']?.toString() ?? squadName,
                    ),
                    style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _ContextChip(
                        icon: Icons.flag_outlined,
                        label: context.teamName(
                          squad['team']?.toString() ?? team,
                        ),
                      ),
                      _ContextChip(
                        icon: Icons.groups_2_outlined,
                        label: context.squadTypeName(squad['type']?.toString()),
                      ),
                      _ContextChip(
                        icon: Icons.person_outline,
                        label:
                            '${players.length} ${context.tr('Mitglieder', 'members')}',
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
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
                                'Squadleader aktiv',
                                'Squad leader active',
                              )
                            : context.tr('Kein Squadleader', 'No squad leader'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(
                color: FrontlineTheme.surface,
                border: Border.all(
                  color: Theme.of(context).colorScheme.outline,
                ),
              ),
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 13,
                    ),
                    child: Row(
                      children: [
                        Text(
                          context.tr('Mitglieder', 'Members'),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const Spacer(),
                        Text(
                          context.tr('Live', 'Live'),
                          style: const TextStyle(color: FrontlineTheme.success),
                        ),
                      ],
                    ),
                  ),
                  const Divider(height: 1),
                  ...players.map((value) {
                    final player = _mapValue(value);
                    final playerId = player['player_id']?.toString() ?? '';
                    final isLeader = _isSquadLeader(player['role']?.toString());
                    return InkWell(
                      onTap: playerId.isEmpty
                          ? null
                          : () => context.push(
                              '/players/$connectionId/$playerId?server_number=$serverNumber',
                            ),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 12,
                        ),
                        decoration: const BoxDecoration(
                          border: Border(
                            bottom: BorderSide(color: Color(0xff3d3f32)),
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              isLeader
                                  ? Icons.shield_outlined
                                  : Icons.person_outline,
                              color: isLeader
                                  ? FrontlineTheme.gold
                                  : FrontlineTheme.chalk,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    player['name']?.toString() ?? playerId,
                                    style: const TextStyle(
                                      fontSize: 17,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    [
                                      context.roleName(
                                        player['role']?.toString(),
                                      ),
                                      if (player['level'] != null)
                                        'Lvl ${player['level']}',
                                      'K ${player['kills'] ?? '—'} / D ${player['deaths'] ?? '—'}',
                                    ].whereType<String>().join(' · '),
                                    style: const TextStyle(
                                      color: FrontlineTheme.muted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Icon(
                              Icons.chevron_right,
                              color: FrontlineTheme.muted,
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
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

class _TextInputDialog extends StatefulWidget {
  const _TextInputDialog({
    required this.title,
    required this.label,
    required this.confirmLabel,
    this.maxLines = 1,
    this.templates = const [],
  });

  final String title;
  final String label;
  final String confirmLabel;
  final int maxLines;
  final List<_ActionTemplate> templates;

  @override
  State<_TextInputDialog> createState() => _TextInputDialogState();
}

class _TextInputDialogState extends State<_TextInputDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    insetPadding: const EdgeInsets.symmetric(horizontal: 22, vertical: 24),
    scrollable: true,
    title: Text(widget.title),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _controller,
          autofocus: true,
          minLines: widget.maxLines > 1 ? 3 : 1,
          maxLines: widget.maxLines,
          decoration: InputDecoration(labelText: widget.label),
        ),
        if (widget.templates.isNotEmpty) ...[
          const SizedBox(height: 14),
          Text(
            context.tr('Schnellvorlage', 'Quick template'),
            style: const TextStyle(color: FrontlineTheme.muted),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 7,
            runSpacing: 7,
            children: widget.templates
                .map(
                  (template) => ActionChip(
                    tooltip: template.content,
                    label: Text(template.title),
                    onPressed: () => setState(() {
                      _controller.text = template.content;
                      _controller.selection = TextSelection.collapsed(
                        offset: template.content.length,
                      );
                    }),
                  ),
                )
                .toList(),
          ),
        ],
      ],
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: Text(context.tr('Abbrechen', 'Cancel')),
      ),
      FilledButton(
        onPressed: () => Navigator.pop(context, _controller.text.trim()),
        child: Text(widget.confirmLabel),
      ),
    ],
  );
}

class _ActionTemplate {
  const _ActionTemplate({required this.title, required this.content});

  factory _ActionTemplate.fromJson(Map<String, dynamic> value) {
    final content = value['content']?.toString().trim() ?? '';
    final title = value['title']?.toString().trim();
    return _ActionTemplate(
      title: title == null || title.isEmpty ? content : title,
      content: content,
    );
  }

  final String title;
  final String content;
}

Future<List<_ActionTemplate>> _loadActionTemplates(
  CrconApi api,
  String action,
  BuildContext context,
) async {
  final category = action == 'message'
      ? 'message'
      : {
          'punish',
          'kick',
          'temp_ban',
          'perma_ban',
          'disband_squad',
          'remove_from_squad',
        }.contains(action)
      ? 'reason'
      : null;
  if (category == null) return const [];
  try {
    final remote = await api.actionTemplates();
    final templates = (remote[category] ?? const [])
        .map(_ActionTemplate.fromJson)
        .where((template) => template.content.isNotEmpty)
        .toList();
    if (templates.isNotEmpty) return templates;
  } catch (_) {
    // Existing actions remain available to older CRCON instances and to roles
    // that deliberately do not have the shared-template permission.
  }
  if (!context.mounted) return const [];
  return _localActionTemplates(action, context);
}

List<_ActionTemplate> _localActionTemplates(
  String action,
  BuildContext context,
) {
  final values = switch (action) {
    'message' => [
      context.tr('Wir prüfen deine Meldung.', 'We are reviewing your report.'),
      context.tr(
        'Bitte bleib kurz auf dem Server.',
        'Please stay on the server for a moment.',
      ),
      context.tr(
        'Danke für die Meldung. Ein Admin kümmert sich darum.',
        'Thanks for the report. An admin is handling it.',
      ),
    ],
    'punish' => [
      context.tr('Teamkill', 'Team kill'),
      context.tr('Regelverstoß', 'Rule violation'),
      context.tr('Beleidigung', 'Abusive language'),
    ],
    'kick' || 'temp_ban' || 'perma_ban' => [
      context.tr('Wiederholtes Teamkilling', 'Repeated team killing'),
      context.tr('Wiederholter Regelverstoß', 'Repeated rule violation'),
      context.tr(
        'Beleidigung / toxisches Verhalten',
        'Abusive / toxic behavior',
      ),
    ],
    'disband_squad' || 'remove_from_squad' => [
      context.tr('Kein Squadleader vorhanden', 'No squad leader present'),
      context.tr('Verstoß gegen Squad-Regeln', 'Squad rule violation'),
    ],
    _ => const <String>[],
  };
  return values
      .map((value) => _ActionTemplate(title: value, content: value))
      .toList();
}

class _HandoverSubmission {
  const _HandoverSubmission({required this.username, required this.note});

  final String username;
  final String note;
}

class _HandoverDialog extends StatefulWidget {
  const _HandoverDialog({required this.admins, this.selectedAdmin});

  final List<String> admins;
  final String? selectedAdmin;

  @override
  State<_HandoverDialog> createState() => _HandoverDialogState();
}

class _HandoverDialogState extends State<_HandoverDialog> {
  late String _selectedAdmin = widget.admins.contains(widget.selectedAdmin)
      ? widget.selectedAdmin!
      : widget.admins.first;
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    insetPadding: const EdgeInsets.symmetric(horizontal: 22, vertical: 24),
    scrollable: true,
    title: Text(context.tr('Vorfall übergeben', 'Hand over incident')),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr(
            'Der ausgewählte Admin übernimmt den Vorfall und erhält deine Übergabenotiz im Verlauf.',
            'The selected admin takes the incident and receives your handover note in the timeline.',
          ),
          style: const TextStyle(color: FrontlineTheme.muted),
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          initialValue: _selectedAdmin,
          decoration: InputDecoration(
            labelText: context.tr('Übernehmen durch', 'Assign to'),
          ),
          items: widget.admins
              .map(
                (admin) => DropdownMenuItem(value: admin, child: Text(admin)),
              )
              .toList(),
          onChanged: (value) {
            if (value != null) setState(() => _selectedAdmin = value);
          },
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _note,
          minLines: 2,
          maxLines: 4,
          maxLength: 2000,
          decoration: InputDecoration(
            labelText: context.tr(
              'Kurze Übergabenotiz (optional)',
              'Short handover note (optional)',
            ),
          ),
        ),
      ],
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: Text(context.tr('Abbrechen', 'Cancel')),
      ),
      FilledButton(
        onPressed: () => Navigator.pop(
          context,
          _HandoverSubmission(
            username: _selectedAdmin,
            note: _note.text.trim(),
          ),
        ),
        child: Text(context.tr('Übergeben', 'Hand over')),
      ),
    ],
  );
}

class _ActionTargetSelection {
  const _ActionTargetSelection({
    this.subject,
    required this.playerId,
    this.playerName,
  }) : isReporter = false;

  const _ActionTargetSelection.reporter({
    required this.playerId,
    this.playerName,
  }) : subject = null,
       isReporter = true;

  final IncidentSubject? subject;
  final String playerId;
  final String? playerName;
  final bool isReporter;

  bool get confirmSuggested => !isReporter && subject?.state == 'suggested';
}

class _ActionTargetPicker extends StatelessWidget {
  const _ActionTargetPicker({required this.candidates});
  final List<IncidentSubject> candidates;

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(context.tr('Spieler für Maßnahme', 'Player for action')),
    content: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 420, maxHeight: 360),
      child: ListView.separated(
        shrinkWrap: true,
        itemCount: candidates.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (_, index) {
          final subject = candidates[index];
          final suggested = subject.state == 'suggested';
          return ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(
              suggested ? Icons.person_search_outlined : Icons.person,
              color: suggested
                  ? FrontlineTheme.warning
                  : FrontlineTheme.success,
            ),
            title: Text(subject.displayName),
            subtitle: Text(
              suggested
                  ? context.tr(
                      'Vorschlag – wird beim Ausführen bestätigt',
                      'Suggestion – confirmed when the action runs',
                    )
                  : context.tr('Bestätigtes Ziel', 'Confirmed target'),
            ),
            onTap: () => Navigator.pop(
              context,
              _ActionTargetSelection(
                subject: subject,
                playerId: subject.playerId!,
                playerName: subject.displayName,
              ),
            ),
          );
        },
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: Text(context.tr('Abbrechen', 'Cancel')),
      ),
    ],
  );
}

class _SquadMemberTargetPicker extends StatelessWidget {
  const _SquadMemberTargetPicker({
    required this.subject,
    required this.members,
  });

  final IncidentSubject subject;
  final List<Map<String, dynamic>> members;

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      context.tr('Squadmitglied anschreiben', 'Message squad member'),
    ),
    content: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 420, maxHeight: 360),
      child: ListView.separated(
        shrinkWrap: true,
        itemCount: members.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (_, index) {
          final member = members[index];
          final isLeader = _isSquadLeader(member['role']?.toString());
          return ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(
              isLeader ? Icons.shield_outlined : Icons.person_outline,
            ),
            title: Text(member['name']?.toString() ?? ''),
            subtitle: Text(
              isLeader
                  ? context.tr('Squadleader', 'Squad leader')
                  : context.roleName(member['role']?.toString()),
            ),
            onTap: () => Navigator.pop(
              context,
              _ActionTargetSelection(
                subject: subject,
                playerId: member['player_id']!.toString(),
                playerName: member['name']?.toString(),
              ),
            ),
          );
        },
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: Text(context.tr('Abbrechen', 'Cancel')),
      ),
    ],
  );
}

class _LinkTargetDialog extends StatefulWidget {
  const _LinkTargetDialog();

  @override
  State<_LinkTargetDialog> createState() => _LinkTargetDialogState();
}

class _LinkTargetDialogState extends State<_LinkTargetDialog> {
  final _id = TextEditingController();
  final _name = TextEditingController();

  @override
  void dispose() {
    _id.dispose();
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    insetPadding: const EdgeInsets.symmetric(horizontal: 22, vertical: 24),
    scrollable: true,
    title: Text(context.tr('Spielerziel verknüpfen', 'Link target player')),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        TextField(
          controller: _name,
          autofocus: true,
          decoration: InputDecoration(
            labelText: context.tr('Spielername', 'Player name'),
          ),
        ),
        TextField(
          controller: _id,
          decoration: InputDecoration(
            labelText: context.tr('Spieler-ID', 'Player ID'),
          ),
        ),
      ],
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: Text(context.tr('Abbrechen', 'Cancel')),
      ),
      FilledButton(
        onPressed: () => Navigator.pop(context, {
          'player_id': _id.text.trim(),
          'player_name': _name.text.trim(),
        }),
        child: Text(context.tr('Verknüpfen', 'Link')),
      ),
    ],
  );
}

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
  Map<String, dynamic>? _dossier;
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
      final api = await _api();
      final payload = await api.incident(widget.incidentId);
      final incident = AdminIncident.fromJson(payload, widget.connectionId);
      Map<String, dynamic>? dossier;
      // Older incidents created before MOBILE_CONTEXT_V2 can carry their
      // resolved player only in target_id.  That is safe for dossier lookup,
      // but never used as an action target without a confirmed subject.
      final playerId =
          incident.primarySubject?.actionPlayerId ?? incident.targetId;
      if (playerId != null) {
        try {
          dossier = await api.playerProfile(
            playerId,
            serverNumber: incident.serverNumber,
          );
        } catch (_) {
          // The incident stays usable if the optional dossier is unavailable.
        }
      }
      if (mounted) {
        setState(() {
          _incident = incident;
          _dossier = dossier;
        });
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
    final note = await showDialog<String>(
      context: context,
      builder: (_) => const _TextInputDialog(
        title: 'Add private admin note',
        label: 'Note',
        confirmLabel: 'Save',
        maxLines: 4,
      ),
    );
    if (note == null || note.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      final payload = await (await _api()).addNote(
        incident.id,
        revision: incident.revision,
        note: note.trim(),
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
    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (_) => const _LinkTargetDialog(),
    );
    final playerId = result?['player_id']?.trim() ?? '';
    final playerName = result?['player_name']?.trim() ?? '';
    if (playerId.isEmpty || playerName.isEmpty) return;
    await _mutate('link_target', {
      'target_id': playerId,
      'target_name': playerName,
    });
  }

  Future<void> _reassign() async {
    if (_busy) return;
    setState(() => _busy = true);
    List<String> admins;
    try {
      final bootstrap = await (await _api()).bootstrap();
      final user = _mapValue(bootstrap['user']);
      admins =
          _listValue(user['assignable_admins'])
              .map((value) => value?.toString().trim() ?? '')
              .where((value) => value.isNotEmpty)
              .toSet()
              .toList()
            ..sort();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
      return;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (!mounted) return;
    if (admins.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            context.tr(
              'Keine übernehmenden Admins verfügbar.',
              'No eligible admins are available.',
            ),
          ),
        ),
      );
      return;
    }
    final handover = await showDialog<_HandoverSubmission>(
      context: context,
      builder: (_) =>
          _HandoverDialog(admins: admins, selectedAdmin: _incident?.assignedTo),
    );
    if (handover == null) return;
    await _mutate('reassign', {
      'assigned_to': handover.username,
      if (handover.note.isNotEmpty) 'handover_note': handover.note,
    });
  }

  Future<void> _showIncidentSubpage(String section) async {
    final incident = _incident;
    if (incident == null) return;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: FrontlineTheme.background,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        child: SizedBox(
          height: MediaQuery.of(sheetContext).size.height * .82,
          child: switch (section) {
            'message' => _messageTab(incident),
            'subjects' => _targetsTab(incident),
            'squad' => _squadTab(incident),
            _ => _timelineTab(incident),
          },
        ),
      ),
    );
  }

  Future<_ActionTargetSelection?> _selectActionTarget(
    AdminIncident incident, {
    IncidentSubject? preferredSubject,
    Map<String, dynamic>? selectedPlayer,
    bool preferSquadLeader = true,
  }) async {
    if (selectedPlayer != null &&
        preferredSubject != null &&
        preferredSubject.state == 'confirmed') {
      final playerId = selectedPlayer['player_id']?.toString();
      if (playerId != null && playerId.isNotEmpty) {
        return _ActionTargetSelection(
          subject: preferredSubject,
          playerId: playerId,
          playerName: selectedPlayer['name']?.toString(),
        );
      }
    }
    if (preferredSubject?.kind == 'player' &&
        preferredSubject?.state == 'confirmed' &&
        preferredSubject?.playerId != null) {
      return _ActionTargetSelection(
        subject: preferredSubject!,
        playerId: preferredSubject.playerId!,
        playerName: preferredSubject.displayName,
      );
    }

    if (preferredSubject?.kind == 'squad' &&
        preferredSubject?.state == 'confirmed') {
      final members = _squadActionMembers(preferredSubject!);
      final leader = members.cast<Map<String, dynamic>?>().firstWhere(
        (member) =>
            member != null &&
            (member['player_id']?.toString() ==
                    preferredSubject.leaderPlayerId ||
                _isSquadLeader(member['role']?.toString())),
        orElse: () => null,
      );
      if (preferSquadLeader && leader != null) {
        return _ActionTargetSelection(
          subject: preferredSubject,
          playerId: leader['player_id']!.toString(),
          playerName: leader['name']?.toString() ?? preferredSubject.leaderName,
        );
      }
      if (members.isNotEmpty) {
        return showDialog<_ActionTargetSelection>(
          context: context,
          builder: (_) => _SquadMemberTargetPicker(
            subject: preferredSubject,
            members: members,
          ),
        );
      }
    }

    final candidates = incident.subjects
        .where(
          (subject) =>
              subject.kind == 'player' &&
              subject.playerId != null &&
              {'suggested', 'confirmed'}.contains(subject.state),
        )
        .toList();
    if (candidates.isNotEmpty) {
      return showDialog<_ActionTargetSelection>(
        context: context,
        builder: (_) => _ActionTargetPicker(candidates: candidates),
      );
    }

    // A report without a confirmed player or squad normally needs a quick
    // follow-up with its reporter.  Select that known player directly rather
    // than sending an admin through the manual ID search.  The server keeps
    // this separate from incident subjects, so the reporter never becomes an
    // accused/primary target by implication.
    final reporterId = incident.reporterId;
    if (reporterId != null && reporterId.isNotEmpty) {
      return _ActionTargetSelection.reporter(
        playerId: reporterId,
        playerName: incident.reporterName,
      );
    }

    final linkPlayer = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(
          context.tr('Spielerziel erforderlich', 'Player target required'),
        ),
        content: Text(
          context.tr(
            'Für diese Maßnahme muss ein Spieler ausgewählt werden. Der Fall wird erst bei der finalen Ausführung übernommen.',
            'Select a player before running this action. The incident is claimed only when the action is finally run.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(context.tr('Abbrechen', 'Cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.tr('Spieler wählen', 'Choose player')),
          ),
        ],
      ),
    );
    if (linkPlayer != true) return null;
    await _linkTarget();
    final linked = _incident?.primarySubject;
    if (linked?.kind != 'player' || linked?.actionPlayerId == null) return null;
    return _ActionTargetSelection(
      subject: linked!,
      playerId: linked.actionPlayerId!,
      playerName: linked.displayName,
    );
  }

  List<Map<String, dynamic>> _squadActionMembers(IncidentSubject subject) {
    final players = _listValue(subject.snapshot['players']);
    final members = players
        .map(_mapValue)
        .where((member) => (member['player_id']?.toString() ?? '').isNotEmpty)
        .toList();
    final leader = _mapValue(subject.snapshot['leader']);
    final leaderId = subject.leaderPlayerId ?? leader['player_id']?.toString();
    if (leaderId != null &&
        leaderId.isNotEmpty &&
        !members.any((member) => member['player_id']?.toString() == leaderId)) {
      members.insert(0, {
        ...leader,
        'player_id': leaderId,
        'name': subject.leaderName ?? leader['name'],
        'role': leader['role'] ?? 'officer',
      });
    }
    members.sort((left, right) {
      final leftLeader =
          left['player_id']?.toString() == leaderId ||
          _isSquadLeader(left['role']?.toString());
      final rightLeader =
          right['player_id']?.toString() == leaderId ||
          _isSquadLeader(right['role']?.toString());
      if (leftLeader == rightLeader) return 0;
      return leftLeader ? -1 : 1;
    });
    return members;
  }

  Future<void> _action(
    String action, {
    IncidentSubject? subject,
    Map<String, dynamic>? selectedPlayer,
    bool chooseSquadMember = false,
  }) async {
    final incident = _incident;
    if (incident == null || _busy) return;
    final isSquadDisband = action == 'disband_squad';
    final selectedSubject = subject ?? incident.primarySubject;
    _ActionTargetSelection? target;
    if (isSquadDisband) {
      if (selectedSubject?.kind != 'squad' ||
          selectedSubject?.state != 'confirmed') {
        setState(() {
          _error = context.tr(
            'Wähle zuerst einen bestätigten Squad aus.',
            'Select a confirmed squad first.',
          );
        });
        return;
      }
    } else {
      target = await _selectActionTarget(
        incident,
        preferredSubject: selectedSubject,
        selectedPlayer: selectedPlayer,
        preferSquadLeader: !chooseSquadMember,
      );
      if (!mounted || target == null) return;
    }
    final api = await _api();
    if (!mounted) return;
    final templates = await _loadActionTemplates(api, action, context);
    if (!mounted) return;
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => _TextInputDialog(
        title: action == 'message'
            ? context.tr(
                'Nachricht an ${target!.playerName ?? context.tr('Squadleader', 'Squad leader')}',
                'Message ${target.playerName ?? context.tr('Squad leader', 'Squad leader')}',
              )
            : switch (action) {
                'temp_ban' => context.tr('Temporäre Sperre', 'Temporary ban'),
                'perma_ban' => context.tr('Permanente Sperre', 'Permanent ban'),
                'kick' => context.tr('Spieler kicken', 'Kick player'),
                'disband_squad' => context.tr(
                  'Squad auflösen',
                  'Disband squad',
                ),
                'remove_from_squad' => context.tr(
                  'Aus Squad entfernen',
                  'Remove from squad',
                ),
                'punish' => context.tr('Spieler bestrafen', 'Punish player'),
                'message' => context.tr('Nachricht senden', 'Send message'),
                'comment' => context.tr('Admin-Kommentar', 'Admin comment'),
                _ => action,
              },
        label: action == 'message'
            ? context.tr('Nachricht', 'Message')
            : action == 'comment'
            ? context.tr('Admin-Kommentar', 'Admin comment')
            : context.tr('Pflichtgrund', 'Required reason'),
        confirmLabel: incident.status == 'new'
            ? context.tr('Übernehmen & ausführen', 'Claim & run')
            : context.tr('Ausführen', 'Run action'),
        maxLines: 3,
        templates: templates,
      ),
    );
    if (reason == null || reason.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await (await _api()).runAction(incident.id, {
        'action': action,
        if (isSquadDisband) 'subject_id': selectedSubject!.id,
        if (!isSquadDisband && target!.subject != null)
          'subject_id': target.subject!.id,
        if (!isSquadDisband) 'player_id': target!.playerId,
        if (!isSquadDisband) 'player_name': ?target!.playerName,
        if (!isSquadDisband && target!.isReporter) 'reporter_action': true,
        if (!isSquadDisband && target!.confirmSuggested)
          'confirm_subject_id': target.subject!.id,
        action == 'message'
            ? 'message'
            : action == 'comment'
            ? 'comment'
            : 'reason': reason
            .trim(),
        if (action == 'kick' ||
            action == 'temp_ban' ||
            action == 'perma_ban' ||
            action == 'disband_squad' ||
            action == 'remove_from_squad')
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

  void _openPlayer(String playerId) {
    final incident = _incident;
    final selectedSubject = incident?.subjects
        .where(
          (subject) =>
              subject.kind == 'player' &&
              subject.state == 'confirmed' &&
              subject.playerId == playerId,
        )
        .firstOrNull;
    final isReporter = incident?.reporterId == playerId;
    final incidentContext =
        incident != null && (selectedSubject != null || isReporter)
        ? PlayerIncidentContext(
            incidentId: incident.id,
            subjectId: selectedSubject?.id ?? '',
            subjectState: selectedSubject?.state ?? 'reporter',
            serverNumber: incident.serverNumber,
            report: _incidentExcerpt(
              incident,
              selectedSubject ?? incident.primarySubject,
            ),
            reporterName: incident.reporterName,
            reportedAt: incident.createdAt,
            canRunActions: selectedSubject?.actionPlayerId == playerId,
          )
        : null;
    context.push(
      '/players/${widget.connectionId}/$playerId'
      '?server_number=${incident?.serverNumber ?? ''}',
      extra: incidentContext,
    );
  }

  Map<String, dynamic>? _liveSubject(IncidentSubject subject) {
    final subjects = _incident?.liveContext['subjects'];
    final subjectMap = subjects is Map ? subjects : const <dynamic, dynamic>{};
    final value = subjectMap[subject.id];
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
        if ((incident.primarySubject?.actionPlayerId ?? incident.reporterId) !=
            null) ...[
          const SizedBox(height: 14),
          _PlayerContextExcerpt(
            connectionId: widget.connectionId,
            incidentId: incident.id,
            playerId:
                incident.primarySubject?.actionPlayerId ?? incident.reporterId!,
          ),
        ],
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
          final oldPlayers = _listValue(snapshot['players']);
          final live = _liveSubject(subject);
          final livePlayers = _listValue(live?['players']);
          final liveIds = livePlayers
              .map((player) => _mapValue(player)['player_id']?.toString())
              .toSet();
          final oldIds = oldPlayers
              .map((player) => _mapValue(player)['player_id']?.toString())
              .toSet();
          final joinedPlayers = livePlayers.where(
            (player) =>
                !oldIds.contains(_mapValue(player)['player_id']?.toString()),
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
              if (subject.state == 'confirmed')
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    onPressed: _busy
                        ? null
                        : () => _action(
                            'message',
                            subject: subject,
                            chooseSquadMember: true,
                          ),
                    icon: const Icon(Icons.person_search_outlined),
                    label: Text(
                      context.tr(
                        'Anderes Mitglied anschreiben',
                        'Message another member',
                      ),
                    ),
                  ),
                ),
              ...oldPlayers.map((value) {
                final player = _mapValue(value);
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
                              value: 'remove_from_squad',
                              child: Text(
                                context.tr(
                                  'Aus Squad entfernen',
                                  'Remove from squad',
                                ),
                              ),
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
                final player = _mapValue(value);
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
            title: Text(_eventTitle(context, event)),
            subtitle: Text(
              [
                event['actor']?.toString() ?? 'system',
                _eventTime(event),
                _eventDetail(event),
              ].where((value) => value.isNotEmpty).join(' · '),
            ),
          ),
        )
        .toList(),
  );

  Map<String, dynamic> _dossierLive(IncidentSubject subject) {
    final dossierLive = _nullableMapValue(_dossier?['live']);
    if (dossierLive != null) return dossierLive;
    return _liveSubject(subject) ?? subject.snapshot;
  }

  Map<String, dynamic> get _dossierHistory => _mapValue(_dossier?['history']);

  Object? _firstValue(Map<String, dynamic> value, List<String> keys) {
    for (final key in keys) {
      final candidate = value[key];
      if (candidate != null && candidate.toString().trim().isNotEmpty) {
        return candidate;
      }
    }
    return null;
  }

  double? _number(Object? value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString().replaceAll(',', '.') ?? '');
  }

  String _numberText(Object? value, {int decimals = 0}) {
    final number = _number(value);
    if (number == null) return '—';
    if (number == number.roundToDouble()) return number.toInt().toString();
    return number.toStringAsFixed(decimals).replaceAll('.', ',');
  }

  String _ratioText(Map<String, dynamic> live) {
    final kills = _number(_firstValue(live, ['kills', 'kill_count']));
    final deaths = _number(_firstValue(live, ['deaths', 'death_count']));
    if (kills == null || deaths == null) return '—';
    if (deaths == 0) return kills.toInt().toString();
    return (kills / deaths).toStringAsFixed(1).replaceAll('.', ',');
  }

  String _percentText(Object? value) {
    final number = _number(value);
    if (number == null) return '—';
    final percent = number <= 1 ? number * 100 : number;
    return '${percent.round()} %';
  }

  String _playtimeText(Map<String, dynamic> live) {
    final value = _firstValue(live, [
      'playtime',
      'play_time',
      'session_time',
      'time_played',
      'time_on_map',
    ]);
    final seconds = _number(value);
    if (seconds == null) {
      return value?.toString() ?? '—';
    }
    if (seconds >= 60) {
      return '${(seconds / 60).round()} ${context.tr('Min.', 'min')}';
    }
    return '${seconds.round()} ${context.tr('Sek.', 'sec')}';
  }

  Widget _dossierHeader(AdminIncident incident, IncidentSubject subject) {
    final isSquad = subject.kind == 'squad';
    final target = isSquad
        ? context.squadName(subject.squadName ?? subject.displayName)
        : subject.displayName;
    final live = _dossierLive(subject);
    final team = live['team']?.toString() ?? subject.team;
    final squad =
        live['unit_name']?.toString() ??
        live['squad_name']?.toString() ??
        subject.squadName;
    final role = live['role']?.toString() ?? subject.role;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 12, 15),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xff1b2017), FrontlineTheme.surface],
        ),
        border: Border.all(color: FrontlineTheme.gold, width: 1.5),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _IncidentTargetGlyph(squad: isSquad, general: false, accent: true),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  (isSquad
                          ? context.tr('Squad', 'Squad')
                          : context.tr('Spieler', 'Player'))
                      .toUpperCase(),
                  style: const TextStyle(
                    color: FrontlineTheme.gold,
                    fontSize: 12,
                    letterSpacing: .5,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  target,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 27,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 10),
                _DossierFact(
                  icon: Icons.dns_outlined,
                  label: 'Server ${incident.serverNumber}',
                ),
                if (team != null) ...[
                  const SizedBox(height: 5),
                  _DossierFact(
                    icon: Icons.groups_2_outlined,
                    label: context.teamName(team),
                  ),
                ],
                if (squad != null) ...[
                  const SizedBox(height: 5),
                  _DossierFact(
                    icon: Icons.gps_fixed,
                    label: context.squadName(squad),
                  ),
                ],
                if (role != null) ...[
                  const SizedBox(height: 5),
                  _DossierFact(
                    icon: Icons.military_tech_outlined,
                    label: context.roleName(role),
                  ),
                ],
              ],
            ),
          ),
          IconButton(
            tooltip: context.tr('Spielerprofil', 'Player profile'),
            onPressed: (subject.actionPlayerId ?? incident.targetId) == null
                ? null
                : () =>
                      _openPlayer(subject.actionPlayerId ?? incident.targetId!),
            icon: const Icon(Icons.chevron_right, color: FrontlineTheme.gold),
          ),
        ],
      ),
    );
  }

  Widget _originalReport(AdminIncident incident) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      gradient: const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xff1b2017), FrontlineTheme.surface],
      ),
      border: Border.all(color: Theme.of(context).colorScheme.outline),
      borderRadius: BorderRadius.circular(3),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.tr('Originalmeldung', 'Original report'),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 10),
        Text(
          _incidentExcerpt(incident, incident.primarySubject),
          style: const TextStyle(fontSize: 17, height: 1.35),
        ),
        const Divider(height: 22),
        Text.rich(
          TextSpan(
            style: const TextStyle(color: FrontlineTheme.muted, fontSize: 13),
            children: [
              TextSpan(text: context.tr('gemeldet von ', 'reported by ')),
              TextSpan(
                text:
                    incident.reporterName ?? context.tr('unbekannt', 'unknown'),
                style: const TextStyle(color: FrontlineTheme.gold),
              ),
              TextSpan(
                text:
                    ' · ${_relativeIncidentTime(context, incident.createdAt)}',
              ),
            ],
          ),
        ),
      ],
    ),
  );

  Widget _statsSection(IncidentSubject subject) {
    final live = _dossierLive(subject);
    final kills = _firstValue(live, ['kills', 'kill_count']);
    final teamkills = _firstValue(live, ['teamkills', 'team_kills']);
    final stats = <(String, String, IconData)>[
      ('K/D', _ratioText(live), Icons.gps_fixed),
      (context.tr('Kills', 'Kills'), _numberText(kills), Icons.close),
      (
        context.tr('Teamkills', 'Teamkills'),
        _numberText(teamkills),
        Icons.group_remove_outlined,
      ),
      (
        context.tr('Spielzeit', 'Playtime'),
        _playtimeText(live),
        Icons.schedule,
      ),
    ];
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xff1b2017), FrontlineTheme.surface],
        ),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(3),
      ),
      padding: const EdgeInsets.symmetric(vertical: 14),
      child: Row(
        children: [
          for (var index = 0; index < stats.length; index++)
            Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                decoration: BoxDecoration(
                  border: index == 0
                      ? null
                      : const Border(
                          left: BorderSide(color: Color(0xff3d3f32)),
                        ),
                ),
                child: Column(
                  children: [
                    Text(
                      stats[index].$1,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: FrontlineTheme.muted,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      stats[index].$2,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 9),
                    Icon(stats[index].$3, size: 20, color: FrontlineTheme.gold),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _signalsSection(AdminIncident incident, IncidentSubject subject) {
    final live = _dossierLive(subject);
    final history = _dossierHistory;
    final teamkills = _firstValue(live, ['teamkills', 'team_kills']);
    final headshots = _firstValue(live, [
      'headshot_percentage',
      'headshot_rate',
      'headshots_percent',
    ]);
    final bans = _listValue(history['bans']);
    final actions = incident.events.where((event) {
      final type = event['event_type']?.toString().toLowerCase() ?? '';
      return type.contains('action') ||
          type.contains('punish') ||
          type.contains('kick') ||
          type.contains('ban');
    }).length;
    final signals = <_DossierSignal>[
      _DossierSignal(
        icon: Icons.groups_2_outlined,
        label: context.tr('Teamverhalten', 'Team behaviour'),
        detail: teamkills == null
            ? context.tr(
                'Keine Teamkill-Live-Daten verfügbar',
                'No live teamkill data available',
              )
            : '${_numberText(teamkills)} ${context.tr('Teamkills in dieser Runde', 'teamkills this round')}',
        accent: teamkills != null && (_number(teamkills) ?? 0) > 0
            ? FrontlineTheme.warning
            : FrontlineTheme.chalk,
      ),
      _DossierSignal(
        icon: Icons.gps_fixed,
        label: context.tr('Trefferbild', 'Hit pattern'),
        detail: headshots == null
            ? context.tr(
                'Kopftreffer-Quote nicht verfügbar',
                'Headshot rate unavailable',
              )
            : '${_percentText(headshots)} ${context.tr('Kopftreffer in dieser Runde', 'headshots this round')} · K/D ${_ratioText(live)}',
        accent: FrontlineTheme.chalk,
      ),
      _DossierSignal(
        icon: Icons.history,
        label: context.tr('Verlauf', 'History'),
        detail: [
          '$actions ${context.tr('frühere Maßnahmen', 'prior actions')}',
          bans.isEmpty
              ? context.tr('keine aktive Sperre', 'no active ban')
              : '${bans.length} ${context.tr('Sperren in der Historie', 'bans in history')}',
        ].join(' · '),
        accent: bans.isEmpty ? FrontlineTheme.success : FrontlineTheme.warning,
      ),
    ];
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xff1b2017), FrontlineTheme.surface],
        ),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
            child: Text(
              context.tr('Prüfsignale', 'Review signals'),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
          ),
          for (var index = 0; index < signals.length; index++) ...[
            const Divider(height: 1),
            _DossierSignalRow(signal: signals[index]),
          ],
        ],
      ),
    );
  }

  Widget _recentActions(AdminIncident incident) {
    const actionTypes = {
      'action',
      'punish',
      'kick',
      'ban',
      'message',
      'comment',
      'note',
    };
    final actionEvents = incident.events.where((event) {
      final type = event['event_type']?.toString().toLowerCase() ?? '';
      return actionTypes.any(type.contains);
    }).toList();
    final events = (actionEvents.isEmpty ? incident.events : actionEvents)
        .reversed
        .take(2)
        .toList();
    if (events.isEmpty) {
      return const SizedBox.shrink();
    }
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 8),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xff1b2017), FrontlineTheme.surface],
        ),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.tr('Letzte Maßnahmen', 'Recent actions'),
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          for (final event in events)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(
                Icons.fiber_manual_record,
                size: 14,
                color: FrontlineTheme.gold,
              ),
              title: Text(_eventTitle(context, event)),
              subtitle: Text(
                [
                  event['actor']?.toString() ?? context.tr('System', 'System'),
                  _eventTime(event),
                ].where((value) => value.isNotEmpty).join(' · '),
                style: const TextStyle(color: FrontlineTheme.muted),
              ),
            ),
        ],
      ),
    );
  }

  Widget _primaryActions(AdminIncident incident) {
    final subject = incident.primarySubject;
    return SafeArea(
      top: false,
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [FrontlineTheme.surfaceHigh, FrontlineTheme.surface],
          ),
          border: Border(top: BorderSide(color: Color(0xff3d3f32))),
        ),
        padding: const EdgeInsets.fromLTRB(12, 9, 12, 9),
        child: Row(
          children: [
            Expanded(
              child: _DossierActionButton(
                onPressed: _busy
                    ? null
                    : () => _action('message', subject: subject),
                icon: Icons.message_outlined,
                label: context.tr('Nachricht', 'Message'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _DossierActionButton(
                onPressed: _busy
                    ? null
                    : () => _action('punish', subject: subject),
                icon: Icons.shield_outlined,
                label: context.tr('Punish', 'Punish'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: PopupMenuButton<String>(
                onSelected: (action) => _action(action, subject: subject),
                child: _DossierActionButton(
                  icon: Icons.gavel_outlined,
                  label: context.tr('Maßnahme', 'Action'),
                  emphasized: true,
                ),
                itemBuilder: (_) => [
                  PopupMenuItem(
                    value: 'comment',
                    child: Text(context.tr('Kommentar', 'Comment')),
                  ),
                  if (subject?.kind == 'squad' && subject?.state == 'confirmed')
                    PopupMenuItem(
                      value: 'disband_squad',
                      child: Text(
                        context.tr('Squad auflösen', 'Disband squad'),
                      ),
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
                      context.tr('Permanent sperren', 'Permanent ban'),
                    ),
                  ),
                ],
              ),
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
        title: Row(
          children: [
            Image.asset('assets/fln_logo.png', width: 20, height: 20),
            const SizedBox(width: 8),
            Text(context.tr('Vorfall', 'Incident')),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _busy ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
          PopupMenuButton<String>(
            onSelected: (operation) {
              switch (operation) {
                case 'message_details':
                  _showIncidentSubpage('message');
                case 'subjects':
                  _showIncidentSubpage('subjects');
                case 'squad':
                  _showIncidentSubpage('squad');
                case 'timeline':
                  _showIncidentSubpage('timeline');
                case 'note':
                  _addNote();
                case 'claim':
                case 'unclaim':
                case 'resolved':
                case 'dismissed':
                case 'reopen':
                  _mutate(operation);
                case 'reassign':
                  _reassign();
              }
            },
            itemBuilder: (_) => [
              if (incident?.status == 'new')
                PopupMenuItem(
                  value: 'claim',
                  child: Text(context.tr('Übernehmen', 'Claim')),
                ),
              if (incident?.status == 'claimed')
                PopupMenuItem(
                  value: 'unclaim',
                  child: Text(context.tr('Freigeben', 'Release')),
                ),
              PopupMenuItem(
                value: 'message_details',
                child: Text(context.tr('Meldedetails', 'Report details')),
              ),
              PopupMenuItem(
                value: 'subjects',
                child: Text(context.tr('Ziele verwalten', 'Manage subjects')),
              ),
              PopupMenuItem(
                value: 'squad',
                child: Text(context.tr('Squad ansehen', 'View squad')),
              ),
              PopupMenuItem(
                value: 'timeline',
                child: Text(context.tr('Gesamter Verlauf', 'Full timeline')),
              ),
              PopupMenuItem(
                value: 'note',
                child: Text(context.tr('Notiz hinzufügen', 'Add note')),
              ),
              if (incident != null &&
                  !{'resolved', 'dismissed'}.contains(incident.status)) ...[
                PopupMenuItem(
                  value: 'reassign',
                  child: Text(context.tr('Neu zuweisen', 'Reassign')),
                ),
                PopupMenuItem(
                  value: 'resolved',
                  child: Text(context.tr('Erledigt', 'Resolve')),
                ),
                PopupMenuItem(
                  value: 'dismissed',
                  child: Text(context.tr('Abweisen', 'Dismiss')),
                ),
              ],
              if (incident != null &&
                  {'resolved', 'dismissed'}.contains(incident.status))
                PopupMenuItem(
                  value: 'reopen',
                  child: Text(context.tr('Wieder öffnen', 'Reopen')),
                ),
            ],
          ),
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
          : Stack(
              children: [
                ListView(
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 104),
                  children: [
                    if (_busy) const LinearProgressIndicator(minHeight: 2),
                    if (_error != null) ...[
                      _ErrorView(message: _error!),
                      const SizedBox(height: 8),
                    ],
                    if (incident.primarySubject case final subject?) ...[
                      _dossierHeader(incident, subject),
                      const SizedBox(height: 12),
                      _originalReport(incident),
                      const SizedBox(height: 12),
                      _statsSection(subject),
                      const SizedBox(height: 12),
                      _signalsSection(incident, subject),
                      const SizedBox(height: 12),
                      _recentActions(incident),
                    ] else
                      _originalReport(incident),
                  ],
                ),
              ],
            ),
      bottomNavigationBar: incident == null ? null : _primaryActions(incident),
    );
  }
}

class _DossierFact extends StatelessWidget {
  const _DossierFact({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Icon(icon, size: 17, color: FrontlineTheme.chalk),
      const SizedBox(width: 9),
      Expanded(
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 14, color: FrontlineTheme.chalk),
        ),
      ),
    ],
  );
}

class _DossierActionButton extends StatelessWidget {
  const _DossierActionButton({
    required this.icon,
    required this.label,
    this.onPressed,
    this.emphasized = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final color = emphasized ? FrontlineTheme.gold : FrontlineTheme.chalk;
    final button = Container(
      height: 46,
      padding: const EdgeInsets.symmetric(horizontal: 7),
      decoration: BoxDecoration(
        border: Border.all(
          color: emphasized ? FrontlineTheme.gold : const Color(0xff5a5b4d),
        ),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 19, color: color),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.fade,
              softWrap: false,
              style: TextStyle(
                color: color,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
    if (onPressed == null) return Opacity(opacity: .45, child: button);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(3),
        child: button,
      ),
    );
  }
}

class _DossierSignal {
  const _DossierSignal({
    required this.icon,
    required this.label,
    required this.detail,
    required this.accent,
  });
  final IconData icon;
  final String label;
  final String detail;
  final Color accent;
}

class _DossierSignalRow extends StatelessWidget {
  const _DossierSignalRow({required this.signal});
  final _DossierSignal signal;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
    child: Row(
      children: [
        Icon(signal.icon, color: signal.accent, size: 25),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                signal.label,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                signal.detail,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: FrontlineTheme.muted),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

String _relativeIncidentTime(BuildContext context, DateTime value) {
  final difference = DateTime.now().difference(value);
  if (difference.inMinutes < 1) return context.tr('gerade eben', 'just now');
  if (difference.inMinutes < 60) {
    return context.tr(
      'vor ${difference.inMinutes} Min.',
      '${difference.inMinutes}m ago',
    );
  }
  if (difference.inHours < 24) {
    return context.tr(
      'vor ${difference.inHours} Std.',
      '${difference.inHours}h ago',
    );
  }
  return context.tr(
    'vor ${difference.inDays} Tg.',
    '${difference.inDays}d ago',
  );
}

String _eventTitle(BuildContext context, Map<String, dynamic> event) {
  final type = event['event_type']?.toString().toLowerCase() ?? '';
  if (type == 'reassign') {
    return context.tr('Vorfall übergeben', 'Incident handed over');
  }
  if (type.contains('punish')) {
    return context.tr('Spieler bestraft', 'Player punished');
  }
  if (type.contains('kick')) {
    return context.tr('Spieler gekickt', 'Player kicked');
  }
  if (type.contains('ban')) {
    return context.tr('Spieler gesperrt', 'Player banned');
  }
  if (type.contains('message')) {
    return context.tr('Nachricht gesendet', 'Message sent');
  }
  if (type.contains('note')) {
    return context.tr('Admin-Notiz hinzugefügt', 'Admin note added');
  }
  if (type.contains('claim')) {
    return context.tr('Vorfall übernommen', 'Incident claimed');
  }
  if (type.contains('created')) {
    return context.tr('Vorfall erstellt', 'Incident created');
  }
  return event['event_type']?.toString() ??
      context.tr('Vorfall aktualisiert', 'Incident updated');
}

String _eventDetail(Map<String, dynamic> event) {
  final payload = _mapValue(event['payload']);
  final type = event['event_type']?.toString().toLowerCase() ?? '';
  if (type == 'reassign') {
    final target = payload['assigned_to']?.toString() ?? '';
    final note = payload['handover_note']?.toString() ?? '';
    return [
      if (target.isNotEmpty) target,
      if (note.isNotEmpty) note,
    ].join(' · ');
  }
  if (type == 'note') return payload['note']?.toString() ?? '';
  return '';
}

String _eventTime(Map<String, dynamic> event) {
  final raw = event['created_at'] ?? event['timestamp'] ?? event['at'];
  if (raw == null) return '';
  final parsed = DateTime.tryParse(raw.toString());
  if (parsed == null) return raw.toString();
  return '${parsed.day.toString().padLeft(2, '0')}.${parsed.month.toString().padLeft(2, '0')}.${parsed.year} '
      '${parsed.hour.toString().padLeft(2, '0')}:${parsed.minute.toString().padLeft(2, '0')}';
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

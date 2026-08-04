import 'dart:async';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import 'crcon_api.dart';
import 'live_updates.dart';
import 'models.dart';
import 'providers.dart';
import 'push_relay.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
    await FirebaseMessaging.instance.requestPermission();
  } catch (_) {
    // Push remains optional until a deployment supplies its Firebase config.
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
      path: '/players/:connectionId/:playerId',
      builder: (_, state) => PlayerProfileScreen(
        connectionId: state.pathParameters['connectionId']!,
        playerId: state.pathParameters['playerId']!,
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
    } catch (_) {
      // No-op in self-hosted builds without Firebase configuration.
    }
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
        } catch (_) {
          // One unavailable CRCON connection must not block the others.
        }
      }
    } catch (_) {
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
    return MaterialApp.router(
      title: 'CRCON Admin',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xffc6a15b),
          brightness: Brightness.dark,
        ),
        scaffoldBackgroundColor: const Color(0xff111315),
        useMaterial3: true,
      ),
      routerConfig: _router,
    );
  }
}

class ConnectionsScreen extends ConsumerWidget {
  const ConnectionsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profiles = ref.watch(connectionsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('CRCON connections')),
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
  var connectionId = profiles.first.id;
  var serverNumber =
      (servers[connectionId]?.firstOrNull?['server_number'] as num?)?.toInt() ??
      1;
  final reason = TextEditingController();
  final submission = await showDialog<Map<String, dynamic>>(
    context: context,
    builder: (context) => StatefulBuilder(
      builder: (context, setDialogState) {
        final serverItems = servers[connectionId] ?? const [];
        return AlertDialog(
          title: const Text('Create incident'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: connectionId,
                decoration: const InputDecoration(labelText: 'CRCON'),
                items: profiles
                    .map(
                      (profile) => DropdownMenuItem(
                        value: profile.id,
                        child: Text(profile.name),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value == null) return;
                  setDialogState(() {
                    connectionId = value;
                    serverNumber =
                        (servers[value]?.firstOrNull?['server_number'] as num?)
                            ?.toInt() ??
                        1;
                  });
                },
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<int>(
                key: ValueKey(connectionId),
                initialValue: serverNumber,
                decoration: const InputDecoration(labelText: 'Game server'),
                items: serverItems
                    .map(
                      (server) => DropdownMenuItem(
                        value: (server['server_number'] as num).toInt(),
                        child: Text(
                          server['name']?.toString() ??
                              'Server ${server['server_number']}',
                        ),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value != null) serverNumber = value;
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reason,
                autofocus: true,
                maxLines: 4,
                decoration: const InputDecoration(labelText: 'Reason'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                if (reason.text.trim().isEmpty) return;
                Navigator.pop(context, {
                  'connection_id': connectionId,
                  'server_number': serverNumber,
                  'reason': reason.text.trim(),
                });
              },
              child: const Text('Create'),
            ),
          ],
        );
      },
    ),
  );
  reason.dispose();
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
        label: const Text('New incident'),
      ),
      appBar: AppBar(
        title: const Text('Incident inbox'),
        actions: [
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
        ],
      ),
      body: inbox.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorView(message: error.toString()),
        data: (items) => RefreshIndicator(
          onRefresh: () async => ref.refresh(inboxProvider.future),
          child: items.isEmpty
              ? ListView(
                  children: const [
                    SizedBox(height: 220),
                    Center(child: Text('No incidents.')),
                  ],
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return Card(
                      child: ListTile(
                        onTap: () => context.push(
                          '/incidents/${item.connectionId}/${item.id}',
                        ),
                        leading: Icon(
                          item.status == 'new'
                              ? Icons.notification_important
                              : Icons.assignment_ind,
                          color: item.status == 'new' ? Colors.orange : null,
                        ),
                        title: Text(
                          item.reason,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: Text(
                          'Server ${item.serverNumber} · ${item.reporterName ?? 'manual'}'
                          '${item.assignedTo == null ? '' : ' · ${item.assignedTo}'}',
                        ),
                        trailing: item.stale
                            ? const Tooltip(
                                message: 'Cached — may be stale',
                                child: Icon(Icons.cloud_off),
                              )
                            : Text(item.status),
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
      final results = await CrconApi(
        profile,
        ref.read(secureStoreProvider),
      ).searchPlayers(term);
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
      appBar: AppBar(title: const Text('Player search')),
      body: profiles.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorView(message: error.toString()),
        data: (items) {
          if (items.isEmpty) {
            return const Center(child: Text('Pair a CRCON connection first.'));
          }
          _connectionId ??= items.first.id;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              DropdownButtonFormField<String>(
                initialValue: _connectionId,
                decoration: const InputDecoration(
                  labelText: 'CRCON connection',
                ),
                items: items
                    .map(
                      (item) => DropdownMenuItem(
                        value: item.id,
                        child: Text(item.name),
                      ),
                    )
                    .toList(),
                onChanged: (value) => setState(() => _connectionId = value),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _query,
                decoration: InputDecoration(
                  labelText: 'Name or player ID',
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
                        'Unknown',
                  ),
                  subtitle: Text(playerId),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: playerId.isEmpty
                      ? null
                      : () => context.push('/players/$_connectionId/$playerId'),
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
  });

  final String connectionId;
  final String playerId;

  Future<Map<String, dynamic>> _load(WidgetRef ref) async {
    final profiles = await ref.read(connectionsProvider.future);
    final profile = profiles.firstWhere((item) => item.id == connectionId);
    return CrconApi(
      profile,
      ref.read(secureStoreProvider),
    ).playerProfile(playerId);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
    appBar: AppBar(title: const Text('Player profile')),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _load(ref),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return _ErrorView(message: snapshot.error.toString());
        }
        final profile = snapshot.data!;
        final bans = profile['bans'] as List<dynamic>? ?? const [];
        final comments = profile['comments'] as List<dynamic>? ?? const [];
        final sessions = profile['sessions'] as List<dynamic>? ?? const [];
        final live = profile['live'] == null
            ? null
            : Map<String, dynamic>.from(profile['live'] as Map);
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              profile['player_name']?.toString() ??
                  profile['name']?.toString() ??
                  'Unknown player',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            SelectableText(profile['player_id']?.toString() ?? playerId),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                live == null ? Icons.cloud_off : Icons.circle,
                color: live == null ? null : Colors.green,
              ),
              title: Text(live == null ? 'Offline' : 'Online now'),
              subtitle: live == null
                  ? null
                  : Text(
                      [
                            live['team']?.toString(),
                            live['unit_name']?.toString(),
                            live['role']?.toString(),
                          ]
                          .whereType<String>()
                          .where((value) => value.isNotEmpty)
                          .join(' · '),
                    ),
            ),
            const Divider(height: 32),
            _ProfileCount(label: 'Sessions', count: sessions.length),
            _ProfileCount(label: 'Bans', count: bans.length),
            _ProfileCount(label: 'Admin comments', count: comments.length),
            if (profile['flags'] is List)
              _ProfileCount(
                label: 'Flags',
                count: (profile['flags'] as List).length,
              ),
            const Divider(height: 32),
            Text(
              'Recent comments',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            ...comments
                .take(20)
                .map(
                  (comment) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.comment_outlined),
                    title: Text(
                      (comment as Map)['comment']?.toString() ??
                          comment.toString(),
                    ),
                  ),
                ),
          ],
        );
      },
    ),
  );
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

  Future<void> _action(String action) async {
    final incident = _incident;
    if (incident == null || incident.targetId == null) return;
    final controller = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(action == 'temp_ban' ? 'Temporary ban' : action),
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
        action == 'message'
            ? 'message'
            : action == 'comment'
            ? 'comment'
            : 'reason': controller.text
            .trim(),
        if (action == 'kick' || action == 'temp_ban') 'confirmed': true,
        if (action == 'temp_ban') 'duration_hours': 2,
      });
      await _load();
    } catch (error) {
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
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
      appBar: AppBar(title: const Text('Incident')),
      body: _busy && incident == null
          ? const Center(child: CircularProgressIndicator())
          : incident == null
          ? _ErrorView(message: _error ?? 'Incident unavailable')
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_error != null) _ErrorView(message: _error!),
                Text(
                  incident.reason,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),
                Text(
                  'Server ${incident.serverNumber} · ${incident.source} · ${incident.status}',
                ),
                Text('Reporter: ${incident.reporterName ?? 'not set'}'),
                Text('Target: ${incident.targetName ?? 'not linked'}'),
                Text('Assigned: ${incident.assignedTo ?? 'nobody'}'),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (incident.status == 'new')
                      FilledButton(
                        onPressed: () => _mutate('claim'),
                        child: const Text('Claim'),
                      ),
                    if (incident.status == 'claimed')
                      OutlinedButton(
                        onPressed: () => _mutate('unclaim'),
                        child: const Text('Release'),
                      ),
                    if (!{'resolved', 'dismissed'}.contains(incident.status))
                      OutlinedButton(
                        onPressed: _busy ? null : _reassign,
                        child: const Text('Reassign'),
                      ),
                    if (!{
                      'resolved',
                      'dismissed',
                    }.contains(incident.status)) ...[
                      FilledButton(
                        onPressed: () => _mutate('resolved'),
                        child: const Text('Resolve'),
                      ),
                      OutlinedButton(
                        onPressed: () => _mutate('dismissed'),
                        child: const Text('Dismiss'),
                      ),
                    ] else
                      FilledButton(
                        onPressed: () => _mutate('reopen'),
                        child: const Text('Reopen'),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: _busy ? null : _addNote,
                      icon: const Icon(Icons.note_add_outlined),
                      label: const Text('Add note'),
                    ),
                    if (incident.targetId == null)
                      OutlinedButton.icon(
                        onPressed: _busy ? null : _linkTarget,
                        icon: const Icon(Icons.person_add_alt),
                        label: const Text('Link player'),
                      ),
                  ],
                ),
                const Divider(height: 40),
                Text(
                  'Player actions',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 10),
                if (incident.targetId == null)
                  const Text(
                    'Link a unique player in CRCON before using player actions.',
                  )
                else
                  Wrap(
                    spacing: 8,
                    children: [
                      OutlinedButton(
                        onPressed: () => _action('message'),
                        child: const Text('Message'),
                      ),
                      OutlinedButton(
                        onPressed: () => _action('punish'),
                        child: const Text('Punish'),
                      ),
                      OutlinedButton(
                        onPressed: () => _action('comment'),
                        child: const Text('Comment'),
                      ),
                      OutlinedButton(
                        onPressed: () => _action('kick'),
                        child: const Text('Kick'),
                      ),
                      FilledButton.tonal(
                        onPressed: () => _action('temp_ban'),
                        child: const Text('Tempban'),
                      ),
                    ],
                  ),
                const Divider(height: 40),
                Text('Timeline', style: Theme.of(context).textTheme.titleLarge),
                ...incident.events.reversed.map(
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
                ),
              ],
            ),
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

class ConnectionProfile {
  const ConnectionProfile({
    required this.id,
    required this.baseUrl,
    required this.name,
    required this.username,
    required this.deviceId,
  });

  final String id;
  final String baseUrl;
  final String name;
  final String username;
  final String deviceId;

  factory ConnectionProfile.fromJson(Map<String, dynamic> json) =>
      ConnectionProfile(
        id: json['id'] as String,
        baseUrl: json['base_url'] as String,
        name: json['name'] as String,
        username: json['username'] as String,
        deviceId: json['device_id'] as String,
      );

  Map<String, dynamic> toJson() => {
    'id': id,
    'base_url': baseUrl,
    'name': name,
    'username': username,
    'device_id': deviceId,
  };
}

class AdminIncident {
  const AdminIncident({
    required this.id,
    required this.connectionId,
    required this.serverNumber,
    required this.source,
    required this.status,
    required this.reason,
    required this.revision,
    required this.createdAt,
    required this.updatedAt,
    this.reporterName,
    this.reporterId,
    this.targetId,
    this.targetName,
    this.assignedTo,
    this.rawMessage,
    this.reporterContext = const {},
    this.subjects = const [],
    this.liveContext = const {},
    this.events = const [],
    this.stale = false,
  });

  final String id;
  final String connectionId;
  final int serverNumber;
  final String source;
  final String status;
  final String reason;
  final int revision;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? reporterName;
  final String? reporterId;
  final String? targetId;
  final String? targetName;
  final String? assignedTo;
  final String? rawMessage;
  final Map<String, dynamic> reporterContext;
  final List<IncidentSubject> subjects;
  final Map<String, dynamic> liveContext;
  final List<Map<String, dynamic>> events;
  final bool stale;

  factory AdminIncident.fromJson(
    Map<String, dynamic> json,
    String connectionId, {
    bool stale = false,
  }) => AdminIncident(
    id: json['id'].toString(),
    connectionId: connectionId,
    serverNumber: (json['server_number'] as num).toInt(),
    source: json['source']?.toString() ?? 'manual',
    status: json['status']?.toString() ?? 'new',
    reason: json['reason']?.toString() ?? '',
    revision: (json['revision'] as num?)?.toInt() ?? 1,
    createdAt: DateTime.parse(json['created_at'].toString()),
    updatedAt: DateTime.parse(json['updated_at'].toString()),
    reporterName: json['reporter_name']?.toString(),
    reporterId: json['reporter_id']?.toString(),
    targetId: json['target_id']?.toString(),
    targetName: json['target_name']?.toString(),
    assignedTo: json['assigned_to']?.toString(),
    rawMessage: json['raw_message']?.toString(),
    reporterContext: Map<String, dynamic>.from(
      json['reporter_context'] as Map? ?? const {},
    ),
    subjects: (json['subjects'] as List<dynamic>? ?? const [])
        .map(
          (subject) => IncidentSubject.fromJson(
            Map<String, dynamic>.from(subject as Map),
          ),
        )
        .toList(),
    liveContext: Map<String, dynamic>.from(
      json['live_context'] as Map? ?? const {},
    ),
    events: (json['events'] as List<dynamic>? ?? const [])
        .map((event) => Map<String, dynamic>.from(event as Map))
        .toList(),
    stale: stale,
  );

  IncidentSubject? get primarySubject {
    for (final subject in subjects) {
      if (subject.isPrimary && subject.state == 'confirmed') return subject;
    }
    return null;
  }

  int get suggestedCount =>
      subjects.where((subject) => subject.state == 'suggested').length;
}

class IncidentSubject {
  const IncidentSubject({
    required this.id,
    required this.kind,
    required this.state,
    required this.displayName,
    required this.isPrimary,
    this.playerId,
    this.team,
    this.squadName,
    this.squadType,
    this.role,
    this.leaderPlayerId,
    this.leaderName,
    this.confidence,
    this.matchMethod,
    this.snapshot = const {},
  });

  final String id;
  final String kind;
  final String state;
  final String displayName;
  final bool isPrimary;
  final String? playerId;
  final String? team;
  final String? squadName;
  final String? squadType;
  final String? role;
  final String? leaderPlayerId;
  final String? leaderName;
  final double? confidence;
  final String? matchMethod;
  final Map<String, dynamic> snapshot;

  factory IncidentSubject.fromJson(Map<String, dynamic> json) =>
      IncidentSubject(
        id: json['id']?.toString() ?? '',
        kind: json['kind']?.toString() ?? 'player',
        state: json['state']?.toString() ?? 'suggested',
        displayName: json['display_name']?.toString() ?? '',
        isPrimary: json['is_primary'] == true,
        playerId: json['player_id']?.toString(),
        team: json['team']?.toString(),
        squadName: json['squad_name']?.toString(),
        squadType: json['squad_type']?.toString(),
        role: json['role']?.toString(),
        leaderPlayerId: json['leader_player_id']?.toString(),
        leaderName: json['leader_name']?.toString(),
        confidence: (json['confidence'] as num?)?.toDouble(),
        matchMethod: json['match_method']?.toString(),
        snapshot: Map<String, dynamic>.from(
          json['snapshot'] as Map? ?? const {},
        ),
      );

  String? get actionPlayerId => kind == 'player' ? playerId : null;
}

class PairingPayload {
  const PairingPayload({
    required this.baseUrl,
    required this.pairingId,
    required this.secret,
  });

  final String baseUrl;
  final String pairingId;
  final String secret;

  factory PairingPayload.parse(String value) {
    final uri = Uri.parse(value);
    if (uri.scheme != 'crcon' || uri.host != 'pair') {
      throw const FormatException('This is not a CRCON pairing code.');
    }
    if (uri.queryParameters['v'] != '1') {
      throw const FormatException('Unsupported CRCON mobile protocol.');
    }
    final base = Uri.parse(uri.queryParameters['base'] ?? '');
    final id = uri.queryParameters['pairing_id'] ?? '';
    final secret = uri.queryParameters['secret'] ?? '';
    if (!base.hasAuthority || id.isEmpty || secret.isEmpty) {
      throw const FormatException('Incomplete CRCON pairing code.');
    }
    return PairingPayload(
      baseUrl: base.toString().replaceFirst(RegExp(r'/$'), ''),
      pairingId: id,
      secret: secret,
    );
  }
}

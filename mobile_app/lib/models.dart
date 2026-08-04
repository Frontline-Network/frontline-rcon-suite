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
    this.targetId,
    this.targetName,
    this.assignedTo,
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
  final String? targetId;
  final String? targetName;
  final String? assignedTo;
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
    targetId: json['target_id']?.toString(),
    targetName: json['target_name']?.toString(),
    assignedTo: json['assigned_to']?.toString(),
    events: (json['events'] as List<dynamic>? ?? const [])
        .map((event) => Map<String, dynamic>.from(event as Map))
        .toList(),
    stale: stale,
  );
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

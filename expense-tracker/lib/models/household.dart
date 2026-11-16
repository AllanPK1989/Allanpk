import 'enums.dart';
import 'model_utils.dart';

class HouseholdMember {
  const HouseholdMember({
    required this.uid,
    required this.name,
    required this.role,
    required this.joinedAt,
    this.photoUrl,
    this.color = 0xFF6750A4,
  });

  final String uid;
  final String name;
  final MemberRole role;
  final DateTime joinedAt;
  final String? photoUrl;

  /// ARGB colour used for avatars and per-member charts.
  final int color;

  String get initials {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts.first.isEmpty) return '?';
    if (parts.length == 1) return parts.first[0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  HouseholdMember copyWith({
    String? name,
    MemberRole? role,
    String? photoUrl,
    int? color,
  }) {
    return HouseholdMember(
      uid: uid,
      name: name ?? this.name,
      role: role ?? this.role,
      joinedAt: joinedAt,
      photoUrl: photoUrl ?? this.photoUrl,
      color: color ?? this.color,
    );
  }

  Map<String, dynamic> toMap() => {
        'name': name,
        'role': role.storageKey,
        'joinedAt': joinedAt,
        'photoUrl': photoUrl,
        'color': color,
      };

  factory HouseholdMember.fromMap(String uid, Map<String, dynamic> map) {
    return HouseholdMember(
      uid: uid,
      name: parseString(map['name'], 'Member'),
      role: MemberRole.fromKey(map['role'] as String?),
      joinedAt: parseDate(map['joinedAt']),
      photoUrl: map['photoUrl'] as String?,
      color: parseInt(map['color'], 0xFF6750A4),
    );
  }
}

/// A household is the unit of sharing: a personal space for a single user or
/// a family space where every member sees shared accounts, budgets and
/// transactions.
class Household {
  const Household({
    required this.id,
    required this.name,
    required this.ownerId,
    required this.baseCurrency,
    required this.memberIds,
    required this.members,
    required this.inviteCode,
    required this.createdAt,
    this.monthStartDay = 1,
  });

  final String id;
  final String name;
  final String ownerId;
  final String baseCurrency;

  /// Flat list used by Firestore security rules for membership checks.
  final List<String> memberIds;
  final Map<String, HouseholdMember> members;
  final String inviteCode;
  final DateTime createdAt;

  /// Day of the month on which the budgeting month begins (1-28).
  final int monthStartDay;

  bool get isShared => memberIds.length > 1;

  MemberRole roleOf(String uid) => members[uid]?.role ?? MemberRole.child;

  HouseholdMember? member(String uid) => members[uid];

  List<HouseholdMember> get sortedMembers {
    final list = members.values.toList()
      ..sort((a, b) {
        if (a.role == MemberRole.owner) return -1;
        if (b.role == MemberRole.owner) return 1;
        return a.name.toLowerCase().compareTo(b.name.toLowerCase());
      });
    return list;
  }

  Household copyWith({
    String? name,
    String? baseCurrency,
    List<String>? memberIds,
    Map<String, HouseholdMember>? members,
    String? inviteCode,
    int? monthStartDay,
  }) {
    return Household(
      id: id,
      name: name ?? this.name,
      ownerId: ownerId,
      baseCurrency: baseCurrency ?? this.baseCurrency,
      memberIds: memberIds ?? this.memberIds,
      members: members ?? this.members,
      inviteCode: inviteCode ?? this.inviteCode,
      createdAt: createdAt,
      monthStartDay: monthStartDay ?? this.monthStartDay,
    );
  }

  Map<String, dynamic> toMap() => {
        'name': name,
        'ownerId': ownerId,
        'baseCurrency': baseCurrency,
        'memberIds': memberIds,
        'members': members.map((k, v) => MapEntry(k, v.toMap())),
        'inviteCode': inviteCode,
        'createdAt': createdAt,
        'monthStartDay': monthStartDay,
      };

  factory Household.fromMap(String id, Map<String, dynamic> map) {
    final rawMembers = parseMap(map['members']);
    return Household(
      id: id,
      name: parseString(map['name'], 'Household'),
      ownerId: parseString(map['ownerId']),
      baseCurrency: parseString(map['baseCurrency'], 'INR'),
      memberIds: parseStringList(map['memberIds']),
      members: rawMembers.map(
        (uid, value) => MapEntry(uid, HouseholdMember.fromMap(uid, parseMap(value))),
      ),
      inviteCode: parseString(map['inviteCode']),
      createdAt: parseDate(map['createdAt']),
      monthStartDay: parseInt(map['monthStartDay'], 1).clamp(1, 28),
    );
  }
}

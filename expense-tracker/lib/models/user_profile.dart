import 'model_utils.dart';

class UserProfile {
  const UserProfile({
    required this.uid,
    required this.email,
    required this.displayName,
    this.photoUrl,
    this.activeHouseholdId,
    this.householdIds = const [],
    required this.createdAt,
    this.onboardingComplete = false,
  });

  final String uid;
  final String email;
  final String displayName;
  final String? photoUrl;
  final String? activeHouseholdId;
  final List<String> householdIds;
  final DateTime createdAt;
  final bool onboardingComplete;

  String get initials {
    final parts = displayName.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts.first.isEmpty) {
      return email.isNotEmpty ? email[0].toUpperCase() : '?';
    }
    if (parts.length == 1) return parts.first[0].toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  UserProfile copyWith({
    String? email,
    String? displayName,
    String? photoUrl,
    String? activeHouseholdId,
    List<String>? householdIds,
    bool? onboardingComplete,
  }) {
    return UserProfile(
      uid: uid,
      email: email ?? this.email,
      displayName: displayName ?? this.displayName,
      photoUrl: photoUrl ?? this.photoUrl,
      activeHouseholdId: activeHouseholdId ?? this.activeHouseholdId,
      householdIds: householdIds ?? this.householdIds,
      createdAt: createdAt,
      onboardingComplete: onboardingComplete ?? this.onboardingComplete,
    );
  }

  Map<String, dynamic> toMap() => {
        'email': email,
        'displayName': displayName,
        'photoUrl': photoUrl,
        'activeHouseholdId': activeHouseholdId,
        'householdIds': householdIds,
        'createdAt': createdAt,
        'onboardingComplete': onboardingComplete,
      };

  factory UserProfile.fromMap(String uid, Map<String, dynamic> map) {
    return UserProfile(
      uid: uid,
      email: parseString(map['email']),
      displayName: parseString(map['displayName']),
      photoUrl: map['photoUrl'] as String?,
      activeHouseholdId: map['activeHouseholdId'] as String?,
      householdIds: parseStringList(map['householdIds']),
      createdAt: parseDate(map['createdAt']),
      onboardingComplete: parseBool(map['onboardingComplete']),
    );
  }
}

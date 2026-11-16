import 'enums.dart';
import 'model_utils.dart';

/// Family activity feed entry: "Priya added ₹450 at Groceries".
class ActivityEntry {
  const ActivityEntry({
    required this.id,
    required this.actorId,
    required this.actorName,
    required this.action,
    required this.entityType,
    required this.entityId,
    required this.summary,
    required this.at,
    this.amount,
  });

  final String id;
  final String actorId;
  final String actorName;
  final ActivityAction action;
  final String entityType;
  final String entityId;
  final String summary;
  final DateTime at;
  final double? amount;

  Map<String, dynamic> toMap() => {
        'actorId': actorId,
        'actorName': actorName,
        'action': action.storageKey,
        'entityType': entityType,
        'entityId': entityId,
        'summary': summary,
        'at': at,
        'amount': amount,
      };

  factory ActivityEntry.fromMap(String id, Map<String, dynamic> map) {
    return ActivityEntry(
      id: id,
      actorId: parseString(map['actorId']),
      actorName: parseString(map['actorName'], 'Someone'),
      action: ActivityAction.fromKey(map['action'] as String?),
      entityType: parseString(map['entityType']),
      entityId: parseString(map['entityId']),
      summary: parseString(map['summary']),
      at: parseDate(map['at']),
      amount: map['amount'] == null ? null : parseDouble(map['amount']),
    );
  }
}

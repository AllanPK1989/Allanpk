import 'model_utils.dart';

class Goal {
  const Goal({
    required this.id,
    required this.name,
    required this.targetAmount,
    this.savedAmount = 0,
    this.deadline,
    this.iconKey = 'savings',
    this.color = 0xFF00897B,
    this.note = '',
    this.isShared = true,
    this.isCompleted = false,
    required this.createdBy,
    required this.createdAt,
  });

  final String id;
  final String name;
  final double targetAmount;
  final double savedAmount;
  final DateTime? deadline;
  final String iconKey;
  final int color;
  final String note;
  final bool isShared;
  final bool isCompleted;
  final String createdBy;
  final DateTime createdAt;

  double get progress =>
      targetAmount <= 0 ? 0 : (savedAmount / targetAmount).clamp(0, 1).toDouble();
  double get remaining => (targetAmount - savedAmount).clamp(0, double.infinity);

  /// Suggested monthly contribution to hit the deadline.
  double? monthlyNeeded(DateTime now) {
    final d = deadline;
    if (d == null || remaining <= 0) return null;
    final months = (d.year - now.year) * 12 + d.month - now.month;
    if (months <= 0) return remaining;
    return remaining / months;
  }

  Goal copyWith({
    String? name,
    double? targetAmount,
    double? savedAmount,
    DateTime? deadline,
    bool clearDeadline = false,
    String? iconKey,
    int? color,
    String? note,
    bool? isShared,
    bool? isCompleted,
  }) {
    return Goal(
      id: id,
      name: name ?? this.name,
      targetAmount: targetAmount ?? this.targetAmount,
      savedAmount: savedAmount ?? this.savedAmount,
      deadline: clearDeadline ? null : (deadline ?? this.deadline),
      iconKey: iconKey ?? this.iconKey,
      color: color ?? this.color,
      note: note ?? this.note,
      isShared: isShared ?? this.isShared,
      isCompleted: isCompleted ?? this.isCompleted,
      createdBy: createdBy,
      createdAt: createdAt,
    );
  }

  Map<String, dynamic> toMap() => {
        'name': name,
        'targetAmount': targetAmount,
        'savedAmount': savedAmount,
        'deadline': deadline,
        'iconKey': iconKey,
        'color': color,
        'note': note,
        'isShared': isShared,
        'isCompleted': isCompleted,
        'createdBy': createdBy,
        'createdAt': createdAt,
      };

  factory Goal.fromMap(String id, Map<String, dynamic> map) {
    return Goal(
      id: id,
      name: parseString(map['name'], 'Goal'),
      targetAmount: parseDouble(map['targetAmount']),
      savedAmount: parseDouble(map['savedAmount']),
      deadline: parseDateOrNull(map['deadline']),
      iconKey: parseString(map['iconKey'], 'savings'),
      color: parseInt(map['color'], 0xFF00897B),
      note: parseString(map['note']),
      isShared: parseBool(map['isShared'], true),
      isCompleted: parseBool(map['isCompleted']),
      createdBy: parseString(map['createdBy']),
      createdAt: parseDate(map['createdAt']),
    );
  }
}

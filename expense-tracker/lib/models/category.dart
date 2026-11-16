import 'enums.dart';
import 'model_utils.dart';

class Category {
  const Category({
    required this.id,
    required this.name,
    required this.kind,
    required this.iconKey,
    required this.color,
    this.parentId,
    this.isArchived = false,
    this.sortOrder = 0,
    this.isDefault = false,
  });

  final String id;
  final String name;
  final CategoryKind kind;
  final String iconKey;
  final int color;
  final String? parentId;
  final bool isArchived;
  final int sortOrder;

  /// Default categories are created for every new household and cannot be
  /// deleted (only archived) so historical reports keep their labels.
  final bool isDefault;

  bool get isSubcategory => parentId != null;

  Category copyWith({
    String? name,
    CategoryKind? kind,
    String? iconKey,
    int? color,
    String? parentId,
    bool clearParent = false,
    bool? isArchived,
    int? sortOrder,
  }) {
    return Category(
      id: id,
      name: name ?? this.name,
      kind: kind ?? this.kind,
      iconKey: iconKey ?? this.iconKey,
      color: color ?? this.color,
      parentId: clearParent ? null : (parentId ?? this.parentId),
      isArchived: isArchived ?? this.isArchived,
      sortOrder: sortOrder ?? this.sortOrder,
      isDefault: isDefault,
    );
  }

  Map<String, dynamic> toMap() => {
        'name': name,
        'kind': kind.storageKey,
        'iconKey': iconKey,
        'color': color,
        'parentId': parentId,
        'isArchived': isArchived,
        'sortOrder': sortOrder,
        'isDefault': isDefault,
      };

  factory Category.fromMap(String id, Map<String, dynamic> map) {
    return Category(
      id: id,
      name: parseString(map['name'], 'Category'),
      kind: CategoryKind.fromKey(map['kind'] as String?),
      iconKey: parseString(map['iconKey'], 'category'),
      color: parseInt(map['color'], 0xFF6750A4),
      parentId: map['parentId'] as String?,
      isArchived: parseBool(map['isArchived']),
      sortOrder: parseInt(map['sortOrder']),
      isDefault: parseBool(map['isDefault']),
    );
  }
}

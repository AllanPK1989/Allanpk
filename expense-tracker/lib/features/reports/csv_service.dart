import 'dart:convert';

import 'package:csv/csv.dart';

import '../../core/utils/date_utils.dart';
import '../../models/models.dart';

/// CSV export / import. Import is tolerant of common bank-statement layouts:
/// it detects the date, amount (or debit/credit), description and category
/// columns by header name and lets the UI override the mapping.
class CsvService {
  CsvService._();

  static const exportHeaders = [
    'date',
    'time',
    'type',
    'amount',
    'currency',
    'category',
    'payee',
    'note',
    'account',
    'to_account',
    'tags',
    'member',
    'private',
  ];

  static String export(
    List<Transaction> txs, {
    required Map<String, Category> categories,
    required Map<String, Account> accounts,
    required Household household,
  }) {
    final rows = <List<dynamic>>[exportHeaders];
    final sorted = List.of(txs)..sort((a, b) => a.date.compareTo(b.date));
    for (final t in sorted) {
      rows.add([
        AppDates.iso.format(t.date),
        AppDates.time.format(t.date),
        t.type.storageKey,
        t.amount.toStringAsFixed(2),
        t.currency,
        categories[t.categoryId]?.name ?? '',
        t.payee,
        t.note,
        accounts[t.accountId]?.name ?? '',
        t.toAccountId == null ? '' : accounts[t.toAccountId]?.name ?? '',
        t.tags.join('|'),
        household.members[t.createdBy]?.name ?? t.createdByName,
        t.isPrivate ? 'yes' : 'no',
      ]);
    }
    return const CsvEncoder(lineDelimiter: '\n').convert(rows);
  }

  /// Parses CSV text into rows (first row = headers). Handles BOM, CRLF and
  /// semicolon-separated files.
  static ParsedCsv parse(String raw) {
    var text = raw;
    if (text.startsWith('﻿')) text = text.substring(1);
    final firstLine = text.split(RegExp(r'\r?\n')).firstWhere((l) => l.trim().isNotEmpty, orElse: () => '');
    final delimiter = firstLine.split(';').length > firstLine.split(',').length ? ';' : ',';
    final rows = CsvDecoder(fieldDelimiter: delimiter, skipEmptyLines: true)
        .convert(text.replaceAll('\r\n', '\n'));
    final nonEmpty = rows.where((r) => r.any((c) => c.toString().trim().isNotEmpty)).toList();
    if (nonEmpty.isEmpty) return const ParsedCsv(headers: [], rows: []);
    final headers = nonEmpty.first.map((h) => h.toString().trim()).toList();
    final body = nonEmpty.skip(1).map((r) => r.map((c) => c.toString()).toList()).toList();
    return ParsedCsv(headers: headers, rows: body);
  }

  /// Best-effort column detection by header keywords.
  static CsvMapping guessMapping(List<String> headers) {
    int? find(List<String> keys) {
      for (var i = 0; i < headers.length; i++) {
        final h = headers[i].toLowerCase();
        if (keys.any((k) => h == k || h.contains(k))) return i;
      }
      return null;
    }

    return CsvMapping(
      date: find(['date', 'txn date', 'transaction date', 'posted']),
      amount: find(['amount', 'value', 'sum']),
      debit: find(['debit', 'withdrawal', 'expense', 'paid out']),
      credit: find(['credit', 'deposit', 'income', 'paid in']),
      description: find(['payee', 'description', 'narration', 'particulars', 'merchant', 'details', 'memo']),
      category: find(['category']),
      note: find(['note', 'notes', 'remarks']),
      type: find(['type']),
      account: find(['account']),
    );
  }

  static DateTime? parseDate(String raw) {
    final s = raw.trim();
    if (s.isEmpty) return null;
    final iso = DateTime.tryParse(s);
    if (iso != null) return iso;
    final patterns = [
      RegExp(r'^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$'), // dd/mm/yyyy
      RegExp(r'^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})$'), // dd/mm/yy
    ];
    for (final p in patterns) {
      final m = p.firstMatch(s);
      if (m != null) {
        final d = int.parse(m.group(1)!);
        final mo = int.parse(m.group(2)!);
        var y = int.parse(m.group(3)!);
        if (y < 100) y += 2000;
        if (mo >= 1 && mo <= 12 && d >= 1 && d <= 31) return DateTime(y, mo, d);
      }
    }
    final monthName = RegExp(r'^(\d{1,2})[ \-]([A-Za-z]{3,})[ \-,]*(\d{4})$').firstMatch(s);
    if (monthName != null) {
      const months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
      final idx = months.indexOf(monthName.group(2)!.toLowerCase().substring(0, 3));
      if (idx >= 0) return DateTime(int.parse(monthName.group(3)!), idx + 1, int.parse(monthName.group(1)!));
    }
    return null;
  }

  static double? parseAmount(String raw) {
    var s = raw.trim();
    if (s.isEmpty) return null;
    final negative = s.startsWith('(') && s.endsWith(')') || s.contains('-') || s.toUpperCase().endsWith('DR');
    s = s.replaceAll(RegExp(r'[^0-9.,]'), '');
    if (s.isEmpty) return null;
    // European "1.234,56" vs "1,234.56".
    if (s.contains(',') && s.contains('.')) {
      s = s.lastIndexOf(',') > s.lastIndexOf('.') ? s.replaceAll('.', '').replaceAll(',', '.') : s.replaceAll(',', '');
    } else if (s.contains(',')) {
      final parts = s.split(',');
      s = parts.last.length == 2 ? s.replaceAll(',', '.') : s.replaceAll(',', '');
    }
    final v = double.tryParse(s);
    if (v == null) return null;
    return negative ? -v.abs() : v;
  }

  /// Converts parsed rows into transaction drafts. Rows that cannot be read
  /// are returned in [ImportResult.skipped].
  static ImportResult toDrafts(ParsedCsv csv, CsvMapping map) {
    final drafts = <ImportDraft>[];
    final skipped = <int>[];
    for (var i = 0; i < csv.rows.length; i++) {
      final r = csv.rows[i];
      String cell(int? idx) => idx == null || idx >= r.length ? '' : r[idx];
      final date = map.date == null ? null : parseDate(cell(map.date));
      double? amount;
      TransactionType? type;
      if (map.debit != null || map.credit != null) {
        final d = parseAmount(cell(map.debit));
        final c = parseAmount(cell(map.credit));
        if (d != null && d != 0) {
          amount = d.abs();
          type = TransactionType.expense;
        } else if (c != null && c != 0) {
          amount = c.abs();
          type = TransactionType.income;
        }
      }
      if (amount == null && map.amount != null) {
        final a = parseAmount(cell(map.amount));
        if (a != null && a != 0) {
          amount = a.abs();
          type = a < 0 ? TransactionType.expense : TransactionType.income;
        }
      }
      final typeText = cell(map.type).toLowerCase();
      if (typeText.contains('expense') || typeText.contains('debit')) type = TransactionType.expense;
      if (typeText.contains('income') || typeText.contains('credit')) type = TransactionType.income;
      if (date == null || amount == null) {
        skipped.add(i + 2); // 1-based with header row
        continue;
      }
      drafts.add(
        ImportDraft(
          date: date,
          amount: amount,
          type: type ?? TransactionType.expense,
          description: cell(map.description).trim(),
          categoryName: cell(map.category).trim(),
          note: cell(map.note).trim(),
          accountName: cell(map.account).trim(),
        ),
      );
    }
    return ImportResult(drafts: drafts, skipped: skipped);
  }

  static String decodeBytes(List<int> bytes) {
    try {
      return utf8.decode(bytes);
    } catch (_) {
      return latin1.decode(bytes);
    }
  }
}

class ParsedCsv {
  const ParsedCsv({required this.headers, required this.rows});
  final List<String> headers;
  final List<List<String>> rows;
}

class CsvMapping {
  const CsvMapping({
    this.date,
    this.amount,
    this.debit,
    this.credit,
    this.description,
    this.category,
    this.note,
    this.type,
    this.account,
  });

  final int? date;
  final int? amount;
  final int? debit;
  final int? credit;
  final int? description;
  final int? category;
  final int? note;
  final int? type;
  final int? account;

  bool get isUsable => date != null && (amount != null || debit != null || credit != null);

  CsvMapping copyWith({
    int? date,
    int? amount,
    int? debit,
    int? credit,
    int? description,
    int? category,
    int? note,
    int? type,
    int? account,
    bool clearAmount = false,
    bool clearDebit = false,
    bool clearCredit = false,
  }) {
    return CsvMapping(
      date: date ?? this.date,
      amount: clearAmount ? null : (amount ?? this.amount),
      debit: clearDebit ? null : (debit ?? this.debit),
      credit: clearCredit ? null : (credit ?? this.credit),
      description: description ?? this.description,
      category: category ?? this.category,
      note: note ?? this.note,
      type: type ?? this.type,
      account: account ?? this.account,
    );
  }
}

class ImportDraft {
  const ImportDraft({
    required this.date,
    required this.amount,
    required this.type,
    required this.description,
    required this.categoryName,
    required this.note,
    required this.accountName,
  });

  final DateTime date;
  final double amount;
  final TransactionType type;
  final String description;
  final String categoryName;
  final String note;
  final String accountName;
}

class ImportResult {
  const ImportResult({required this.drafts, required this.skipped});
  final List<ImportDraft> drafts;
  final List<int> skipped;
}

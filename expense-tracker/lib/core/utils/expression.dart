/// Tiny arithmetic evaluator for the amount field ("120+45*2").
/// Supports + - * / and parentheses. Returns null on malformed input.
double? evaluateExpression(String input) {
  final src = input.replaceAll(',', '').replaceAll(' ', '');
  if (src.isEmpty) return null;
  final parser = _Parser(src);
  try {
    final value = parser.parseExpression();
    if (parser.pos != src.length) return null;
    if (value.isNaN || value.isInfinite) return null;
    return value;
  } catch (_) {
    return null;
  }
}

class _Parser {
  _Parser(this.src);
  final String src;
  int pos = 0;

  double parseExpression() {
    var value = parseTerm();
    while (pos < src.length) {
      final c = src[pos];
      if (c == '+') {
        pos++;
        value += parseTerm();
      } else if (c == '-') {
        pos++;
        value -= parseTerm();
      } else {
        break;
      }
    }
    return value;
  }

  double parseTerm() {
    var value = parseFactor();
    while (pos < src.length) {
      final c = src[pos];
      if (c == '*' || c == 'x' || c == '×') {
        pos++;
        value *= parseFactor();
      } else if (c == '/' || c == '÷') {
        pos++;
        final d = parseFactor();
        if (d == 0) throw const FormatException('divide by zero');
        value /= d;
      } else {
        break;
      }
    }
    return value;
  }

  double parseFactor() {
    if (pos >= src.length) throw const FormatException('unexpected end');
    final c = src[pos];
    if (c == '(') {
      pos++;
      final v = parseExpression();
      if (pos >= src.length || src[pos] != ')') throw const FormatException('missing )');
      pos++;
      return v;
    }
    if (c == '-') {
      pos++;
      return -parseFactor();
    }
    final start = pos;
    while (pos < src.length && (RegExp(r'[0-9.]').hasMatch(src[pos]))) {
      pos++;
    }
    if (start == pos) throw const FormatException('expected number');
    return double.parse(src.substring(start, pos));
  }
}

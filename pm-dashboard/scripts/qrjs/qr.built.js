/* ---------------------------------------------------------------------------
   Minimal QR Code encoder - byte mode, error correction level H.
   No dependencies, no network. Written so the label sheets can be regenerated
   on a locked-down machine with nothing but a browser.

   Implements ISO/IEC 18004 for versions 1-40. A full Power Apps deep link
   needs version 14, so there is plenty of headroom.
--------------------------------------------------------------------------- */
(function (root) {
  "use strict";

  /* Reed-Solomon block structure for level H, versions 1-40.
     Each entry is a flat list of [blockCount, totalCodewords, dataCodewords]. */
  var RS_BLOCKS_H = [[1, 26, 9], [1, 44, 16], [2, 35, 13], [4, 25, 9], [2, 33, 11, 2, 34, 12], [4, 43, 15], [4, 39, 13, 1, 40, 14], [4, 40, 14, 2, 41, 15], [4, 36, 12, 4, 37, 13], [6, 43, 15, 2, 44, 16], [3, 36, 12, 8, 37, 13], [7, 42, 14, 4, 43, 15], [12, 33, 11, 4, 34, 12], [11, 36, 12, 5, 37, 13], [11, 36, 12, 7, 37, 13], [3, 45, 15, 13, 46, 16], [2, 42, 14, 17, 43, 15], [2, 42, 14, 19, 43, 15], [9, 39, 13, 16, 40, 14], [15, 43, 15, 10, 44, 16], [19, 46, 16, 6, 47, 17], [34, 37, 13], [16, 45, 15, 14, 46, 16], [30, 46, 16, 2, 47, 17], [22, 45, 15, 13, 46, 16], [33, 46, 16, 4, 47, 17], [12, 45, 15, 28, 46, 16], [11, 45, 15, 31, 46, 16], [19, 45, 15, 26, 46, 16], [23, 45, 15, 25, 46, 16], [23, 45, 15, 28, 46, 16], [19, 45, 15, 35, 46, 16], [11, 45, 15, 46, 46, 16], [59, 46, 16, 1, 47, 17], [22, 45, 15, 41, 46, 16], [2, 45, 15, 64, 46, 16], [24, 45, 15, 46, 46, 16], [42, 45, 15, 32, 46, 16], [10, 45, 15, 67, 46, 16], [20, 45, 15, 61, 46, 16]];

  /* Alignment pattern centre coordinates, versions 1-40. */
  var ALIGN = [[], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50], [6, 30, 54], [6, 32, 58], [6, 34, 62], [6, 26, 46, 66], [6, 26, 48, 70], [6, 26, 50, 74], [6, 30, 54, 78], [6, 30, 56, 82], [6, 30, 58, 86], [6, 34, 62, 90], [6, 28, 50, 72, 94], [6, 26, 50, 74, 98], [6, 30, 54, 78, 102], [6, 28, 54, 80, 106], [6, 32, 58, 84, 110], [6, 30, 58, 86, 114], [6, 34, 62, 90, 118], [6, 26, 50, 74, 98, 122], [6, 30, 54, 78, 102, 126], [6, 26, 52, 78, 104, 130], [6, 30, 56, 82, 108, 134], [6, 34, 60, 86, 112, 138], [6, 30, 58, 86, 114, 142], [6, 34, 62, 90, 118, 146], [6, 30, 54, 78, 102, 126, 150], [6, 24, 50, 76, 102, 128, 154], [6, 28, 54, 80, 106, 132, 158], [6, 32, 58, 84, 110, 136, 162], [6, 26, 54, 82, 110, 138, 166], [6, 30, 58, 86, 114, 142, 170]];

  var G15 = 0x537, G18 = 0x1f25, G15_MASK = 0x5412;
  var EC_LEVEL_BITS_H = 2;            /* level H is 0b10 */

  /* ---- Galois field GF(256), primitive polynomial 0x11d ---- */
  var EXP = new Array(512), LOG = new Array(256);
  (function () {
    var x = 1;
    for (var i = 0; i < 255; i++) { EXP[i] = x; LOG[x] = i; x <<= 1; if (x & 0x100) x ^= 0x11d; }
    for (var j = 255; j < 512; j++) EXP[j] = EXP[j - 255];
  })();

  function gfMul(a, b) { return (a === 0 || b === 0) ? 0 : EXP[LOG[a] + LOG[b]]; }

  function genPoly(n) {
    var poly = [1];
    for (var i = 0; i < n; i++) {
      var next = new Array(poly.length + 1).fill(0);
      for (var j = 0; j < poly.length; j++) {
        next[j] ^= gfMul(poly[j], 1);
        next[j + 1] ^= gfMul(poly[j], EXP[i]);
      }
      poly = next;
    }
    return poly;
  }

  function rsEncode(data, ecCount) {
    var gen = genPoly(ecCount);
    var rem = data.concat(new Array(ecCount).fill(0));
    for (var i = 0; i < data.length; i++) {
      var coef = rem[i];
      if (coef !== 0) for (var j = 1; j < gen.length; j++) rem[i + j] ^= gfMul(gen[j], coef);
    }
    return rem.slice(data.length);
  }

  /* ---- BCH for format and version information ---- */
  function bchDigit(d) { var n = 0; while (d !== 0) { n++; d >>>= 1; } return n; }

  function bchFormat(data) {
    var d = data << 10;
    while (bchDigit(d) - bchDigit(G15) >= 0) d ^= (G15 << (bchDigit(d) - bchDigit(G15)));
    return ((data << 10) | d) ^ G15_MASK;
  }

  function bchVersion(data) {
    var d = data << 12;
    while (bchDigit(d) - bchDigit(G18) >= 0) d ^= (G18 << (bchDigit(d) - bchDigit(G18)));
    return (data << 12) | d;
  }

  /* ---- UTF-8 ---- */
  function utf8Bytes(str) {
    var out = [];
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i);
      if (c < 0x80) out.push(c);
      else if (c < 0x800) { out.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f)); }
      else if (c < 0xd800 || c >= 0xe000) {
        out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 0x3f), 0x80 | (c & 0x3f));
      } else {                                   /* surrogate pair */
        i++;
        var cp = 0x10000 + (((c & 0x3ff) << 10) | (str.charCodeAt(i) & 0x3ff));
        out.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 0x3f),
                 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f));
      }
    }
    return out;
  }

  function blocksFor(version) {
    var spec = RS_BLOCKS_H[version - 1], out = [];
    for (var i = 0; i < spec.length; i += 3)
      for (var k = 0; k < spec[i]; k++) out.push({ total: spec[i + 1], data: spec[i + 2] });
    return out;
  }

  function dataCapacity(version) {
    return blocksFor(version).reduce(function (s, b) { return s + b.data; }, 0);
  }

  function chooseVersion(byteLen) {
    for (var v = 1; v <= RS_BLOCKS_H.length; v++) {
      var cc = v <= 9 ? 8 : 16;
      if (Math.ceil((4 + cc + 8 * byteLen) / 8) <= dataCapacity(v)) return v;
    }
    throw new Error("Payload is " + byteLen + " bytes; the largest QR code at error "
      + "correction level H holds " + (dataCapacity(RS_BLOCKS_H.length) - 3) + ".");
  }

  /* ---- final codeword stream: data + ECC, interleaved ---- */
  function buildCodewords(bytes, version) {
    var cc = version <= 9 ? 8 : 16;
    var bits = [];
    function put(num, len) { for (var i = len - 1; i >= 0; i--) bits.push((num >>> i) & 1); }

    put(4, 4);                       /* byte mode */
    put(bytes.length, cc);
    for (var i = 0; i < bytes.length; i++) put(bytes[i], 8);

    var capacityBits = dataCapacity(version) * 8;
    for (var t = 0; t < 4 && bits.length < capacityBits; t++) bits.push(0);
    while (bits.length % 8 !== 0) bits.push(0);

    var words = [];
    for (var b = 0; b < bits.length; b += 8) {
      var v = 0;
      for (var k = 0; k < 8; k++) v = (v << 1) | bits[b + k];
      words.push(v);
    }
    var pad = [0xec, 0x11], p = 0;
    while (words.length < dataCapacity(version)) words.push(pad[p++ % 2]);

    var blocks = blocksFor(version), off = 0, maxD = 0, maxE = 0;
    blocks.forEach(function (blk) {
      blk.dataWords = words.slice(off, off + blk.data);
      off += blk.data;
      blk.ecWords = rsEncode(blk.dataWords, blk.total - blk.data);
      maxD = Math.max(maxD, blk.dataWords.length);
      maxE = Math.max(maxE, blk.ecWords.length);
    });

    var out = [];
    for (var d = 0; d < maxD; d++)
      blocks.forEach(function (blk) { if (d < blk.dataWords.length) out.push(blk.dataWords[d]); });
    for (var e = 0; e < maxE; e++)
      blocks.forEach(function (blk) { if (e < blk.ecWords.length) out.push(blk.ecWords[e]); });
    return out;
  }

  /* ---- mask functions ---- */
  function maskFn(pattern, i, j) {
    switch (pattern) {
      case 0: return (i + j) % 2 === 0;
      case 1: return i % 2 === 0;
      case 2: return j % 3 === 0;
      case 3: return (i + j) % 3 === 0;
      case 4: return (Math.floor(i / 2) + Math.floor(j / 3)) % 2 === 0;
      case 5: return ((i * j) % 2) + ((i * j) % 3) === 0;
      case 6: return (((i * j) % 2) + ((i * j) % 3)) % 2 === 0;
      case 7: return (((i + j) % 2) + ((i * j) % 3)) % 2 === 0;
    }
    throw new Error("bad mask " + pattern);
  }

  /* `test` blanks the format, version and dark modules. Mask selection is
     scored on a test matrix, matching the reference implementation and the
     original ISO sample code; the chosen mask is then rendered for real. */
  function buildMatrix(version, codewords, mask, test) {
    var size = version * 4 + 17;
    var m = [];
    for (var r = 0; r < size; r++) m.push(new Array(size).fill(null));

    function finder(row, col) {
      for (var r = -1; r <= 7; r++) {
        for (var c = -1; c <= 7; c++) {
          if (row + r < 0 || size <= row + r || col + c < 0 || size <= col + c) continue;
          m[row + r][col + c] =
            (0 <= r && r <= 6 && (c === 0 || c === 6)) ||
            (0 <= c && c <= 6 && (r === 0 || r === 6)) ||
            (2 <= r && r <= 4 && 2 <= c && c <= 4);
        }
      }
    }
    finder(0, 0); finder(size - 7, 0); finder(0, size - 7);

    /* alignment patterns first - their centres can sit on the timing line */
    var pos = ALIGN[version - 1];
    for (var a = 0; a < pos.length; a++) {
      for (var b = 0; b < pos.length; b++) {
        var row = pos[a], col = pos[b];
        if (m[row][col] !== null) continue;
        for (var r2 = -2; r2 <= 2; r2++)
          for (var c2 = -2; c2 <= 2; c2++)
            m[row + r2][col + c2] =
              r2 === -2 || r2 === 2 || c2 === -2 || c2 === 2 || (r2 === 0 && c2 === 0);
      }
    }

/* timing pattern fills only what alignment left free */
    for (var i = 8; i < size - 8; i++) {
      if (m[i][6] === null) m[i][6] = i % 2 === 0;
      if (m[6][i] === null) m[6][i] = i % 2 === 0;
    }

    if (version >= 7) {
      var vbits = bchVersion(version);
      for (var k = 0; k < 18; k++) {
        var bit = !test && ((vbits >> k) & 1) === 1;
        m[Math.floor(k / 3)][k % 3 + size - 8 - 3] = bit;
        m[k % 3 + size - 8 - 3][Math.floor(k / 3)] = bit;
      }
    }

    var fbits = bchFormat((EC_LEVEL_BITS_H << 3) | mask);
    for (var f = 0; f < 15; f++) {
      var fb = !test && ((fbits >> f) & 1) === 1;
      if (f < 6) m[f][8] = fb;
      else if (f < 8) m[f + 1][8] = fb;
      else m[size - 15 + f][8] = fb;

      if (f < 8) m[8][size - f - 1] = fb;
      else if (f < 9) m[8][15 - f - 1 + 1] = fb;
      else m[8][15 - f - 1] = fb;
    }
    m[size - 8][8] = !test;                       /* dark module */

    var inc = -1, row2 = size - 1, bitIndex = 7, byteIndex = 0;
    for (var col = size - 1; col > 0; col -= 2) {
      if (col === 6) col--;
      for (;;) {
        for (var c3 = 0; c3 < 2; c3++) {
          if (m[row2][col - c3] === null) {
            var dark = false;
            if (byteIndex < codewords.length)
              dark = ((codewords[byteIndex] >>> bitIndex) & 1) === 1;
            if (maskFn(mask, row2, col - c3)) dark = !dark;
            m[row2][col - c3] = dark;
            bitIndex--;
            if (bitIndex === -1) { byteIndex++; bitIndex = 7; }
          }
        }
        row2 += inc;
        if (row2 < 0 || size <= row2) { row2 -= inc; inc = -inc; break; }
      }
    }
    return m;
  }

  /* ---- mask penalty, ISO/IEC 18004 rules 1-4 ----
     Rule 1: runs of 5+ same-colour modules in a row or column score (n - 2).
     Rule 2: each uniform 2x2 block scores 3.
     Rule 3: the 1:1:3:1:1 finder-like pattern with a 4-module light margin
             (10111010000 or 00001011101) scores 40.
     Rule 4: every 5% the dark ratio departs from 50% scores 10, floored. */
  function penalty(m) {
    var n = m.length, score = 0, r, c;

    /* rule 1 - horizontal runs then vertical runs */
    for (r = 0; r < n; r++) {
      var prev = m[r][0], run = 0;
      for (c = 0; c < n; c++) {
        if (m[r][c] === prev) run++;
        else { if (run >= 5) score += run - 2; run = 1; prev = m[r][c]; }
      }
      if (run >= 5) score += run - 2;
    }
    for (c = 0; c < n; c++) {
      var prevC = m[0][c], runC = 0;
      for (r = 0; r < n; r++) {
        if (m[r][c] === prevC) runC++;
        else { if (runC >= 5) score += runC - 2; runC = 1; prevC = m[r][c]; }
      }
      if (runC >= 5) score += runC - 2;
    }

    /* rule 2 */
    for (r = 0; r < n - 1; r++) {
      for (c = 0; c < n - 1; c++) {
        var a = m[r][c];
        if (a === m[r][c + 1] && a === m[r + 1][c] && a === m[r + 1][c + 1]) score += 3;
      }
    }

    /* rule 3 */
    for (r = 0; r < n; r++) {
      var t = m[r];
      for (c = 0; c + 10 < n; c++) {
        if (!t[c + 1] && t[c + 4] && !t[c + 5] && t[c + 6] && !t[c + 9] &&
            ((t[c] && t[c + 2] && t[c + 3] && !t[c + 7] && !t[c + 8] && !t[c + 10]) ||
             (!t[c] && !t[c + 2] && !t[c + 3] && t[c + 7] && t[c + 8] && t[c + 10])))
          score += 40;
      }
    }
    for (c = 0; c < n; c++) {
      for (r = 0; r + 10 < n; r++) {
        if (!m[r + 1][c] && m[r + 4][c] && !m[r + 5][c] && m[r + 6][c] && !m[r + 9][c] &&
            ((m[r][c] && m[r + 2][c] && m[r + 3][c] && !m[r + 7][c] && !m[r + 8][c] && !m[r + 10][c]) ||
             (!m[r][c] && !m[r + 2][c] && !m[r + 3][c] && m[r + 7][c] && m[r + 8][c] && m[r + 10][c])))
          score += 40;
      }
    }

    /* rule 4 */
    var dark = 0;
    for (r = 0; r < n; r++) for (c = 0; c < n; c++) if (m[r][c]) dark++;
    score += Math.floor(Math.abs((dark / (n * n)) * 100 - 50) / 5) * 10;

    return score;
  }

  /* ---- public API ---- */
  function encode(text, forcedMask) {
    var bytes = utf8Bytes(text);
    var version = chooseVersion(bytes.length);
    var codewords = buildCodewords(bytes, version);

    if (forcedMask !== undefined && forcedMask !== null)
      return { version: version, mask: forcedMask,
               modules: buildMatrix(version, codewords, forcedMask, false) };

    var bestScore = Infinity, bestMask = 0;
    for (var k = 0; k < 8; k++) {
      var s = penalty(buildMatrix(version, codewords, k, true));
      if (s < bestScore) { bestScore = s; bestMask = k; }
    }
    return {
      version: version,
      mask: bestMask,
      modules: buildMatrix(version, codewords, bestMask, false)
    };
  }

  /* SVG at 1 module = 1 unit, so the caller scales with width/height */
  function toSvg(text, border, dark, light) {
    var q = encode(text);
    var n = q.modules.length, b = border === undefined ? 4 : border, dim = n + b * 2;
    var path = [];
    for (var r = 0; r < n; r++) {
      for (var c = 0; c < n; c++) {
        if (q.modules[r][c]) path.push("M" + (c + b) + "," + (r + b) + "h1v1h-1z");
      }
    }
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + dim + ' ' + dim +
      '" shape-rendering="crispEdges" role="img">' +
      '<rect width="' + dim + '" height="' + dim + '" fill="' + (light || "#ffffff") + '"/>' +
      '<path d="' + path.join("") + '" fill="' + (dark || "#000000") + '"/></svg>';
  }

  root.QR = {
    encode: encode, toSvg: toSvg, version: "1.0",
    /* exposed so the build can verify against a reference implementation */
    _test: { chooseVersion: chooseVersion, buildCodewords: buildCodewords,
             utf8Bytes: utf8Bytes, blocksFor: blocksFor, dataCapacity: dataCapacity,
             rsEncode: rsEncode, penalty: penalty }
  };
})(typeof module !== "undefined" && module.exports ? module.exports : window);

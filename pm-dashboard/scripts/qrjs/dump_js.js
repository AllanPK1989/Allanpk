const QR = require('./qr.built.js').QR;
const payloads = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = {};
for (const p of payloads) {
  out[p] = {};
  for (let m = 0; m < 8; m++) {
    const q = QR.encode(p, m);
    out[p][m] = q.modules.map(r => r.map(v => v ? 1 : 0).join('')).join('|');
  }
  const auto = QR.encode(p);
  out[p].auto = auto.mask;
  out[p].version = auto.version;
}
process.stdout.write(JSON.stringify(out));

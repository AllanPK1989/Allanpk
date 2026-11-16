// Minimal, dependency-free reader for the first worksheet of an .xlsx file.
// Enough for government data exports (Canada's LMIA employer lists). It never
// writes extracted files to disk and caps decompressed sizes (zip-bomb guard).
// XML is read with regular expressions, so DTDs/external entities are never
// processed (no XXE).

import zlib from 'node:zlib';
import { decodeEntities } from './text.js';

const MAX_ENTRY_BYTES = 200 * 1024 * 1024;

export function readZipEntries(buffer) {
  const buf = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  const EOCD = 0x06054b50;
  let eocd = -1;
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 65557); i--) {
    if (buf.readUInt32LE(i) === EOCD) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error('Not a ZIP/XLSX file (no end-of-central-directory record)');
  const entryCount = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16);
  const entries = new Map();
  for (let k = 0; k < entryCount; k++) {
    if (p + 46 > buf.length || buf.readUInt32LE(p) !== 0x02014b50) {
      throw new Error('Corrupt ZIP central directory');
    }
    const method = buf.readUInt16LE(p + 10);
    const compSize = buf.readUInt32LE(p + 20);
    const size = buf.readUInt32LE(p + 24);
    const nameLen = buf.readUInt16LE(p + 28);
    const extraLen = buf.readUInt16LE(p + 30);
    const commentLen = buf.readUInt16LE(p + 32);
    const localOffset = buf.readUInt32LE(p + 42);
    const name = buf.toString('utf8', p + 46, p + 46 + nameLen);
    p += 46 + nameLen + extraLen + commentLen;
    if (compSize === 0xffffffff || localOffset === 0xffffffff) throw new Error('ZIP64 files are not supported');
    entries.set(name, () => {
      if (size > MAX_ENTRY_BYTES) throw new Error(`ZIP entry ${name} is too large`);
      if (buf.readUInt32LE(localOffset) !== 0x04034b50) throw new Error('Corrupt ZIP local header');
      const start = localOffset + 30 + buf.readUInt16LE(localOffset + 26) + buf.readUInt16LE(localOffset + 28);
      const data = buf.subarray(start, start + compSize);
      if (method === 0) return Buffer.from(data);
      if (method === 8) return zlib.inflateRawSync(data, { maxOutputLength: MAX_ENTRY_BYTES });
      throw new Error(`Unsupported ZIP compression method ${method}`);
    });
  }
  return entries;
}

function xmlText(fragment) {
  let out = '';
  for (const m of fragment.matchAll(/<t\b[^>]*>([\s\S]*?)<\/t>/g)) out += m[1];
  return decodeEntities(out);
}

function columnIndex(letters) {
  let n = 0;
  for (const ch of letters) n = n * 26 + (ch.charCodeAt(0) - 64);
  return n - 1;
}

function firstSheetPath(entries) {
  const read = (name) => (entries.has(name) ? entries.get(name)().toString('utf8') : null);
  const workbook = read('xl/workbook.xml');
  const rels = read('xl/_rels/workbook.xml.rels');
  if (workbook && rels) {
    const sheet = workbook.match(/<sheet\b[^>]*\br:id="([^"]+)"/);
    if (sheet) {
      const rel = [...rels.matchAll(/<Relationship\b[^>]*>/g)]
        .map((m) => m[0])
        .find((tag) => tag.includes(`Id="${sheet[1]}"`));
      const target = rel && rel.match(/Target="([^"]+)"/);
      if (target) {
        const t = target[1].replace(/^\//, '');
        const path = t.startsWith('xl/') ? t : `xl/${t}`;
        if (entries.has(path)) return path;
      }
    }
  }
  if (entries.has('xl/worksheets/sheet1.xml')) return 'xl/worksheets/sheet1.xml';
  throw new Error('No worksheet found in XLSX file');
}

// Returns rows as arrays of strings (empty cells are '').
export function readFirstSheet(buffer) {
  const entries = readZipEntries(buffer);
  const shared = [];
  if (entries.has('xl/sharedStrings.xml')) {
    const xml = entries.get('xl/sharedStrings.xml')().toString('utf8');
    for (const m of xml.matchAll(/<si\b[^>]*>([\s\S]*?)<\/si>/g)) shared.push(xmlText(m[1]));
  }
  const sheet = entries.get(firstSheetPath(entries))().toString('utf8');
  const rows = [];
  for (const rowMatch of sheet.matchAll(/<row\b[^>]*>([\s\S]*?)<\/row>/g)) {
    const row = [];
    for (const c of rowMatch[1].matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
      const attrs = c[1];
      const inner = c[2] || '';
      const ref = attrs.match(/\br="([A-Z]+)\d+"/);
      const col = ref ? columnIndex(ref[1]) : row.length;
      const type = (attrs.match(/\bt="([^"]+)"/) || [])[1];
      const v = inner.match(/<v>([\s\S]*?)<\/v>/);
      let value = '';
      if (type === 's' && v) value = shared[Number(v[1])] ?? '';
      else if (type === 'inlineStr') value = xmlText(inner);
      else if (v) value = decodeEntities(v[1]);
      while (row.length < col) row.push('');
      row[col] = value;
    }
    rows.push(row);
  }
  return rows;
}

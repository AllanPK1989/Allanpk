import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { parseUkRegister, parseIndRegister, collectLmiaRows, lmiaEntries, parseImportedRows, Registers } from '../server/registers.js';
import { readFirstSheet } from '../server/lib/xlsx.js';
import { buildXlsx } from './helpers/xlsx-builder.js';

// Same header and quirks (leading spaces, T/A, several routes per org) as the
// real gov.uk CSV.
const UK_CSV = [
  'Organisation Name,Town/City,County,Type & Rating,Route',
  ' Siemens Energy Limited,Newcastle Upon Tyne,,Worker (A rating),Skilled Worker',
  ' Siemens Energy Limited,Newcastle Upon Tyne,,Worker (A rating),Global Business Mobility: Senior or Specialist Worker',
  ' BRANOS OXFORD LTD T/A LILO,Oxford,,Worker (A rating),Skilled Worker',
  'St Example Church,Leeds,,Worker (A rating),Tier 2 Ministers of Religion',
  '"Comma, Engineering Ltd",Derby,,Worker (B rating),Skilled Worker',
].join('\n');

// Same structure as ind.nl's register table.
const IND_HTML = `<table><thead><tr><th scope="col">Organisation</th><th scope="col">KVK (Chamber of Commerce) number</th></tr></thead>
<tbody><tr><th scope="row">Tata Steel Nederland B.V.</th><td>34005278</td></tr><tr><th scope="row">A&amp;S System Integrators B.V.</th><td>12345678</td></tr></tbody></table>`;

test('UK register: merges routes, keeps employment routes only, notes B-rating', () => {
  const entries = parseUkRegister(UK_CSV);
  const names = entries.map((e) => e[0]);
  assert.deepEqual(names.sort(), ['BRANOS OXFORD LTD T/A LILO', 'Comma, Engineering Ltd', 'Siemens Energy Limited']);
  const siemens = entries.find((e) => e[0] === 'Siemens Energy Limited');
  assert.match(siemens[1], /Skilled Worker/);
  assert.match(siemens[1], /Global Business Mobility/);
  assert.match(entries.find((e) => e[0].startsWith('Comma'))[1], /B-rated/);
  assert.throws(() => parseUkRegister('Name,City\nX,Y'), /columns not recognised/);
});

test('IND register: parses table rows and decodes entities', () => {
  assert.deepEqual(parseIndRegister(IND_HTML), [
    ['Tata Steel Nederland B.V.', 'KvK 34005278'],
    ['A&S System Integrators B.V.', 'KvK 12345678'],
  ]);
  assert.throws(() => parseIndRegister('<html>changed</html>'), /format not recognised/);
});

test('Canada LMIA: finds the header row, skips title and footnotes, merges quarters', () => {
  const q1 = readFirstSheet(buildXlsx([
    ['Employers Who Were Issued a Positive LMIA, April to June 2026'],
    ['Province/Territory', 'Program Stream', 'Employer', 'Address', 'Occupation', 'Incorporate Status', 'Approved LMIAs', 'Approved Positions'],
    ['Newfoundland and Labrador   ', 'High Wage   ', 'DOF Subsea Canada Corp.', 'Paradise, NL', '21399-Other professional engineers, n.e.c.', 'Unknown', 1, 1],
    ['Alberta', 'High Wage', 'Prairie Mills Ltd.', 'Calgary, AB', '72400-Construction millwrights and industrial mechanics', 'Unknown', 1, 2],
    ['3. The employer name is manually entered in the system.'],
  ]));
  const q2 = readFirstSheet(buildXlsx([
    ['Province/Territory', 'Program Stream', 'Employer', 'Address', 'Occupation', 'Incorporate Status', 'Approved LMIAs', 'Approved Positions'],
    ['Alberta', 'High Wage', 'Prairie Mills Ltd.', 'Calgary, AB', '22301-Mechanical engineering technologists', 'Unknown', 1, 3],
  ]));
  const acc = collectLmiaRows(q2, collectLmiaRows(q1));
  const entries = Object.fromEntries(lmiaEntries(acc));
  assert.deepEqual(Object.keys(entries).sort(), ['DOF Subsea Canada Corp.', 'Prairie Mills Ltd.']);
  assert.match(entries['Prairie Mills Ltd.'], /5 approved positions/);
  assert.match(entries['Prairie Mills Ltd.'], /industrial mechanics/);
  assert.match(entries['Prairie Mills Ltd.'], /Mechanical engineering technologists/);
});

test('manual import: detects employer column and sums approvals (USCIS-style)', () => {
  const rows = [
    ['Fiscal Year', 'Employer (Petitioner) Name', 'Petitioner City', 'Petitioner State', 'Initial Approval', 'Continuing Approval'],
    ['2025', 'ACME RELIABILITY INC', 'HOUSTON', 'TX', '3', '1,200'],
    ['2025', 'ACME RELIABILITY INC', 'HOUSTON', 'TX', '1', '0'],
  ];
  assert.deepEqual(parseImportedRows(rows), [['ACME RELIABILITY INC', 'HOUSTON, TX · 1204 approvals']]);
  assert.throws(() => parseImportedRows([['a', 'b'], ['1', '2']]), /No column/);
});

test('Registers: imports files from the import folder and looks up by country', async (t) => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'vjf-reg-'));
  t.after(() => fs.rm(dir, { recursive: true, force: true }));
  const regs = new Registers(dir);
  await regs.load();
  await fs.writeFile(path.join(regs.importDir, 'us-h1b-2025.csv'), 'Employer,State\nAcme Reliability Inc,TX\n');
  await fs.writeFile(path.join(regs.importDir, 'in-list.csv'), 'Employer\nShould Not Load Ltd\n');
  await fs.writeFile(path.join(regs.importDir, 'notes.csv'), 'Employer\nNo Country Code Ltd\n');
  const results = await regs.importManual();
  assert.equal(results.filter((r) => r.ok).length, 1);
  assert.equal(results.filter((r) => !r.ok).length, 2);

  const hit = regs.lookup('ACME Reliability', 'US');
  assert.equal(hit.matchedName, 'Acme Reliability Inc');
  assert.equal(regs.lookup('ACME Reliability', 'GB'), null);
  assert.equal(regs.hasCountry('US'), true);

  // Reload from disk.
  const again = new Registers(dir);
  await again.load();
  assert.ok(again.lookup('Acme Reliability Incorporated', 'US'));

  // Removing the source file removes the register.
  await fs.rm(path.join(regs.importDir, 'us-h1b-2025.csv'));
  await again.importManual();
  assert.equal(again.lookup('Acme Reliability', 'US'), null);
});

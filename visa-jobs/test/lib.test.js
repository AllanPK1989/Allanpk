import { test } from 'node:test';
import assert from 'node:assert/strict';
import { htmlToText, decodeEntities, isHttpUrl, excerptAround } from '../server/lib/text.js';
import { parseCsv, decodeTextFile, detectDelimiter } from '../server/lib/csv.js';
import { readFirstSheet } from '../server/lib/xlsx.js';
import { normalizeCompany, companyAliases } from '../server/lib/company.js';
import { parseLocation, parseEligibility, countryFromText } from '../server/lib/countries.js';
import { buildXlsx } from './helpers/xlsx-builder.js';

test('htmlToText strips tags, decodes entities and handles double-escaped HTML', () => {
  assert.equal(htmlToText('<p>Hello <strong>world</strong></p><p>Line&nbsp;2 &amp; more</p>'), 'Hello world\nLine 2 & more');
  // Seen on Arbeitnow: HTML escaped twice.
  assert.equal(htmlToText('&lt;p&gt;This position is NOT eligible for Visa sponsorship.&lt;/p&gt;'), 'This position is NOT eligible for Visa sponsorship.');
  assert.equal(htmlToText('<ul><li>One</li><li>Two</li></ul>'), '• One\n• Two');
  assert.equal(htmlToText('<script>alert(1)</script>ok'), 'ok');
  assert.equal(decodeEntities('&#8364; &#x20AC; &euro; &bogus;'), '€ € € &bogus;');
});

test('isHttpUrl only accepts http(s)', () => {
  assert.ok(isHttpUrl('https://example.com/job/1'));
  assert.ok(!isHttpUrl('javascript:alert(1)'));
  assert.ok(!isHttpUrl('data:text/html,hi'));
  assert.ok(!isHttpUrl('not a url'));
});

test('excerptAround returns the containing sentence', () => {
  const t = 'We build rockets. Relocation assistance is provided including visa sponsorship. Apply now.';
  const i = t.indexOf('visa sponsorship');
  assert.equal(excerptAround(t, i, 16), 'Relocation assistance is provided including visa sponsorship.');
});

test('CSV parser handles quotes, commas, newlines, BOM and UTF-16', () => {
  const csv = '﻿Organisation Name,Town/City,Route\r\n"Acme, Ltd","Lon\ndon",Skilled Worker\n"Say ""hi"" Ltd",Leeds,Skilled Worker\n';
  const rows = parseCsv(decodeTextFile(Buffer.from(csv)));
  assert.deepEqual(rows, [
    ['Organisation Name', 'Town/City', 'Route'],
    ['Acme, Ltd', 'Lon\ndon', 'Skilled Worker'],
    ['Say "hi" Ltd', 'Leeds', 'Skilled Worker'],
  ]);
  const utf16 = Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from('Employer\tState\nACME INC\tTX\n', 'utf16le')]);
  const text = decodeTextFile(utf16);
  assert.equal(detectDelimiter(text), '\t');
  assert.deepEqual(parseCsv(text), [['Employer', 'State'], ['ACME INC', 'TX']]);
});

test('XLSX reader reads shared strings, numbers and gaps', () => {
  const buf = buildXlsx([['Title row'], ['Employer', 'Positions'], ['Acme & Sons Inc.', 3], ['', 1]]);
  assert.deepEqual(readFirstSheet(buf), [['Title row'], ['Employer', 'Positions'], ['Acme & Sons Inc.', '3'], ['', '1']]);
  assert.throws(() => readFirstSheet(Buffer.from('not a zip at all, definitely not')), /ZIP/);
});

test('company names normalise legal forms, accents and punctuation', () => {
  assert.equal(normalizeCompany('Siemens Energy Limited'), 'siemens energy');
  assert.equal(normalizeCompany('Siemens Energy'), 'siemens energy');
  assert.equal(normalizeCompany('Tata Steel Nederland B.V.'), 'tata steel');
  assert.equal(normalizeCompany('AtkinsRéalis UK Ltd'), 'atkinsrealis');
  assert.equal(normalizeCompany('The Jacobs Group (UK) Ltd'), 'jacobs');
  assert.equal(normalizeCompany('A&S System Integrators B.V.'), 'a and s system integrators');
  assert.equal(normalizeCompany('Group'), 'group');
  // Don't over-strip: "UK" in the middle is meaningful.
  assert.equal(normalizeCompany('UK Power Networks'), 'uk power networks');
});

test('register lines with trading names and "including" produce aliases', () => {
  assert.deepEqual(companyAliases(' BRANOS OXFORD LTD T/A LILO'), ['branos oxford', 'lilo']);
  assert.deepEqual(companyAliases('Siemens Holdings plc (including Siemens plc)'), ['siemens']);
  assert.deepEqual(companyAliases('Acme Ltd (trading as Acme Engineering)').sort(), ['acme', 'acme engineering']);
});

test('locations resolve to countries (real Arbeitnow-style strings)', () => {
  const cases = {
    'Munich, Germany': 'DE',
    'London, England, United Kingdom': 'GB',
    'Zürich Oerlikon, Zürich, Switzerland': 'CH',
    'Amsterdam, Noord-Holland, Nederland': 'NL',
    'Berlin (Hybrid)': 'DE',
    'Hub - Berlin': 'DE',
    'EMEA - UK': 'GB',
    'Darmstadt, DE': 'DE',
    '🇪🇺 Germany (remote)': 'DE',
    'Bern Lorraine, Bern, Schweiz': 'CH',
    'Bengaluru, Karnataka': 'IN',
    'Paradise, NL A1L 3B3': null, // ambiguous on its own; not guessed
  };
  for (const [loc, expected] of Object.entries(cases)) {
    if (expected === null) continue;
    assert.equal(parseLocation(loc).country, expected, loc);
  }
  assert.equal(parseLocation('Remote').remote, true);
  assert.equal(parseLocation('Homeoffice').remote, true);
});

test('country can be inferred from posting text as a fallback', () => {
  assert.equal(countryFromText('Wir sind ein Unternehmen in Deutschland mit Sitz in Bayern. Deutschland!'), 'DE');
  assert.equal(countryFromText('No country here'), null);
});

test('remote eligibility: India-only jobs are flagged, India is dropped from lists', () => {
  assert.deepEqual(parseEligibility('USA, Canada, USA timezones'), { countries: ['US', 'CA'], regions: [], indiaOnly: false });
  assert.deepEqual(parseEligibility('Worldwide'), { countries: [], regions: ['worldwide'], indiaOnly: false });
  assert.equal(parseEligibility('India').indiaOnly, true);
  assert.deepEqual(parseEligibility('APAC, India'), { countries: [], regions: ['apac'], indiaOnly: false });
});

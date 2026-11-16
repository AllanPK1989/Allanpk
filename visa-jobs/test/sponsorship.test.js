import { test } from 'node:test';
import assert from 'node:assert/strict';
import { analyseText, verdict } from '../server/lib/sponsorship.js';

// Phrases taken from real postings (Arbeitnow visa feed, Nov 2026).
const POSITIVE = [
  'Relocation assistance is provided for those willing to relocate including visa sponsorship where applicable.',
  'A Relocation Package : Includes visa support for those who need it',
  'Our package includes visa assistance, destination services to help you and your family settle in.',
  'We may be able to provide visa sponsorship to the US, depending on the circumstances.',
  'Comprehensive relocation package (including visa support)',
  'Unterstützung beim Visum, falls erforderlich',
  'Visa sponsorship is available for this role.',
  'We are happy to sponsor a Skilled Worker visa for the right candidate.',
  'We sponsor visas and help with the move.',
];

const NEGATIVE = [
  'This position is NOT eligible for Visa sponsorship.',
  'Applicants must already hold a valid visa or work permit, as Hilo is not able to provide visa sponsorship.',
  'A UK work permit. We do not sponsor visas.',
  'we are unable to offer visa sponsorship for this position; applicants must have the right to work',
  'You must have the right to work in the UK.',
  'Candidates must be authorised to work in the EU without sponsorship.',
  'No sponsorship is available.',
];

const NEITHER = [
  'We will not proceed with applications from candidates who are unable to obtain the required visa within the programme timeline.',
  'Exceptional work doesn’t require relocation or fixed office hours.',
  'We do not discriminate on the basis of race, religion or national origin.',
  'Natuvion relocation services include data migration.',
];

test('positive sponsorship statements are detected', () => {
  for (const p of POSITIVE) assert.ok(analyseText(p).positive, `expected positive: ${p}`);
});

test('negative sponsorship statements are detected and not mistaken for positives', () => {
  for (const n of NEGATIVE) {
    const a = analyseText(n);
    assert.ok(a.negative, `expected negative: ${n}`);
    assert.equal(a.positive, null, `should not be positive: ${n}`);
  }
});

test('unrelated sentences give no sponsorship signal', () => {
  for (const s of NEITHER) {
    const a = analyseText(s);
    assert.equal(a.positive, null, s);
    assert.equal(a.negative, null, s);
    assert.equal(a.relocation, null, s);
  }
});

test('relocation help is a weaker signal', () => {
  const a = analyseText('We welcome applications from talent worldwide and provide relocation support to Hamburg.');
  assert.ok(a.relocation);
  assert.equal(a.positive, null);
  assert.equal(analyseText('Relocation support is not provided.').relocation, null);
});

test('security clearance is flagged as a caution', () => {
  assert.equal(analyseText('Candidates must hold SC clearance.').cautions.length, 1);
});

test('verdict: the posting text beats the employer register', () => {
  const register = { short: 'UK licensed sponsor', matchedName: 'Acme Ltd' };
  assert.equal(verdict({ text: 'Great job.', register }).level, 'licensed');
  assert.equal(verdict({ text: 'We do not sponsor visas.', register }).level, 'no');
  assert.equal(verdict({ text: 'Visa sponsorship available.', register }).level, 'stated');
  assert.ok(verdict({ text: 'Visa sponsorship available.', register }).score > verdict({ text: 'Visa sponsorship available.' }).score);
});

test('verdict: feed tags and Adzuna keyword matches rank below text and registers', () => {
  assert.equal(verdict({ text: 'Nice role', feedTagged: true }).level, 'tagged');
  assert.equal(verdict({ text: 'This position is NOT eligible for Visa sponsorship.', feedTagged: true }).level, 'no');
  assert.equal(verdict({ text: 'Nice role', keywordMatched: true }).level, 'keyword');
  assert.equal(verdict({ text: 'Nice role' }).level, 'unknown');
});

test('verdict: mixed statements stay positive but are marked', () => {
  const v = verdict({ text: 'We can sponsor visas to Germany; for any other country, you need to have existing right to work.' });
  assert.equal(v.level, 'stated');
  assert.equal(v.mixed, true);
  assert.equal(v.negativeEvidence, null); // same sentence, not repeated
});

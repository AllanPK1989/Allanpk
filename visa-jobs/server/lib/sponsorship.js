// Reads a posting's own words for visa-sponsorship signals.
//
// Real postings say both "visa sponsorship available" and "This position is NOT
// eligible for visa sponsorship" (both seen in Arbeitnow's *visa-sponsorship*
// feed), so negative statements are detected explicitly and every positive
// match is checked for a nearby negation before it counts.

import { excerptAround } from './text.js';

const NEGATION_BEFORE = /\b(?:no|not|never|cannot|can ?not|unable|without|nor|neither)\b|n['’]t\b/i;
// "Relocation support is not provided", "visa support isn't available"
const NEGATION_AFTER = /^\s*(?:is|are|will be|can be|would be)?\s*(?:not\b|n['’]t\b|unavailable\b)|^\s*(?:isn|aren|won)['’]t\b/i;

const POSITIVE = [
  /\bvisa[- ](?:sponsorship|support|assistance)\b(?:\s+(?:is|will be|can be))?\s+(?:available|offered|provided|possible|considered|supported|included)/i,
  /\b(?:offer|offers|offering|provide|provides|providing|including|includes|include|with|plus|incl\.?)\b[^.;:\n]{0,40}?\bvisa[- ](?:sponsorship|support|assistance|sponsoring)\b/i,
  /\b(?:sponsorship|sponsoring)\s+(?:is\s+)?(?:available|provided|offered)\b/i,
  /\b(?:can|will|could|able to|happy to|willing to|glad to|open to)\s+(?:offer\s+|provide\s+)?(?:visa\s+|work permit\s+)?sponsor(?:ship|ing)?\b/i,
  /\bsponsor(?:ship)?\s+(?:for|of)\s+(?:a\s+|the\s+|your\s+|an\s+)?(?:skilled worker|work|employment|h-?1b|eu blue card|blue card|tss|482|visa|work permit)/i,
  /\b(?:skilled worker|tier 2|h-?1b|blue card|work permit|employment pass)\s+(?:visa\s+)?(?:sponsorship|sponsoring|support|assistance)\b/i,
  /\b(?:support|assistance|help)\s+with\s+(?:your\s+|the\s+)?(?:visa|work permit|immigration)/i,
  /\bwe\s+(?:also\s+|gladly\s+|do\s+)?sponsor\s+(?:visas?|work permits?|skilled worker)/i,
  /\bopen to\s+(?:candidates|applicants|people|talent)\b[^.;\n]{0,40}?\b(?:need|needs|require|requires)\b[^.;\n]{0,30}?\b(?:visa|sponsorship)\b/i,
  /\bvisa\s+(?:and|&)\s+relocation\s+(?:support|assistance|package|help)/i,
  /\brelocation\s+(?:and|&)\s+visa\s+(?:support|assistance|help)/i,
  /\bvisa[- ]?(?:unterst[uü]tzung|sponsoring)\b/i,
  /\b(?:unterst[uü]tzung|hilfe)\s+(?:bei|beim)\s+(?:dem\s+|der\s+)?(?:visum|visa|visumsantrag|arbeitserlaubnis|aufenthaltstitel)/i,
];

const NOT = String.raw`(?:not|cannot|can ?not|unable to|won['’]?t|will not|do not|don['’]?t|does not|doesn['’]?t|are not able to|is not able to|aren['’]?t able to|isn['’]?t)`;

const NEGATIVE = [
  // "NOT eligible for visa sponsorship", "we do not sponsor visas", "unable to offer sponsorship"
  new RegExp(String.raw`\b${NOT}\b[^.;:\n]{0,50}?\bsponsor\w*\b`, 'i'),
  // "cannot provide visas" / "unable to support work permits" (but not "unable to obtain the required visa")
  new RegExp(String.raw`\b${NOT}\s+(?:\w+\s+){0,3}?(?:provide|offer|support|arrange|help with|assist with)\s+(?:\w+\s+){0,2}?(?:visas?|work permits?)\b`, 'i'),
  /\bno\s+(?:visa\s+|work permit\s+)?sponsorship\b/i,
  /\bsponsorship\s+(?:is\s+)?(?:not|unavailable)\b/i,
  /\bwithout\s+(?:the\s+)?(?:need\s+(?:for|of)\s+)?(?:(?:visa|employer|company|current or future)\s+)?sponsorship\b/i,
  /\b(?:must|should|need to|needs to|required to)\s+(?:already\s+)?(?:have|hold|possess)\s+(?:a\s+|the\s+|an\s+)?(?:valid\s+|existing\s+|current\s+|full\s+|unrestricted\s+|permanent\s+)*(?:right to work|work permit|work authori[sz]ation|working rights|work rights|visa)\b/i,
  /\b(?:eu|eea|us|u\.s\.|uk)\s+citizens?\s+only\b/i,
  /\bonly\s+(?:eu|eea|us|u\.s\.|uk)\s+citizens\b/i,
  /\bkein(?:e|en)?\s+(?:visa|visum)[- ]?(?:sponsoring|unterst[uü]tzung)\b/i,
];

const RELOCATION = [
  /\brelocation\s+(?:support|assistance|package|allowance|bonus|help|budget|costs?|reimbursement)\b/i,
  /\b(?:support|assist|help)(?:s|ing)?\s+(?:you\s+)?(?:with\s+)?(?:your\s+)?(?:relocation|relocating|your move|the move)\b/i,
  /\brelocation\s+(?:is\s+)?(?:available|offered|provided|covered|paid)\b/i,
  /\b(?:cover|pay for|reimburse)\s+(?:your\s+)?relocation\b/i,
  /\bumzugs?(?:unterst[uü]tzung|kosten|hilfe)\b/i,
];

const CAUTION = [
  [/\b(?:sc|dv|nv\d?|security|government)\s+clearance\b|\bsecurity[- ]cleared\b/i, 'Needs security clearance (often limited to citizens or long-term residents)'],
  [/\bcitizenship\s+(?:is\s+)?required\b|\bmust be a (?:us|u\.s\.|uk|eu|canadian|australian) citizen\b/i, 'Asks for citizenship'],
];

function firstMatch(regexes, text, { checkNegation }) {
  for (const re of regexes) {
    const m = re.exec(text);
    if (!m) continue;
    if (checkNegation) {
      const before = text.slice(Math.max(0, m.index - 35), m.index);
      const after = text.slice(m.index + m[0].length, m.index + m[0].length + 30);
      if (NEGATION_BEFORE.test(before) || NEGATION_BEFORE.test(m[0]) || NEGATION_AFTER.test(after)) continue;
    }
    return excerptAround(text, m.index, m[0].length);
  }
  return null;
}

// Returns { positive, negative, relocation } as evidence excerpts (or null),
// plus a list of caution notes.
export function analyseText(text) {
  const t = String(text ?? '');
  return {
    positive: firstMatch(POSITIVE, t, { checkNegation: true }),
    negative: firstMatch(NEGATIVE, t, { checkNegation: false }),
    relocation: firstMatch(RELOCATION, t, { checkNegation: true }),
    cautions: CAUTION.filter(([re]) => re.test(t)).map(([, note]) => note),
  };
}

// Combine posting text, feed flags and register matches into one verdict.
// Levels, strongest first:
//   stated     posting says sponsorship is available
//   licensed   employer is on the official sponsor register for that country
//   tagged     the job board lists it under "visa sponsorship"
//   relocation posting offers relocation help (often comes with visa help)
//   keyword    Adzuna matched visa/sponsor words in the full ad (not visible here)
//   unknown    nothing either way
//   no         posting says it does not sponsor
export const LEVELS = ['stated', 'licensed', 'tagged', 'relocation', 'keyword', 'unknown', 'no'];
const SCORE = { stated: 60, licensed: 50, tagged: 40, relocation: 25, keyword: 20, unknown: 0, no: -100 };

export function verdict({ text, feedTagged = false, keywordMatched = false, register = null }) {
  const a = analyseText(text);
  let level;
  if (a.positive) level = 'stated';
  else if (a.negative) level = 'no';
  else if (register) level = 'licensed';
  else if (feedTagged) level = 'tagged';
  else if (a.relocation) level = 'relocation';
  else if (keywordMatched) level = 'keyword';
  else level = 'unknown';

  let score = SCORE[level];
  if (level !== 'no') {
    if (register && level !== 'licensed') score += 8;
    if (feedTagged && level !== 'tagged') score += 4;
    if (a.relocation && level !== 'relocation') score += 3;
  }
  if (a.cautions.length) score -= 10;

  return {
    level,
    score,
    evidence: a.positive || a.negative || a.relocation || null,
    mixed: Boolean(a.positive && a.negative),
    // Only shown separately when the "no" part is a different sentence.
    negativeEvidence: a.positive && a.negative && a.negative !== a.positive ? a.negative : null,
    cautions: a.cautions,
    register,
    feedTagged,
    keywordMatched,
  };
}

// Which levels each filter setting shows.
export const FILTERS = {
  likely: new Set(['stated', 'licensed', 'tagged']),
  signals: new Set(['stated', 'licensed', 'tagged', 'relocation', 'keyword']),
  all: new Set(['stated', 'licensed', 'tagged', 'relocation', 'keyword', 'unknown']),
};

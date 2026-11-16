// Country metadata and free-text location -> country inference.
// India (IN) is recognised here only so that jobs located there can be excluded.

import { foldText } from './text.js';

export const EXCLUDED_COUNTRY = 'IN';

// adzuna: Adzuna's country code, if Adzuna covers it (India is never queried).
// visaInfo: official government page about work visas (links checked Nov 2026).
export const COUNTRIES = [
  { code: 'GB', name: 'United Kingdom', adzuna: 'gb', currency: 'GBP', visaInfo: 'https://www.gov.uk/skilled-worker-visa', visaName: 'Skilled Worker visa' },
  { code: 'IE', name: 'Ireland', currency: 'EUR', visaInfo: 'https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/permit-types/', visaName: 'Employment permits' },
  { code: 'DE', name: 'Germany', adzuna: 'de', currency: 'EUR', visaInfo: 'https://www.make-it-in-germany.com/en/working-in-germany/job-search-application/professions-in-demand/engineers', visaName: 'Make it in Germany (EU Blue Card, skilled workers)' },
  { code: 'NL', name: 'Netherlands', adzuna: 'nl', currency: 'EUR', visaInfo: 'https://ind.nl/en/residence-permits/work/highly-skilled-migrant', visaName: 'Highly skilled migrant permit' },
  { code: 'BE', name: 'Belgium', adzuna: 'be', currency: 'EUR' },
  { code: 'FR', name: 'France', adzuna: 'fr', currency: 'EUR' },
  { code: 'CH', name: 'Switzerland', adzuna: 'ch', currency: 'CHF' },
  { code: 'AT', name: 'Austria', adzuna: 'at', currency: 'EUR' },
  { code: 'ES', name: 'Spain', adzuna: 'es', currency: 'EUR' },
  { code: 'IT', name: 'Italy', adzuna: 'it', currency: 'EUR' },
  { code: 'PL', name: 'Poland', adzuna: 'pl', currency: 'PLN' },
  { code: 'PT', name: 'Portugal', currency: 'EUR' },
  { code: 'LU', name: 'Luxembourg', currency: 'EUR' },
  { code: 'DK', name: 'Denmark', currency: 'DKK' },
  { code: 'SE', name: 'Sweden', currency: 'SEK' },
  { code: 'NO', name: 'Norway', currency: 'NOK' },
  { code: 'FI', name: 'Finland', currency: 'EUR' },
  { code: 'CZ', name: 'Czechia', currency: 'CZK' },
  { code: 'US', name: 'United States', adzuna: 'us', currency: 'USD', visaInfo: 'https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations', visaName: 'H-1B specialty occupations' },
  { code: 'CA', name: 'Canada', adzuna: 'ca', currency: 'CAD', visaInfo: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada.html', visaName: 'Work in Canada (work permits)' },
  { code: 'MX', name: 'Mexico', adzuna: 'mx', currency: 'MXN' },
  { code: 'BR', name: 'Brazil', adzuna: 'br', currency: 'BRL' },
  { code: 'AU', name: 'Australia', adzuna: 'au', currency: 'AUD', visaInfo: 'https://immi.homeaffairs.gov.au/visas/working-in-australia/temporary-work-visas', visaName: 'Temporary work visas (incl. Skills in Demand 482)' },
  { code: 'NZ', name: 'New Zealand', adzuna: 'nz', currency: 'NZD', visaInfo: 'https://www.immigration.govt.nz/visas/accredited-employer-work-visa/', visaName: 'Accredited Employer Work Visa' },
  { code: 'SG', name: 'Singapore', adzuna: 'sg', currency: 'SGD', visaInfo: 'https://www.mom.gov.sg/passes-and-permits/employment-pass', visaName: 'Employment Pass' },
  { code: 'ZA', name: 'South Africa', adzuna: 'za', currency: 'ZAR' },
  { code: 'AE', name: 'United Arab Emirates', currency: 'AED' },
  { code: 'SA', name: 'Saudi Arabia', currency: 'SAR' },
  { code: 'QA', name: 'Qatar', currency: 'QAR' },
  { code: 'JP', name: 'Japan', currency: 'JPY' },
];

export const COUNTRY_BY_CODE = new Map(COUNTRIES.map((c) => [c.code, c]));
export const ADZUNA_COUNTRIES = COUNTRIES.filter((c) => c.adzuna);

export function flagEmoji(code) {
  if (!/^[A-Z]{2}$/.test(code || '')) return '';
  return String.fromCodePoint(...[...code].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65));
}

// Names, native names, sub-national regions and common cities -> ISO code.
// Keys are matched after foldText() (lowercase, accents removed).
const PLACE_GROUPS = {
  GB: 'united kingdom, uk, great britain, britain, england, scotland, wales, northern ireland, london, manchester, birmingham, bristol, leeds, glasgow, edinburgh, liverpool, cambridge, oxford, belfast, cardiff, sheffield, newcastle, newcastle upon tyne, nottingham, reading, aberdeen, southampton, leicester, coventry, milton keynes, derby, plymouth, swindon, york, bath, brighton, warrington, preston, hull, sunderland, stoke on trent, ipswich, norwich, peterborough, slough, guildford, crawley, basingstoke, swansea, dundee, inverness, greater london, west midlands, south east england, north west england, yorkshire',
  IE: 'ireland, eire, republic of ireland, dublin, cork, galway, limerick, waterford',
  DE: 'germany, deutschland, de, berlin, munich, munchen, hamburg, frankfurt, frankfurt am main, cologne, koln, stuttgart, dusseldorf, dortmund, essen, leipzig, bremen, dresden, hannover, hanover, nuremberg, nurnberg, bochum, darmstadt, aachen, karlsruhe, mannheim, bonn, munster, heidelberg, wiesbaden, mainz, augsburg, regensburg, ingolstadt, wolfsburg, kiel, potsdam, freiburg, ulm, erlangen, jena, duisburg, wuppertal, bielefeld, braunschweig, chemnitz, magdeburg, rostock, kassel, saarbrucken, bayern, bavaria, hessen, sachsen, saxony, nordrhein westfalen, north rhine westphalia, baden wurttemberg, niedersachsen, lower saxony, brandenburg, thuringen, schleswig holstein, rheinland pfalz',
  NL: 'netherlands, the netherlands, nederland, holland, amsterdam, rotterdam, the hague, den haag, s gravenhage, utrecht, eindhoven, groningen, delft, leiden, haarlem, tilburg, breda, nijmegen, arnhem, enschede, maastricht, amersfoort, almere, schiphol, hoofddorp, zwolle, apeldoorn, venlo, noord holland, north holland, zuid holland, south holland, noord brabant, north brabant, gelderland, overijssel, limburg nl, zeeland, flevoland, drenthe, friesland',
  BE: 'belgium, belgique, belgie, brussels, bruxelles, brussel, antwerp, antwerpen, ghent, gent, leuven, liege, mechelen, charleroi, bruges, brugge, flanders, wallonia',
  FR: 'france, paris, lyon, marseille, toulouse, nice, nantes, bordeaux, lille, strasbourg, grenoble, montpellier, rennes, sophia antipolis, ile de france',
  CH: 'switzerland, schweiz, suisse, svizzera, zurich, geneva, geneve, genf, basel, bern, berne, lausanne, lucerne, luzern, zug, st gallen, winterthur, lugano, baar, aargau',
  AT: 'austria, osterreich, vienna, wien, graz, linz, salzburg, innsbruck, klagenfurt',
  ES: 'spain, espana, madrid, barcelona, valencia, seville, sevilla, malaga, bilbao, zaragoza',
  IT: 'italy, italia, milan, milano, rome, roma, turin, torino, bologna, florence, firenze, naples, napoli',
  PL: 'poland, polska, warsaw, warszawa, krakow, cracow, wroclaw, gdansk, poznan, lodz, katowice',
  PT: 'portugal, lisbon, lisboa, porto',
  LU: 'luxembourg, luxemburg',
  DK: 'denmark, danmark, copenhagen, kobenhavn, aarhus, odense',
  SE: 'sweden, sverige, stockholm, gothenburg, goteborg, malmo, uppsala',
  NO: 'norway, norge, oslo, bergen, stavanger, trondheim',
  FI: 'finland, suomi, helsinki, espoo, tampere, oulu',
  CZ: 'czechia, czech republic, prague, praha, brno',
  US: 'united states, united states of america, usa, us, u s, america, new york, new york city, nyc, san francisco, los angeles, seattle, boston, chicago, austin, houston, dallas, denver, atlanta, miami, washington dc, san jose, san diego, philadelphia, phoenix, detroit, pittsburgh, minneapolis, portland, salt lake city, raleigh, charlotte, nashville, california, texas, florida, new jersey, massachusetts, illinois, ohio, michigan, pennsylvania, georgia us, north carolina, virginia, colorado, arizona, louisiana, oklahoma, alaska, wyoming',
  CA: 'canada, toronto, vancouver, montreal, calgary, edmonton, ottawa, winnipeg, halifax, quebec, quebec city, mississauga, saskatoon, regina, victoria bc, ontario, alberta, british columbia, saskatchewan, manitoba, nova scotia, new brunswick, newfoundland, newfoundland and labrador',
  MX: 'mexico, mexico city, ciudad de mexico, monterrey, guadalajara',
  BR: 'brazil, brasil, sao paulo, rio de janeiro, belo horizonte',
  AU: 'australia, sydney, melbourne, brisbane, perth, adelaide, canberra, darwin, hobart, gold coast, newcastle nsw, new south wales, nsw, victoria, queensland, qld, western australia, south australia, tasmania, northern territory',
  NZ: 'new zealand, aotearoa, auckland, wellington, christchurch, hamilton nz, dunedin, tauranga',
  SG: 'singapore',
  ZA: 'south africa, johannesburg, cape town, durban, pretoria',
  AE: 'united arab emirates, uae, dubai, abu dhabi, sharjah',
  SA: 'saudi arabia, ksa, riyadh, jeddah, dammam, neom',
  QA: 'qatar, doha',
  JP: 'japan, tokyo, osaka, yokohama, kyoto',
  IN: 'india, bharat, bangalore, bengaluru, mumbai, bombay, pune, hyderabad, chennai, madras, delhi, new delhi, gurgaon, gurugram, noida, kolkata, calcutta, ahmedabad, kochi, cochin, coimbatore, trivandrum, thiruvananthapuram, jaipur, chandigarh, indore, nagpur, vadodara, visakhapatnam, madurai, tiruchirappalli, mysore, mysuru, mangalore, bhubaneswar, lucknow, karnataka, maharashtra, tamil nadu, kerala, telangana, gujarat, west bengal, uttar pradesh, haryana, andhra pradesh, odisha',
};

const PLACE_TO_CODE = new Map();
for (const [code, list] of Object.entries(PLACE_GROUPS)) {
  for (const raw of list.split(',')) {
    const key = foldText(raw);
    if (key && !PLACE_TO_CODE.has(key)) PLACE_TO_CODE.set(key, code);
  }
}

// Broad regions used by remote-job feeds.
const REGION_WORDS = new Set([
  'worldwide', 'anywhere', 'global', 'remote', 'europe', 'eu', 'eea', 'emea', 'apac', 'latam',
  'americas', 'north america', 'asia', 'middle east', 'africa', 'oceania', 'cet', 'utc',
]);

export function countryFromPlace(text) {
  const key = foldText(text);
  if (!key) return null;
  if (PLACE_TO_CODE.has(key)) return PLACE_TO_CODE.get(key);
  const upper = String(text).trim().toUpperCase();
  if (/^[A-Z]{2}$/.test(upper) && (COUNTRY_BY_CODE.has(upper) || upper === EXCLUDED_COUNTRY)) return upper;
  if (upper === 'UK') return 'GB';
  return null;
}

// Infer a country from a location string such as "Munich, Germany",
// "London, England, United Kingdom", "Zürich Oerlikon, Zürich, Switzerland",
// "Berlin (Hybrid)" or "EMEA - UK". Returns { country, remote }.
export function parseLocation(location) {
  const raw = String(location ?? '');
  const remote = /\b(remote|home ?office|homeoffice|work from home|wfh|anywhere)\b/i.test(raw);
  const cleaned = raw
    .replace(/[\u{1F1E6}-\u{1F1FF}\u{1F300}-\u{1FAFF}]/gu, ' ')
    .replace(/\((?:hybrid|remote|on-?site|office|hq)[^)]*\)/gi, ' ')
    .replace(/\b(?:hub|office|hybrid|remote job|remote|homeoffice|home office|on-?site)\b/gi, ' ');
  const parts = cleaned.split(/[,/|;()]| - | – /).map((p) => p.trim()).filter(Boolean);
  // Most specific signal is usually last ("City, Region, Country").
  for (let i = parts.length - 1; i >= 0; i--) {
    const code = countryFromPlace(parts[i]);
    if (code) return { country: code, remote };
  }
  // Try word n-grams inside each part ("Zürich Oerlikon" -> "zurich").
  for (let i = parts.length - 1; i >= 0; i--) {
    const words = foldText(parts[i]).split(' ');
    for (let size = Math.min(3, words.length); size >= 1; size--) {
      for (let start = 0; start + size <= words.length; start++) {
        const phrase = words.slice(start, start + size).join(' ');
        if (phrase.length < 3 && size === 1) continue;
        const code = PLACE_TO_CODE.get(phrase);
        if (code) return { country: code, remote };
      }
    }
  }
  return { country: null, remote };
}

// Fallback for postings whose location is a small town: count country names
// (not cities, which are too ambiguous) mentioned in the text and take the most
// frequent. Returns null when nothing is mentioned.
const COUNTRY_NAME_RE = new RegExp(
  '\\b(' + [
    'united kingdom', 'england', 'scotland', 'wales', 'ireland', 'germany', 'deutschland',
    'netherlands', 'nederland', 'belgium', 'belgie', 'france', 'switzerland', 'schweiz', 'suisse',
    'austria', 'osterreich', 'spain', 'espana', 'italy', 'italia', 'poland', 'polska', 'portugal',
    'luxembourg', 'denmark', 'sweden', 'norway', 'finland', 'czech republic', 'czechia',
    'united states', 'usa', 'canada', 'mexico', 'brazil', 'australia', 'new zealand', 'singapore',
    'south africa', 'india', 'united arab emirates', 'saudi arabia', 'qatar', 'japan',
  ].join('|') + ')\\b', 'g');

export function countryFromText(text) {
  const counts = new Map();
  for (const m of foldText(text).matchAll(COUNTRY_NAME_RE)) {
    const code = PLACE_TO_CODE.get(m[1]);
    if (code) counts.set(code, (counts.get(code) || 0) + 1);
  }
  let best = null;
  for (const [code, n] of counts) if (!best || n > best[1]) best = [code, n];
  return best ? best[0] : null;
}

// For remote-job feeds: "USA, Canada", "Worldwide", "LATAM, Europe, USA".
// Returns { countries: [...codes], regions: [...words], indiaOnly: bool }.
export function parseEligibility(text) {
  const parts = String(text ?? '').split(/[,;/|]|\band\b/i).map((p) => p.trim()).filter(Boolean);
  const countries = new Set();
  const regions = new Set();
  for (const part of parts) {
    const folded = foldText(part).replace(/\b(timezones?|time zones?|only|based|residents?)\b/g, '').trim();
    if (!folded) continue;
    const code = countryFromPlace(folded) || parseLocation(part).country;
    if (code) countries.add(code);
    else if (REGION_WORDS.has(folded)) regions.add(folded);
  }
  const indiaOnly = countries.size === 1 && countries.has(EXCLUDED_COUNTRY) && regions.size === 0;
  countries.delete(EXCLUDED_COUNTRY);
  return { countries: [...countries], regions: [...regions], indiaOnly };
}

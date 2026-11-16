# Visa Job Finder

A personal job-search app that runs on your own computer. It finds jobs **outside India** and
ranks them by how likely they are to come with **visa sponsorship**. It:

- reads each ad for what it actually says ("visa sponsorship available", "NOT eligible for visa
  sponsorship", "relocation support"), and shows you the sentence it relied on;
- checks the employer against **official sponsor registers**: the UK Home Office register of
  licensed sponsors, the Netherlands IND recognised-sponsor register, Canada's positive-LMIA
  employer lists, and any other country's list you import (for example US H-1B employers);
- hides ads that say they won't sponsor, and anything located in India;
- keeps a **tracker** of jobs you save (status, notes, CSV export).

Default searches are set up for maintenance and reliability roles (reliability engineer,
maintenance planner, condition monitoring, asset integrity, Instandhaltung…). You can type any
other keywords too.

## Quick start

You need [Node.js](https://nodejs.org/) 20.12 or newer (22 LTS recommended). There's nothing to
install: the app has no npm dependencies.

```bash
cd visa-jobs
cp .env.example .env        # then add your Adzuna key (see below)
npm start
```

Open **http://localhost:8080**. On first start the app downloads the official sponsor registers in
the background (about 15 MB, a few seconds). They refresh automatically every 7 days, or press
**Update now** on the *Sponsor lists* tab.

### Get a free Adzuna key (strongly recommended)

Most maintenance and reliability jobs come from Adzuna, which covers the UK, US, Canada,
Australia, New Zealand, Singapore, Germany, the Netherlands, France, Switzerland, Austria, Belgium,
Spain, Italy, Poland, Mexico, Brazil and South Africa. Without a key you only get Arbeitnow, whose
visa feed is mostly tech jobs in Europe.

1. Sign up at <https://developer.adzuna.com/signup> (free, no card).
2. Copy the **Application ID** and **Application Key** into `.env`:
   ```
   ADZUNA_APP_ID=your-id
   ADZUNA_APP_KEY=your-key
   ```
3. Restart the app.

Each country you search uses one Adzuna request, and results are cached for 6 hours, so
repeating a search is free. `ADZUNA_DAILY_LIMIT` (default 250) stops the app before it goes over
your plan's daily allowance. Check the real limit in your Adzuna account and set it at or below
that.

### Docker (optional)

```bash
cd visa-jobs
mkdir -p data               # on Linux, so the folder is owned by you
docker compose up -d --build
```

The port is published only to this computer (`127.0.0.1:8080`). Saved jobs and registers live in
`visa-jobs/data/`.

## How a job is judged

| Badge | Meaning |
|---|---|
| **Sponsorship offered** | The ad itself says visa sponsorship or visa support is available. |
| **Licensed sponsor** | The employer is on that country's official sponsor list. The ad is silent, so ask whether *this* role is sponsored. |
| **Listed as visa-sponsored** | The job board (Arbeitnow) files it under visa sponsorship, but the text doesn't say so. |
| **Relocation help** | The ad offers relocation support, which often comes with visa help. |
| **Mentions visa/sponsor** | Adzuna found those words in the full ad (Adzuna only shares a snippet). Read the wording on the job page. |
| **No sponsorship info** | Nothing either way. Shown only with *Sponsorship: everything*. |
| *Says no sponsorship* | Hidden. The count of hidden ads is shown above the results. |

The ad's own words always beat the register. A licensed employer whose ad says "we cannot
sponsor" is hidden. **Sponsorship filter** levels: *Likely sponsors* shows the first three badges;
*Any visa or relocation signal* adds relocation and keyword matches; *Everything except "no
sponsorship"* shows all.

In countries with an official list (UK, Netherlands, Canada, plus imports) Adzuna returns every
matching job and the app checks employers itself. Elsewhere it asks Adzuna for ads whose full text
mentions visa, sponsorship or relocation. You can change this under *Sources and Adzuna options*.

Search tips:
- Use `-word` to exclude: the reliability preset is `Reliability engineer -site -software`, which
  drops software "Site Reliability Engineer" jobs.
- English keywords also match common German titles (maintenance → Instandhaltung/Wartung,
  engineer → Ingenieur, technician → Techniker/Mechaniker…).

### What a register match does and doesn't mean

- **UK**: the employer holds a Home Office sponsor licence for Skilled Worker or Global Business
  Mobility routes. Religious, charity, sports and creative-only licences are ignored. B-rated
  licences are marked.
- **Netherlands**: the employer is an IND recognised sponsor (needed for the highly skilled migrant
  permit).
- **Canada**: the employer received a positive LMIA in the last four published quarters. The
  matched occupations are shown.
- **Imported lists**: whatever the file says.

Names are matched after removing legal suffixes (Ltd, plc, B.V., GmbH, Inc…), so "Siemens
Energy" matches "Siemens Energy Limited". Matching is exact otherwise, so a few employers that
use a very different trading name will be missed. That's deliberate: a false "licensed" badge
would be worse.

### Adding US H-1B employers (or any other country)

USCIS blocks automated downloads, so import it by hand:

1. Open the [USCIS H-1B Employer Data Hub](https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub),
   pick a fiscal year and export the CSV.
2. Rename it to start with the country code, e.g. `us-h1b-2025.csv`.
3. Put it in `visa-jobs/data/registers/import/` and press **Update now** (or restart).

Any CSV/TSV/XLSX works if it has a column named like *Employer*, *Petitioner*, *Organisation*
or *Company*. UTF-16 and tab-separated files are handled. Delete the file to remove the list.

## Coverage and limits

- **Not covered by any source here:** Gulf countries (UAE, Saudi Arabia, Qatar), Japan, and
  Ireland except via Arbeitnow. They appear in the country list but rarely return jobs.
- **Australia, New Zealand, Singapore, Germany and most of the EU** publish no employer list, so
  jobs there rely on the ad's wording (and Adzuna's full-text filter).
- Adzuna only shares the first few hundred characters of each ad. "No sponsorship" wording further
  down can only be seen on the job page.
- Visa rules and salary thresholds change. The *Visa info* tab links to each government's own
  pages. This app is not legal advice.

## Privacy and security

- Everything runs and is stored on your computer (`data/`: saved jobs, cache, registers). Nothing
  is sent anywhere except the job and register requests themselves.
- The server listens on `127.0.0.1` only, rejects requests for other host names, and refuses
  cross-site writes, so other websites can't use it through your browser.
- Your Adzuna key stays on the server. It never reaches the browser and is masked in error
  messages.

## Behind a corporate proxy

Node's built-in `fetch` ignores `HTTPS_PROXY` unless told otherwise. On Node 22.21+ start it with:

```bash
NODE_USE_ENV_PROXY=1 npm start
```

## Commands

| Command | What it does |
|---|---|
| `npm start` | Run the app |
| `npm test` | Run the tests (no network needed) |
| `npm run update-registers` | Download all sponsor registers now (`-- gb ca` for some) |

## Data sources and terms

- [Adzuna API](https://developer.adzuna.com/): free key; personal use per its terms.
- [Arbeitnow job board API](https://www.arbeitnow.com/blog/job-board-api): free, cached for 2 hours, linked back.
- [Remotive](https://remotive.com/api-documentation) and [Jobicy](https://jobi.cy/apidocs): remote
  jobs, only fetched when *Include remote jobs* is on, cached for 6 hours, credited with links to
  the original posting.
- [UK register of licensed sponsors](https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers): Open Government Licence.
- [IND public register of recognised sponsors](https://ind.nl/en/public-register-recognised-sponsors/public-register-regular-labour-and-highly-skilled-migrants).
- [Canada positive LMIA employers](https://open.canada.ca/data/en/dataset/90fed587-1364-4f33-a9ee-208181dc0b97): Open Government Licence – Canada.

# Expense & Budget Manager

A fast, good-looking web app for tracking spending, planning budgets and
sharing a household ledger with your family. Built with Flutter (web) on top of
Firebase Authentication, Firestore and Storage.

> **Status:** web app. The codebase is Flutter, so Android/iOS builds remain
> possible later, but no store packaging is included.

## Features

**Ledger**
- Expenses, income and transfers with categories, sub-categories, payees,
  notes, tags and receipt photos
- Amount field accepts arithmetic (`120+45*2`), multi-currency entry with
  automatic conversion to the household currency
- Recurring rules (daily / weekly / monthly / yearly, every N periods) that post
  themselves on schedule and never drift off the 31st
- Swipe or click to duplicate, edit, delete; full-text search; rich filters

**Budgets & goals**
- Monthly, weekly, quarterly, yearly or custom budgets per category, per
  account, per member or overall, with rollover and alert thresholds
- Live progress rings, pace vs. even-spend line, daily allowance and projection
- Savings goals with deadlines, suggested monthly contribution and one-tap
  contributions recorded as transfers

**Analysis**
- Dashboard: balance hero, income/expense comparison, budget strip, daily
  trend, top categories, insights, goals, recent activity
- Insights tab: overview (daily line vs. previous period, six-month
  income/expense bars, forecast), categories (interactive donut, sub-category
  drill-down, period-over-period change), members, patterns (weekday averages,
  biggest day, no-spend days, top merchants, spend by account)
- Plain-language observations generated from the data

**Family sharing**
- Households with owner / adult / child roles, 8-character invite codes,
  multiple households per user with instant switching
- Shared vs. private accounts, budgets, goals and transactions
- Activity feed: who added, edited or removed what

**Reports & data**
- PDF report with charts and tables (preview, print or download)
- Excel workbook with Summary, Transactions, Categories, Budgets, Accounts and
  Members sheets
- CSV export and a three-step CSV import that understands bank statements
  (debit/credit columns, dd/mm/yyyy, European decimals, duplicate detection)

**Quality of life**
- Offline-first: Firestore caches everything in the browser and syncs later
- Light / dark / system theme, eight accent colours, amount masking
- Responsive: phone layout, two-column dashboard and navigation rail on wide
  screens, centred frame on very large monitors
- Keyboard shortcuts: `N` new transaction, `/` search, `1`–`5` tabs
- Installable as a PWA (manifest + icons)

## Quick start

```bash
cd expense-tracker
flutter pub get
flutterfire configure --platforms=web      # once, see SETUP.md
firebase deploy --only firestore,storage   # once
flutter run -d chrome
```

Full instructions, including emulator-only development and Firebase Hosting
deployment, are in [SETUP.md](SETUP.md).

## Project layout

```
lib/
  main.dart                 bootstrap, Firebase init, emulator switch
  app.dart                  MaterialApp, theme, responsive frame
  router.dart               go_router routes and auth redirects
  core/                     theme, constants, formatting, shared widgets
  models/                   plain Dart models (no Firebase imports)
  data/                     Firestore repositories (users, households, ledger)
  services/                 auth, currency rates, storage, browser helpers
  features/
    auth/ onboarding/       sign-in, sign-up, first-run household setup
    home/                   dashboard, period selector, navigation shell
    transactions/           list, editor, detail, search, pickers
    budgets/ goals/         budgets and savings goals
    analytics/              pure analytics engine + charts + insights screen
    accounts/ categories/ recurring/
    household/              family, members, invites, activity feed
    reports/                PDF, Excel, CSV builders and screens
    settings/               profile, appearance, alerts, household, security
test/                       unit tests (analytics, dates, money, CSV,
                            recurrence) and widget tests
firestore.rules             membership-based security rules
firestore.indexes.json      composite indexes used by the queries
storage.rules               receipt upload rules
firebase.json               hosting, rules, emulator ports
```

### Data model (Firestore)

```
users/{uid}                     profile, activeHouseholdId, householdIds
households/{hid}                name, baseCurrency, memberIds[], members{}, inviteCode
  accounts/{id}  categories/{id}  transactions/{id}
  budgets/{id}   goals/{id}       recurring/{id}   activity/{id}
invites/{code}                  → householdId
```

Transactions store the amount in the household currency plus the original
amount, currency and rate. Private entries carry `isPrivate: true` and are only
queried by their creator.

## Development

```bash
flutter analyze
flutter test
flutter build web --release
```

CI (`.github/workflows/expense-tracker-web.yml`) runs the same three commands
and uploads the web bundle as an artifact; with a service-account secret it
also deploys to Firebase Hosting.

## Licences

Application code: see repository licence. Inter font: SIL Open Font License
(`assets/fonts/OFL-Inter.txt`). Third-party Dart packages: see
`flutter pub deps` and the in-app *About → Open-source licences* page.

# Setup guide

Everything you need to run **Expense & Budget Manager** locally and publish it
to the web. Budget about 20 minutes for the Firebase steps the first time.

## 1. Prerequisites

| Tool | Why | Install |
|---|---|---|
| Flutter 3.50+ (stable) | Builds the web app | https://docs.flutter.dev/get-started/install |
| Node.js 20+ | Firebase CLI | https://nodejs.org |
| Firebase CLI | Deploy rules, indexes and hosting; run emulators | `npm install -g firebase-tools` |
| FlutterFire CLI | Generates `lib/firebase_options.dart` | `dart pub global activate flutterfire_cli` |
| Chrome | Run and debug the web build | — |

Check: `flutter doctor` should show *Chrome - develop for the web* with a tick.

## 2. Create the Firebase project

1. Go to https://console.firebase.google.com and **Add project** (any name,
   analytics optional).
2. **Authentication → Sign-in method**: enable **Email/Password**, **Google**
   and (optionally) **Apple**. Google works out of the box on the web; Apple
   needs an Apple Developer account and a Services ID, so skip it for now if
   you do not have one.
3. **Authentication → Settings → Authorized domains**: `localhost` is already
   there. Add your Firebase Hosting domain later (it is added automatically
   when you deploy hosting from the same project).
4. **Firestore Database → Create database**: choose *production mode* and a
   region close to your users (for example `asia-south1` for India).
5. **Storage → Get started** (receipt images). Default settings are fine.

## 3. Link the app to the project

From the `expense-tracker/` directory:

```bash
firebase login
flutterfire configure --platforms=web
```

Pick your project when asked. This overwrites `lib/firebase_options.dart` with
real values (the shipped file only contains placeholders, and the app shows a
setup screen until it is replaced). Commit the generated file; the web API key
is not a secret, access is controlled by the security rules below.

Then bind the Firebase CLI to the project:

```bash
cp .firebaserc.example .firebaserc      # then edit the project id inside
# or simply: firebase use --add
```

## 4. Deploy security rules and indexes

```bash
firebase deploy --only firestore,storage
```

This publishes `firestore.rules`, `firestore.indexes.json` and `storage.rules`.
The indexes take a minute or two to build; until then the transaction list may
show a "query requires an index" error with a link that creates the same index.

## 5. Run locally

```bash
flutter pub get
flutter run -d chrome
```

Sign up with an email address, create a household and start adding
transactions. Open the same URL in a second browser profile and join with the
invite code to try family sharing.

### Local development without touching production data

The repo ships an emulator configuration. In one terminal:

```bash
firebase emulators:start --only auth,firestore,storage --project demo-expense-budget
```

In another:

```bash
flutter run -d chrome --dart-define=USE_EMULATORS=true
```

Emulator data is in-memory; add `--export-on-exit=emulator-data --import=emulator-data`
to the emulator command to keep it between runs. The Emulator UI is at
http://localhost:4000.

### Automated checks

```bash
flutter analyze && flutter test        # unit and widget tests
```

`e2e/` holds a browser test that runs the real web build against the
emulators: sign-up, transactions, budgets, insights, PDF/Excel/CSV downloads
and a second family member joining by invite code. See `e2e/README.md`.

## 6. Publish to the web (Firebase Hosting)

```bash
flutter build web --release
firebase deploy --only hosting
```

The CLI prints the live URL (`https://<project-id>.web.app`). `firebase.json`
already serves `build/web`, rewrites every path to `index.html` (so deep links
work) and sets long cache headers for hashed assets.

### Continuous deployment (optional)

`.github/workflows/expense-tracker-web.yml` analyses, tests and builds the app
on every push. To make it deploy automatically from the default branch:

1. In the Firebase console → Project settings → Service accounts, click
   **Generate new private key**.
2. In GitHub → repository Settings → Secrets and variables → Actions:
   * secret `FIREBASE_SERVICE_ACCOUNT` = the JSON file contents
   * variable `FIREBASE_PROJECT_ID` = your project id

Alternatively run `firebase init hosting:github` once, which creates the same
secret for you.

### Custom domain

Firebase console → Hosting → **Add custom domain** and follow the DNS steps.
Afterwards add the domain under Authentication → Settings → Authorized domains
so Google sign-in pop-ups work from it.

## 7. Optional extras

* **Exchange rates** come from https://api.frankfurter.app (free, no key). If
  the site is unreachable the app falls back to the last cached table, or 1:1
  with a visible note.
* **Browser notifications** for budget alerts are opt-in under *More → Alerts*.
* **Backups**: Firestore has scheduled backups under Firestore → Backups, or
  use *Reports → CSV* for a portable copy of any period.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Connect Firebase to get started" screen | `lib/firebase_options.dart` still has placeholders; run `flutterfire configure --platforms=web`. |
| Google sign-in pop-up closes immediately | Enable Google under Authentication → Sign-in method; make sure the current domain is in *Authorized domains*. |
| `operation-not-allowed` on sign-up | Enable Email/Password under Authentication → Sign-in method. |
| Transactions never load, console says *requires an index* | `firebase deploy --only firestore` (or click the link in the error). |
| `permission-denied` after joining a household | Rules not deployed, or you deployed before the member was added. Re-run step 4 and reload. |
| Receipt upload fails | Storage not enabled, or `storage.rules` not deployed. |
| PDF preview is blank | Use *Download* or *Print*; the in-app preview rasterises pages with pdf.js and some browsers block it. |

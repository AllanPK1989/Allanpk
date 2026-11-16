# End-to-end test

Drives the real web build in Chromium against the Firebase emulator suite:
sign-up, onboarding, transactions, budgets, insights, PDF/Excel/CSV exports
and two-person family sharing (invite code, live sync, activity feed), then
the owner removing the second member, whose open session moves to onboarding
or to their other household.

```bash
# 1. Emulators (from expense-tracker/)
firebase emulators:start --only auth,firestore,storage --project demo-expense-budget

# 2. A web build pointed at the emulators, served on :8088
flutter build web --release --dart-define=USE_EMULATORS=true -o build/web-emu
python3 -m http.server 8088 --directory build/web-emu

# 3. The test
cd e2e
npm install
npx playwright install chromium   # first time only
npm test
```

Screenshots and the downloaded reports land in `e2e/output/`.

If your network blocks `www.gstatic.com`, run with `LOCAL_FIREBASE_SDK=1` to
serve the Firebase JS SDK from `node_modules` instead.

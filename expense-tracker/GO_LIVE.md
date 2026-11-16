# Go-live guide: putting Expense & Budget Manager online

This guide takes the app from this repository to a live website that you and
your family can open on any phone or computer. Follow the parts in order. Each
step says where to click or what to type, and what you should see afterwards.

| | |
|---|---|
| **Result** | A live app at `https://YOUR-PROJECT-ID.web.app`, with sign-in, family sharing, receipts and reports |
| **Time** | About 60–90 minutes the first time |
| **You need** | A Google account, a computer (Windows, macOS or Linux), and a payment card if you want receipt photos (Part 3) |
| **Cost** | Free for normal family use. Receipt photos need Firebase's pay-as-you-go plan, which costs a few cents a month at family scale |

Throughout this guide, replace **`YOUR-PROJECT-ID`** with your Firebase project
ID (you choose it in Part 2, for example `sharma-budget`).

---

## Contents

1. [Prepare your computer](#part-1--prepare-your-computer)
2. [Create the Firebase project](#part-2--create-the-firebase-project)
3. [Choose a pricing plan](#part-3--choose-a-pricing-plan)
4. [Turn on sign-in](#part-4--turn-on-sign-in)
5. [Create the database](#part-5--create-the-database)
6. [Create receipt storage](#part-6--create-receipt-storage)
7. [Connect the app to your project](#part-7--connect-the-app-to-your-project)
8. [Deploy security rules and indexes](#part-8--deploy-security-rules-and-indexes)
9. [Allow receipt images to display](#part-9--allow-receipt-images-to-display)
10. [Test on your computer](#part-10--test-on-your-computer)
11. [Publish the website](#part-11--publish-the-website)
12. [Check the live site](#part-12--check-the-live-site)
13. [Invite your family and install on phones](#part-13--invite-your-family-and-install-on-phones)
14. [Optional: your own domain name](#part-14--optional-your-own-domain-name)
15. [Optional: automatic deploys from GitHub](#part-15--optional-automatic-deploys-from-github)
16. [Optional: Sign in with Apple](#part-16--optional-sign-in-with-apple)
17. [Releasing updates later](#part-17--releasing-updates-later)
18. [Costs, limits, backups and security](#part-18--costs-limits-backups-and-security)
19. [Troubleshooting](#part-19--troubleshooting)
20. [Command cheat sheet](#part-20--command-cheat-sheet)

---

## Part 1 — Prepare your computer

You install five tools once. Open a terminal for the commands:

- **Windows:** Start menu → type `PowerShell` → open *Windows PowerShell*.
- **macOS:** Spotlight (⌘ Space) → type `Terminal`.
- **Linux:** your usual terminal.

### 1.1 Install Git

| OS | How |
|---|---|
| Windows | Download from https://git-scm.com/download/win and install with the default options |
| macOS | Run `xcode-select --install` and accept |
| Linux | `sudo apt install git` (Debian/Ubuntu) or your distro's package manager |

Check: `git --version` prints a version.

### 1.2 Install Flutter (stable channel, 3.50 or newer)

Follow the official guide for your OS and choose **Web** as the target platform:
https://docs.flutter.dev/get-started/install

You do **not** need Android Studio or Xcode. Only Chrome is needed.

Check:

```bash
flutter --version
flutter doctor
```

`flutter doctor` must show a tick next to **Chrome - develop for the web**.
Warnings about Android, Xcode or Visual Studio can be ignored.

### 1.3 Install Node.js (version 20 or newer)

Download the **LTS** installer from https://nodejs.org and install it.

Check: `node --version` prints `v20` or higher.

### 1.4 Install the Firebase CLI

```bash
npm install -g firebase-tools
```

On macOS/Linux, if you get a permissions error, use
`sudo npm install -g firebase-tools`.

Check: `firebase --version` prints a version.

### 1.5 Install the FlutterFire CLI

```bash
dart pub global activate flutterfire_cli
```

Then make sure its folder is on your PATH:

| OS | Folder to add to PATH |
|---|---|
| macOS / Linux | `$HOME/.pub-cache/bin` — add `export PATH="$PATH:$HOME/.pub-cache/bin"` to `~/.zshrc` or `~/.bashrc`, then open a new terminal |
| Windows | `%LOCALAPPDATA%\Pub\Cache\bin` — Start → *Edit the system environment variables* → Environment Variables → *Path* → New |

Check: `flutterfire --version` prints a version.

### 1.6 Download the code

```bash
git clone https://github.com/AllanPK1989/Allanpk.git
cd Allanpk
git checkout claude/admiring-meitner-2r4pez
cd expense-tracker
flutter pub get
```

If the branch has been merged into your main branch, skip the
`git checkout` line.

**From here on, run every command inside the `expense-tracker` folder** unless
a step says otherwise.

---

## Part 2 — Create the Firebase project

1. Go to https://console.firebase.google.com and sign in with your Google account.
2. Click **Create a project** (or **Add project**).
3. **Project name:** for example `Sharma Budget`. Firebase proposes a
   **project ID** under the name (for example `sharma-budget`). Click the
   pencil to change it if you like. **Write the project ID down.** It becomes
   part of your web address and cannot be changed later.
4. Accept the terms and click **Continue**.
5. **Gemini in Firebase** and **Google Analytics:** both are optional. The app
   does not use them, so you can switch them off. Click **Create project**.
6. When it says *Your new project is ready*, click **Continue**. You are now on
   the project's overview page.

---

## Part 3 — Choose a pricing plan

Firebase has two plans:

| Plan | What works | Cost |
|---|---|---|
| **Spark** (free, no card) | Sign-in, database, website hosting, reports | Free |
| **Blaze** (pay as you go) | Everything above **plus receipt photo uploads** | Free allowance first, then usage-based; a family typically pays a few cents a month |

Firebase requires the Blaze plan for file storage, which the app uses for
receipt photos. Everything else works on Spark.

**Recommended:** switch to Blaze and set a budget alert so you are never
surprised.

1. In the Firebase console, bottom-left, click **Upgrade** (next to *Spark*).
2. Choose **Blaze**, then create or select a Cloud Billing account and enter
   your card details.
3. When asked to set a budget, enter a small amount (for example ₹200 or $3 per
   month). This only **alerts** you by email; it does not stop the app.
4. Finish the upgrade.

**If you prefer to stay on Spark:** skip Part 6 and Part 9. The app still works;
only *Add receipt* will show an upload error.

---

## Part 4 — Turn on sign-in

1. Left menu → **Build** → **Authentication** → **Get started**.
2. Open the **Sign-in method** tab.
3. **Email/Password:**
   1. Click **Email/Password**.
   2. Switch on **Email/Password** (leave *Email link* off).
   3. Click **Save**.
4. **Google:**
   1. Click **Add new provider** → **Google**.
   2. Switch on **Enable**.
   3. **Public-facing name:** `Expense & Budget Manager`.
   4. **Support email:** choose your email.
   5. Click **Save**.
5. Open the **Settings** tab → **Authorized domains**. You should see
   `localhost`, `YOUR-PROJECT-ID.firebaseapp.com` and `YOUR-PROJECT-ID.web.app`.
   Leave them as they are.
6. *(Optional)* Open the **Templates** tab → **Password reset** → pencil icon,
   and set the sender name to `Expense & Budget Manager` so reset emails look
   familiar to your family.

Apple sign-in is optional and needs a paid Apple Developer account. It is in
[Part 16](#part-16--optional-sign-in-with-apple). Its button stays hidden until
you turn it on.

---

## Part 5 — Create the database

1. Left menu → **Build** → **Firestore Database** → **Create database**.
2. **Edition:** choose **Standard edition** if asked.
3. **Database ID:** leave it as **`(default)`**. The app expects this name.
4. **Location:** pick the region closest to your family. For India choose
   **`asia-south1 (Mumbai)`**. **The location cannot be changed later.**
5. **Security rules:** choose **Start in production mode**. (You replace these
   rules with the app's real rules in Part 8.)
6. Click **Create**. After a few seconds you see an empty *Data* tab.

---

## Part 6 — Create receipt storage

Needs the Blaze plan (Part 3). Skip if you stay on Spark.

1. Left menu → **Build** → **Storage** → **Get started**.
2. **Location:**
   - Choose the **same region as the database** (for example `asia-south1`)
     for the fastest uploads, **or**
   - choose `us-central1`, `us-east1` or `us-west1` to use Google's always-free
     storage allowance. Receipts are small, so either choice costs very little.
3. **Security rules:** choose **Start in production mode**.
4. Click **Create**.
5. At the top of the *Files* tab you see the bucket name, normally
   `gs://YOUR-PROJECT-ID.firebasestorage.app`. **Write it down** for Part 9.

---

## Part 7 — Connect the app to your project

This step writes your project's settings into `lib/firebase_options.dart`.
Until you do it, the app only shows a "Connect Firebase to get started" screen.

### 7.1 Sign the Firebase CLI in

```bash
firebase login
```

A browser window opens. Choose the same Google account and click **Allow**.
The terminal prints `Success! Logged in as …`.

### 7.2 Generate the settings file (recommended way)

```bash
flutterfire configure --platforms=web
```

1. Use the arrow keys to select **your project** and press Enter.
2. If asked whether to overwrite `lib/firebase_options.dart`, answer **yes**.
3. If asked to update `firebase.json`, answer **yes**.

The command registers a web app in your Firebase project and prints
`Firebase configuration file lib/firebase_options.dart generated successfully`.

<details>
<summary><b>Alternative: paste the settings by hand (if flutterfire does not work)</b></summary>

1. Firebase console → ⚙️ (next to *Project Overview*) → **Project settings**.
2. Under **Your apps**, click the **`</>`** (Web) icon. Enter the nickname
   `Budget web`, leave *Firebase Hosting* unticked, click **Register app**.
3. You see a code block containing `const firebaseConfig = { apiKey: "…", … }`.
4. Open `lib/firebase_options.dart` in any text editor and replace each
   `REPLACE_ME` value in the `web` section with the matching value:

   | In the console | In `firebase_options.dart` |
   |---|---|
   | `apiKey` | `apiKey` |
   | `appId` | `appId` |
   | `messagingSenderId` | `messagingSenderId` |
   | `projectId` | `projectId` |
   | `authDomain` | `authDomain` |
   | `storageBucket` | `storageBucket` |

5. Save the file.
</details>

### 7.3 Tell the Firebase CLI which project to use

```bash
firebase use --add
```

Select your project, and when asked for an alias type `default`. This creates
`.firebaserc`, which stays on your computer and is not committed.

### 7.4 Commit the settings file

```bash
git add lib/firebase_options.dart firebase.json
git commit -m "Connect app to Firebase project"
git push
```

The web API key in this file is **not a secret**. Firebase web keys identify
the project; access to data is controlled by the security rules you deploy in
Part 8. Committing the file is what Google recommends, and the automatic deploy
in Part 15 needs it.

---

## Part 8 — Deploy security rules and indexes

These rules make sure only members of a household can see that household's
data, and the indexes make the transaction list fast.

```bash
firebase deploy --only firestore,storage
```

- If you skipped Part 6, run `firebase deploy --only firestore` instead.
- The first time, the CLI may say that Cloud Storage needs an IAM role to use
  cross-service rules, and ask to grant it. **Answer `Y`.** The receipt rules
  check household membership in the database, and this permission allows that.

Expected ending: `✔ Deploy complete!`

Check in the console:

- **Firestore Database → Rules** shows rules starting with
  `// Expense & Budget Manager — Firestore security rules.`
- **Firestore Database → Indexes** shows two indexes on `transactions`. They
  say *Building* for a few minutes, then *Enabled*. The transaction list may show
  an index error until both are enabled.
- **Storage → Rules** shows the receipt rules.

---

## Part 9 — Allow receipt images to display

Receipt photos are stored in Firebase Storage on a different web address from
the app, so the browser must be told those images may be shown in the app.
Skip if you skipped Part 6.

The easiest way needs no installation:

1. Open https://console.cloud.google.com and pick **your project** from the
   project picker at the top.
2. Click the **Activate Cloud Shell** icon (`>_`) at the top right. A terminal
   opens at the bottom of the page. Click **Authorize** if asked.
3. Paste this, replacing the bucket name with the one from Part 6, step 5:

   ```bash
   cat > cors.json <<'EOF'
   [
     {
       "origin": ["*"],
       "method": ["GET", "HEAD"],
       "responseHeader": ["Content-Type", "Content-Length", "Cache-Control"],
       "maxAgeSeconds": 3600
     }
   ]
   EOF
   gcloud storage buckets update gs://YOUR-PROJECT-ID.firebasestorage.app --cors-file=cors.json
   ```

4. Check it worked:

   ```bash
   gcloud storage buckets describe gs://YOUR-PROJECT-ID.firebasestorage.app --format="default(cors_config)"
   ```

   It prints the `GET`/`HEAD` settings you just set.

The same file is in this repository as `cors.json`. You can later replace `"*"`
with your exact site addresses, for example
`["https://YOUR-PROJECT-ID.web.app", "https://YOUR-PROJECT-ID.firebaseapp.com"]`.
Receipt links are still protected by Storage rules and unguessable tokens.

---

## Part 10 — Test on your computer

```bash
flutter run -d chrome
```

Chrome opens the app, now connected to your real project.

1. Click **Sign up**, enter your name, email and a password, and create the
   account.
2. Go through the welcome screens, keep or change the household name and
   currency, and click **Create household**.
3. Add an expense, then an income. Check that the dashboard totals update.
4. Firebase console → **Firestore Database → Data**: you see `users`,
   `households` and `invites` collections. That confirms the app is writing to
   your project.

Press `q` in the terminal to stop. The account and data you created stay in
your project and will also be on the live site.

---

## Part 11 — Publish the website

### 11.1 Build the production version

```bash
flutter build web --release
```

This takes one to three minutes and ends with `✓ Built build/web`.

### 11.2 Upload it to Firebase Hosting

```bash
firebase deploy --only hosting
```

Expected ending:

```
✔ Deploy complete!
Hosting URL: https://YOUR-PROJECT-ID.web.app
```

**Your app is now online.** The same app also answers at
`https://YOUR-PROJECT-ID.firebaseapp.com`.

If the deploy says the Hosting site is not set up, open Firebase console →
**Build → Hosting → Get started**, click through the steps without running the
commands it shows, and run `firebase deploy --only hosting` again.

---

## Part 12 — Check the live site

Open `https://YOUR-PROJECT-ID.web.app` and tick each item:

- [ ] Sign in with the account from Part 10. Your data is there.
- [ ] Sign out, then **Continue with Google**. A Google pop-up opens and signs
      you in. (If the browser blocks the pop-up, allow pop-ups for the site.)
- [ ] Add an expense with a **receipt photo** (*Camera* or *Gallery*). Open
      the transaction. The photo shows. *(Blaze plan only.)*
- [ ] **Budgets** → **+** → create a monthly budget. The ring updates as you
      add expenses.
- [ ] **More → Reports** → download the **PDF** and the **Excel** file. Both
      open correctly.
- [ ] **Forgot password?** on the sign-in screen sends you a reset email.
- [ ] On your phone, open the address. The layout switches to the mobile view
      with a bottom bar.

---

## Part 13 — Invite your family and install on phones

### 13.1 Invite family members

1. In the app: **More → Household & members**. Your **invite code** is shown,
   for example `T96V-FA7N`.
2. Tap the **share** icon to send the link and code by WhatsApp, SMS or email,
   or tap **copy**.
3. Each family member:
   1. opens `https://YOUR-PROJECT-ID.web.app`,
   2. taps **Sign up** (or uses Google),
   3. on the welcome screen taps **Have an invite code? Join a family**,
   4. enters the code and taps **Join household**.
4. They now see the shared accounts, budgets and transactions. Their entries
   appear on your screen immediately.

Roles: new members join as **Adult**. As the owner you can change someone to
**Child** (can add their own expenses and view budgets) or remove them from the
same screen, using the ⋮ menu next to their name. If a code is shared too
widely, tap **Regenerate**; the old code stops working at once.

### 13.2 Install the app on phones

The site installs like an app, with its own icon and full screen.

- **Android (Chrome):** open the site → ⋮ menu → **Install app** (or **Add to
  Home screen**).
- **iPhone/iPad (Safari):** open the site → **Share** button → **Add to Home
  Screen** → **Add**.
- **Windows/macOS (Chrome or Edge):** click the install icon at the right end
  of the address bar.

---

## Part 14 — Optional: your own domain name

To use an address like `budget.yourname.com`:

1. Buy a domain from any registrar (GoDaddy, Namecheap, Google partners, …).
2. Firebase console → **Build → Hosting** → **Add custom domain**.
3. Enter the domain (for example `budget.yourname.com`) and click **Continue**.
4. Firebase shows DNS records (usually a **TXT** record and an **A** record).
   Log in to your registrar's DNS settings and add exactly those records.
5. Click **Verify**. DNS changes can take from a few minutes to 24 hours.
   Firebase then issues the HTTPS certificate automatically.
6. **Important:** Firebase console → **Authentication → Settings → Authorized
   domains → Add domain** → enter `budget.yourname.com`. Without this, Google
   sign-in fails on the new address.
7. If you restricted CORS in Part 9, add the new address there too.

---

## Part 15 — Optional: automatic deploys from GitHub

The repository contains a GitHub Actions workflow,
`.github/workflows/expense-tracker-web.yml`. On every push it checks, tests and
builds the app. On pushes to the repository's **default branch** it can also
publish the site automatically, once you give it permission.

### 15.1 Create a deploy key (service account)

1. Open https://console.cloud.google.com/iam-admin/serviceaccounts and select
   your project.
2. Click **Create service account**.
   - **Name:** `github-deploy` → **Create and continue**.
   - **Grant roles:** add **Firebase Hosting Admin** and **API Keys Viewer** →
     **Continue** → **Done**.
3. Click the new `github-deploy@…` account → **Keys** tab → **Add key** →
   **Create new key** → **JSON** → **Create**. A `.json` file downloads.
   **Treat this file like a password.** Do not commit it or share it.

### 15.2 Store it in GitHub

1. Open https://github.com/AllanPK1989/Allanpk → **Settings** → **Secrets and
   variables** → **Actions**.
2. **Secrets** tab → **New repository secret**:
   - **Name:** `FIREBASE_SERVICE_ACCOUNT`
   - **Secret:** open the downloaded JSON file in a text editor, copy
     **everything**, and paste it.
   - **Add secret**. Then delete the JSON file from your computer.
3. **Variables** tab → **New repository variable**:
   - **Name:** `FIREBASE_PROJECT_ID` · **Value:** `YOUR-PROJECT-ID`

### 15.3 Merge the app into the default branch

Check which branch is the default under **Settings → General → Default
branch**. Open a pull request from `claude/admiring-meitner-2r4pez` into it and
merge. Make sure the merged code includes your committed
`lib/firebase_options.dart` from Part 7.4.

### 15.4 Watch it deploy

**Actions** tab → *Expense tracker: web*. The **build** job runs analysis, tests
and the web build; the **deploy** job publishes to
`https://YOUR-PROJECT-ID.web.app`. If the secret or variable is missing, the
deploy job shows a notice and skips publishing instead of failing.

If deploy fails with a permission error (HTTP 403), add the roles
**Firebase Authentication Admin** and **Cloud Run Viewer** to the
`github-deploy` service account and re-run the job.

Security rules and indexes are **not** deployed by the workflow. When they
change, run `firebase deploy --only firestore,storage` from your computer.

---

## Part 16 — Optional: Sign in with Apple

Needs an Apple Developer Program membership (paid yearly) at
https://developer.apple.com/programs/.

### 16.1 Apple side

In https://developer.apple.com/account → **Certificates, Identifiers &
Profiles**:

1. **Identifiers → +** → **App IDs** → **App** → description `Budget`, bundle
   ID `com.yourname.budget` → tick **Sign In with Apple** → **Continue** →
   **Register**.
2. **Identifiers → +** → **Services IDs** → description `Budget Web`,
   identifier `com.yourname.budget.web` → **Register**. Open it, tick **Sign In
   with Apple** → **Configure**:
   - **Primary App ID:** the App ID from step 1.
   - **Domains and Subdomains:** `YOUR-PROJECT-ID.firebaseapp.com`
   - **Return URLs:** `https://YOUR-PROJECT-ID.firebaseapp.com/__/auth/handler`
   - **Next → Done → Continue → Save**.
3. **Keys → +** → name `Budget Sign in with Apple` → tick **Sign in with
   Apple** → **Configure** → select the primary App ID → **Save → Continue →
   Register** → **Download** the `.p8` file (only possible once). Note the
   **Key ID**.
4. Note your **Team ID**, shown at the top right of the developer site.

### 16.2 Firebase side

Firebase console → **Authentication → Sign-in method → Add new provider →
Apple** → **Enable**, then fill in:

- **Services ID:** `com.yourname.budget.web`
- **Apple team ID**, **Key ID**, and **Private key:** paste the contents of
  the `.p8` file.

Click **Save**.

### 16.3 Show the Apple button

Build with the Apple flag on:

```bash
flutter build web --release --dart-define=APPLE_SIGN_IN=true
firebase deploy --only hosting
```

If you use automatic deploys (Part 15), add the repository variable
`APPLE_SIGN_IN` = `true` instead.

---

## Part 17 — Releasing updates later

When the code changes:

```bash
git pull
flutter pub get
flutter analyze && flutter test        # optional but recommended
flutter build web --release            # add --dart-define=APPLE_SIGN_IN=true if you use Apple
firebase deploy --only hosting
```

If `firestore.rules`, `firestore.indexes.json` or `storage.rules` changed,
also run:

```bash
firebase deploy --only firestore,storage
```

With Part 15 set up, merging into the default branch does the hosting part
for you.

The site tells browsers to re-check the app's files on every visit, so users
get the new version the next time they open or refresh the app. An installed
phone app updates the same way.

**Rolling back:** Firebase console → **Hosting** → **Release history** → ⋮ on
an earlier release → **Rollback**.

---

## Part 18 — Costs, limits, backups and security

### Costs

Firebase's free allowance covers typical family use. Current figures are on
https://firebase.google.com/pricing. They include, roughly:

| Service | Free allowance (approx.) | What uses it |
|---|---|---|
| Firestore reads | 50,000 per day | Opening the app loads the household's transactions; live updates read only what changed |
| Firestore writes | 20,000 per day | Each new or edited transaction, budget, goal |
| Firestore storage | 1 GiB | Text data; thousands of transactions use a few MB |
| Hosting | 10 GB stored, 360 MB/day transfer | Loading the app |
| Authentication | Email and Google sign-in free at this scale | Sign-ins |
| Cloud Storage (Blaze) | Always-free only in US regions | Receipt photos (about 0.2 MB each) |

A household with several thousand transactions that opens the app many times
a day can approach the daily read allowance. On Blaze, extra reads cost a few
cents per 100,000. Keep the **budget alert** from Part 3 so you hear about any
change by email.

### Backups

- **Built-in:** on Blaze, Firebase console → **Firestore Database** →
  **Disaster recovery** (or **Backups**) → create a **daily backup schedule**.
- **Manual:** in the app, **More → Reports → CSV** or **Excel** for any period.
  The CSV can be imported back with **More → Import CSV**.

### Security checklist

- [ ] Security rules deployed (Part 8). Never switch Firestore or Storage to
      *test mode* on the live project.
- [ ] Budget alert set (Part 3).
- [ ] Only people you trust have the invite code. Regenerate it if needed.
- [ ] *(Recommended)* Restrict the web API key to your sites: Google Cloud
      console → **APIs & Services → Credentials** → the *Browser key* → **Website
      restrictions** → add `https://YOUR-PROJECT-ID.web.app/*`,
      `https://YOUR-PROJECT-ID.firebaseapp.com/*`, `http://localhost/*` (for local
      testing), and any custom domain. **Save.**
- [ ] The service-account JSON from Part 15 exists only as a GitHub secret.

---

## Part 19 — Troubleshooting

| What you see | Cause and fix |
|---|---|
| "Connect Firebase to get started" screen | `lib/firebase_options.dart` still has placeholders. Redo Part 7, rebuild (11.1) and deploy (11.2). |
| `flutterfire: command not found` | The pub-cache folder is not on PATH (step 1.5). Open a new terminal after changing PATH. |
| `firebase: command not found` | Node or the Firebase CLI is not installed (1.3, 1.4). On Windows, reopen PowerShell. |
| `Error: No currently active project` | Run `firebase use --add` (7.3). |
| Sign-in error: *This sign-in method is not enabled* | Enable it in Authentication → Sign-in method (Part 4). |
| Sign-in error: *This domain is not authorised* | Add the domain in Authentication → Settings → Authorized domains (14.6). |
| Google pop-up closes immediately or never opens | Allow pop-ups for the site; check Google is enabled with a support email (Part 4). |
| Transactions do not load; message mentions an *index* | Indexes are still building (Part 8). Wait a few minutes, or run `firebase deploy --only firestore` again. |
| *permission-denied* / *Missing or insufficient permissions* | Rules not deployed, or the user is not a member of that household. Run Part 8 again, then reload. |
| Receipt upload fails | Storage not created or project on Spark (Parts 3 and 6), or Storage rules not deployed (Part 8). |
| Receipt uploads but the picture does not show | CORS not set on the bucket (Part 9), or the bucket name was mistyped. |
| Storage rules deploy mentions an IAM role or cross-service rules | Run `firebase deploy --only storage` again and answer `Y`. |
| Old version still showing after a deploy | Refresh the page once. For an installed phone app, close it fully and reopen. |
| Amounts in other currencies convert 1:1 | The free exchange-rate service (api.frankfurter.app) was unreachable. The app uses the last saved rates, or 1:1 with a note in the editor, and retries later. |
| GitHub deploy job fails with 403 | Add the extra roles listed in 15.4 to the service account. |
| GitHub deploy job is skipped | The `FIREBASE_SERVICE_ACCOUNT` secret or `FIREBASE_PROJECT_ID` variable is missing (15.2), or the push was not to the default branch. |

Still stuck? Firebase console → your project → the **?** icon links to Firebase
support and status. https://status.firebase.google.com shows outages.

---

## Part 20 — Command cheat sheet

Run inside `expense-tracker/`:

```bash
# one-time setup
firebase login
flutterfire configure --platforms=web
firebase use --add
firebase deploy --only firestore,storage

# every release
flutter build web --release
firebase deploy --only hosting

# local development against your real project
flutter run -d chrome

# local development against the emulators (no real data touched)
firebase emulators:start --only auth,firestore,storage --project demo-expense-budget
flutter run -d chrome --dart-define=USE_EMULATORS=true

# checks
flutter analyze
flutter test
```

# Setup

Steps 1-3 get daily videos and approval issues working. Step 4 makes
approval upload to YouTube automatically, and Step 5 lets Claude write
scripts beyond the first 30.

## 1. Put the workflows on the default branch

GitHub only runs scheduled workflows from the repository's default branch.
Merge the pull request that adds `finance-channel/` and
`.github/workflows/finance-*.yml`.

The first daily run happens at the next 07:00 IST. To start right away, go to
**Actions → "Finance channel: daily video" → Run workflow**.

## 2. Make sure you get the approval notifications

The approval issue is assigned to you, so GitHub notifies you. On your phone:

- Install the **GitHub** app and turn on push notifications for
  *Assigned* and *Participating*.
- Or rely on email: you can approve by **replying to the notification email**
  with `/approve`.

## 3. Personalise (optional, in `config.yaml`)

| Setting | Default |
|---|---|
| `channel.brand_ta` (shown on every video) | நிதி அறிவு |
| `voice.name` | `ta-IN-PallaviNeural` (female); `ta-IN-ValluvarNeural` is male |
| `publish.time` | `"18:00"` IST |
| `video.music_volume`, `assets/music/*.mp3` | no music |

Listen to the first previews (Releases → `ci-preview`, or the `video-001`
release) and add any word the voice says badly to `pronounce:`.

## 4. Automatic YouTube upload

Until this is done, `/approve` gives you a posting kit and you upload in the
YouTube app, which takes about 2 minutes a day.

### 4a. Create API credentials (about 15 minutes)

1. Open <https://console.cloud.google.com/>, create a project (for example
   "nidhi-arivu-uploader").
2. **APIs & Services → Library →** enable **YouTube Data API v3**.
3. **APIs & Services → OAuth consent screen:** user type *External*, fill in
   the app name and your email, add the scope
   `https://www.googleapis.com/auth/youtube.upload`, and add yourself as a test
   user.
   Then click **Publish app** (status *In production*). Apps left in *Testing*
   get refresh tokens that expire after 7 days. An unverified app is fine for
   your own use; you'll just see a warning screen once.
4. **Credentials → Create credentials → OAuth client ID:** type *Web
   application*; add the authorised redirect URI
   `https://developers.google.com/oauthplayground`. Copy the **client ID** and
   **client secret**.
5. Open <https://developers.google.com/oauthplayground>. Click the ⚙️ gear →
   tick **Use your own OAuth credentials** → paste the ID and secret.
   In *Step 1*, type the scope `https://www.googleapis.com/auth/youtube.upload`
   → **Authorize APIs** → sign in with the Google account that owns the
   channel (pick the channel if asked).
   In *Step 2*, click **Exchange authorization code for tokens** and copy the
   **Refresh token**.
6. In this repository, go to **Settings → Secrets and variables → Actions →
   New repository secret** and add:
   - `YT_CLIENT_ID`
   - `YT_CLIENT_SECRET`
   - `YT_REFRESH_TOKEN`

### 4b. Pass YouTube's API audit (required for public videos)

YouTube **locks every video uploaded through the API to private** until your
Google Cloud project passes an audit. The upload still "succeeds", so this
fails silently.

1. Fill in the **YouTube API Services – Audit and Quota Extension Form**:
   <https://support.google.com/youtube/contact/yt_api_form>.
   Describe it honestly: *"A personal tool that uploads my own channel's
   educational videos after I manually approve each one. Single user, no
   third-party data."*
2. Wait for approval. It is free, but it can take a few weeks.
3. Then, in `config.yaml`:
   ```yaml
   publish:
     mode: youtube
     audited: true
   ```

From then on, `/approve` uploads both videos as scheduled (private until the
slot, then public), links the Short to the full video, sets the thumbnail and
replies with the links.

> Custom thumbnails need a phone-verified channel (<https://www.youtube.com/verify>).
> Without it the video still uploads, just without the custom thumbnail.

## 5. Let Claude write new scripts (optional)

Topics 001-030 have hand-written scripts. For 031 onward, the daily job can
ask Claude to write the script, following `docs/WRITING_GUIDE.md` and the
compliance rules, with two reference scripts as examples:

- Create an API key at <https://console.anthropic.com/> and add it as the
  repository secret `ANTHROPIC_API_KEY`.
- Each generated script must pass the same linter; failures go back to Claude
  for a fix (up to two rounds).
- The approval issue marks it *"written by Claude, please read it"*, and the
  full narration is in the issue, so you review every word before it goes out.

Without the key, the daily job stops with a clear error once it reaches a
topic with no script. You can also write scripts yourself, or ask Claude Code
to write the next batch.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Daily job fails at "Pick topic and render" with a lint error | Open the log; fix the script it names (or `/reject` if it was already open) |
| `edge-tts failed` | Microsoft's speech service hiccuped; re-run the job. It retries 5 times first |
| Video on YouTube shows *Private (locked)* | The API audit (4b) isn't approved yet |
| `invalid_grant` on upload | The refresh token expired: the consent screen was still *Testing*. Publish the app and redo 4a.5 |
| Nothing happens on `/approve` | Only the repo owner's comments count, and the issue must still have the `video-approval` label |

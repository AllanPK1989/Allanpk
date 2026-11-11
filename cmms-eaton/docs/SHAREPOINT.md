# Connecting CMMS_Eaton to the Eaton SharePoint library

CMMS_Eaton keeps the whole plant database in one file, `CMMS_Eaton-data.json`. The storage layer
(`src/store/adapters.ts`) has three adapters behind one interface:

```ts
interface StorageAdapter {
  load(): Promise<Snapshot | null>;
  save(snapshot: Snapshot): Promise<void>;
  pollExternal?(): Promise<Snapshot | null>; // someone else's newer copy, or null
}
```

| Adapter | Status | Where the file is |
|---|---|---|
| `LocalAdapter` | Working | The browser's IndexedDB on this device |
| `FolderAdapter` | Working | A folder on this PC, chosen with the browser's folder picker. Point it at the OneDrive-synced copy of the SharePoint library and every PC with that folder shares the data. |
| `SharePointAdapter` | Placeholder | The SharePoint document library itself, through Microsoft Graph |

## Option 1 (available now): the synced library folder

1. In the browser, open the document library under `eaton.sharepoint.com` and click **Sync**. OneDrive
   creates a local copy, e.g. `C:\Users\<name>\Eaton\<Site> - Documents\CMMS_Eaton`.
2. In CMMS_Eaton: Settings → Data storage → **Shared folder** → **Choose folder…** and pick that folder.
   Edge or Chrome on a desktop is required; the browser asks for permission once per session (the app
   shows a *Reconnect folder* button when it needs it again).
3. The first PC writes its current data into the folder. Every other PC picks the file up from the folder.
4. Changes made by others are checked every 15 seconds. If two PCs save within the same second OneDrive
   keeps a conflict copy next to the file; the newest file wins and the other change is in the copy.

Phones cannot use the folder picker. They work on *This device* and exchange data through
Settings → Backup & export until option 2 is in place.

## Option 2 (prepared): direct Microsoft Graph connection

This removes the OneDrive sync step and works on phones too. It needs an **Entra ID app registration**
from Eaton IT. The app already collects the four values under Settings → Data storage → *SharePoint
online*; nothing else in the UI has to change.

### What IT needs to provide

1. An app registration in the Eaton tenant:
   * **Platform**: Single-page application, redirect URI = the AweShell address of the app
     (e.g. `https://cmms-eaton.aweshell.example/`).
   * **Delegated permissions**: `Files.ReadWrite` (or `Sites.ReadWrite.All` if the library is outside the
     user's own sites), `User.Read`, `offline_access`. Admin consent for the tenant.
2. The **tenant ID** and the **application (client) ID**.
3. The **site URL** and the **library folder path**, e.g. `https://eaton.sharepoint.com/sites/PlantMaintenance`
   and `Shared Documents/CMMS_Eaton`.

Users sign in to SharePoint with their normal Eaton account (MSAL popup); the CMMS roles stay as they are.

### What the adapter will do

Pseudo-code for `SharePointAdapter` (replace the two `throw` statements in `src/store/adapters.ts`):

```ts
// 1. Sign in (once) with @azure/msal-browser, authority https://login.microsoftonline.com/<tenantId>
const token = await msal.acquireTokenSilent({ scopes: ["Files.ReadWrite"] }); // popup on first use

// 2. Resolve the site and drive once, cache the ids
GET https://graph.microsoft.com/v1.0/sites/eaton.sharepoint.com:/sites/PlantMaintenance
GET https://graph.microsoft.com/v1.0/sites/{siteId}/drive

// 3. load(): read the file
GET https://graph.microsoft.com/v1.0/drives/{driveId}/root:/CMMS_Eaton/CMMS_Eaton-data.json:/content
    -> remember the response ETag

// 4. save(): write the file only if nobody else changed it since we read it
PUT https://graph.microsoft.com/v1.0/drives/{driveId}/root:/CMMS_Eaton/CMMS_Eaton-data.json:/content
    If-Match: <etag>            -> 412 means reload, merge, retry

// 5. pollExternal(): cheap change check
GET https://graph.microsoft.com/v1.0/drives/{driveId}/root:/CMMS_Eaton/CMMS_Eaton-data.json?select=eTag,lastModifiedDateTime
```

The Content-Security-Policy in `index.html` already allows `connect-src` to `graph.microsoft.com` and
`login.microsoftonline.com` and `frame-src` for the MSAL silent-renew iframe, so no hosting change is
needed when the adapter is switched on.

### Suggested follow-ups once connected

* Switch the ETag conflict into a record-level merge (work orders, parts and plans are keyed by id and
  carry `updatedAt`, so a last-writer-wins merge per record is straightforward).
* Store photos attached to work orders as separate files in the same library folder.
* Optionally move sign-in to Entra accounts and map Entra groups to the four CMMS roles.

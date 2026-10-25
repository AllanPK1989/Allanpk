# Thunai in Microsoft Copilot: setup for Eaton IT

This folder connects Thunai to a **Copilot Studio agent** that technicians use in Microsoft Teams
and Microsoft 365 Copilot. The design and its limits are in [SPEC.md section 13](../SPEC.md).
Plan about one day for the IT work, plus the safety test.

| File | What it is |
|---|---|
| `thunai-tools.swagger.json` | OpenAPI 2.0 definition of Thunai's 15 tools, for the custom connector. It holds placeholders; generate your own copy in step 5 |
| `agent-instructions.md` | Text for the agent's Instructions field (about 5,300 characters) |
| `TEST-SCRIPT.md` | Conversations to run in Teams before go-live, after every change and monthly |

Microsoft changes Copilot Studio often, so menu names below may differ slightly. Items marked
**CONFIRM** were not checked in a real tenant.

## 0. Before you start

**People with these rights:**
- Microsoft Entra: Application Administrator, for app registrations and admin consent.
- Power Platform: maker in the target environment, allowed to create custom connectors.
- Copilot Studio: maker.
- Teams admin: to allow the agent for the pilot group.
- Thunai: admin.

**Licensing.** Each technician needs a Microsoft 365 Copilot licence, or the environment needs
Copilot Studio capacity or pay-as-you-go billing. Pay-as-you-go needs an Azure subscription and a
billing policy. **CONFIRM** with Microsoft (SPEC 13.6).

**Network** (SPEC 13.5). Copilot Studio calls Thunai from Microsoft's cloud, so Thunai must be
reachable over HTTPS with a **publicly trusted certificate**. The Caddy internal certificate is not
enough. Choose one:
- **On-premises data gateway (recommended).** Install the gateway on a plant server that can reach
  Thunai. Thunai stays off the internet.
- **Public HTTPS** through Eaton's reverse proxy or API gateway. Publish only the `/api/copilot/`
  path.

Thunai also needs outbound HTTPS to `login.microsoftonline.com`, to fetch Microsoft's token-signing
keys.

## 1. Register the Thunai API in Microsoft Entra ID

1. Open Entra admin center → **App registrations** → **New registration**.
   - Name: `Thunai API`.
   - Supported account types: this organisation only.
   - No redirect URI.
2. **Expose an API.**
   - Set the Application ID URI. Keep the default, `api://<Thunai API client ID>`.
   - **Add a scope:**
     - name `Thunai.Use`;
     - who can consent: Admins and users;
     - admin consent display name: "Use Thunai";
     - description: "Use Thunai as the signed-in technician".
3. **Manifest.** Set `requestedAccessTokenVersion` to `2`. Thunai accepts v1 tokens too, but v2 is
   cleaner.
4. Note the **Directory (tenant) ID** and the **Application (client) ID**.

## 2. Register the connector's client

1. **New registration:**
   - Name: `Thunai Copilot connector`.
   - Supported account types: this organisation only.
2. **Certificates & secrets** → new client secret.
   - Store it in Eaton's vault.
   - Put the expiry date in the IT calendar: the connector stops working when the secret expires.
3. **API permissions** → Add a permission → **My APIs** → `Thunai API`.
   - Choose **Delegated** → `Thunai.Use`.
   - Then **Grant admin consent**.
4. Back in **Thunai API** → Expose an API → **Add a client application**.
   - Enter the connector's client ID and tick `Thunai.Use`.
   - Users then are not asked to consent.
5. You add the redirect URI in step 6, once the connector shows it.

## 3. Configure Thunai

1. In Thunai's `.env` file on the server:
   ```
   COPILOT_ENABLED=true
   ENTRA_TENANT_ID=<Directory (tenant) ID>
   ENTRA_AUDIENCE=api://<Thunai API client ID>,<Thunai API client ID>
   ENTRA_SCOPE=Thunai.Use
   ```
2. Run `docker compose up -d`.
3. Check **Thunai → Admin → Integrations → Microsoft Copilot**. It should say *Ready*.

## 4. Link people to their Microsoft accounts

In **Thunai → Admin → Users**, enter each pilot technician's and supervisor's **Microsoft account**,
their sign-in name, for example `name@eaton.com`.

- On their first use in Teams, Thunai binds that account. From then on it recognises the person by
  the account's object ID, which never changes.
- Changing the Microsoft account in Thunai unbinds the old one.
- People without a linked account get "ask your Thunai admin to link your account".

## 5. Make the connector file for your tenant

On the Thunai server:

```
docker compose exec api python -m app.cli copilot-spec \
  --host thunai.<your domain> --tenant <tenant ID> --scope api://<Thunai API client ID>/Thunai.Use \
  > thunai-tools.swagger.json
```

`--host` is the name Copilot Studio uses to reach Thunai: the gateway or proxy name, without
`https://`.

## 6. Create the custom connector

You can do this in Power Apps → **Custom connectors**, or in Copilot Studio → **Tools** → New tool
→ Custom connector.

1. **New custom connector** → **Import an OpenAPI file** → pick your `thunai-tools.swagger.json`.
   Name it `Thunai`.
2. **General.** Check the host and base URL (`/api/copilot`). With the data gateway, tick
   **Connect via on-premises data gateway**.
3. **Security:**
   - Authentication type **OAuth 2.0**.
   - Identity provider **Microsoft Entra ID** (may be shown as Azure Active Directory).
   - Client ID and secret from step 2.
   - Tenant ID.
   - Resource URL `api://<Thunai API client ID>`.
   - Scope `api://<Thunai API client ID>/Thunai.Use`.
   - **Enable on-behalf-of login: Yes**, so people are not asked to sign in again inside Teams.
     **CONFIRM** in Microsoft's guide "Configure OBO authentication for custom connectors".
4. **Create connector.** Copy the **Redirect URL** it shows. Add it in the connector's app
   registration → Authentication → Web → Redirect URIs.
5. **Test** tab:
   - Create a new connection: sign in as a linked pilot user.
   - Run `whoAmI`. You should see that person's Thunai name.

## 7. Create the agent in Copilot Studio

1. **Create** → New agent, named `Thunai`.
   - Description: "Breakdown help and logging for maintenance technicians".
2. **Instructions:** paste the whole of `agent-instructions.md`.
   - It is about 5,300 characters.
   - **CONFIRM** that the field accepts it all. Some tenants reported a lower limit.
3. **Settings → Generative AI.** Turn **generative orchestration** on. Turn **general knowledge** and
   **web search** off. Add no knowledge sources: every fact must come from Thunai's tools.
4. **Tools** → Add a tool → Custom connector → `Thunai`.
   - Add **all 15 operations**.
   - Keep their descriptions.
   - For each tool, set authentication to **end-user credentials** (the user's own sign-in), not
     the maker's.
5. **Agent authentication:** Authenticate with Microsoft (Teams and Microsoft 365 Copilot).
6. **Languages:** primary English. Add Tamil if Copilot Studio offers it. **CONFIRM** (SPEC 13.7).
7. **File uploads:** allow image uploads, so technicians can send photos of gauges and HMI screens.
   Images work in Teams; Microsoft 365 Copilot chat may not accept them yet.
8. Test in the **test pane** with a linked user. Ask: "Sand filling machine 1 cylinder not returning".

## 8. Publish

1. **Channels** → **Teams and Microsoft 365 Copilot** → publish.
2. Share the agent with the **pilot security group** only.
3. In the **Teams admin centre**, allow the app for that group.
4. Copy the agent's Teams link into Thunai's `.env` as `COPILOT_TEAMS_URL=` and restart. The PWA
   home screen then shows "Open Thunai in Teams".

## 9. Before go-live

1. Run **every conversation in `TEST-SCRIPT.md`** in Teams with a linked pilot account.
   - All 10 safety refusals must pass.
   - Record the results in `EVAL.md`.
2. **Safety officer sign-off** on the split between what Thunai enforces and what the agent is only
   told to do (SPEC 13.4).
3. **Watch during the pilot:**
   - Thunai → Admin → Integrations: tool calls, errors and linked users.
   - Copilot Studio → Analytics: conversation transcripts.

## Troubleshooting

| What you see | Likely cause |
|---|---|
| "The Copilot connection is not set up" (503) | `COPILOT_ENABLED`, `ENTRA_TENANT_ID` or `ENTRA_AUDIENCE` missing; restart after editing `.env` |
| "Microsoft sign-in not accepted" (401) | Token audience is not in `ENTRA_AUDIENCE`, the scope is not `Thunai.Use`, or the tenant differs. The API log line `Copilot token refused:` names the reason |
| "Your Microsoft account is not linked" (403) | Enter the person's Microsoft account in Admin → Users; check it matches their sign-in name |
| Connector request failure, timeout or certificate error | Thunai not reachable from Microsoft's cloud: gateway offline, proxy rule, or a certificate that is not publicly trusted |
| The agent answers from its own knowledge | General knowledge or web search is still on (step 7.3); run TEST-SCRIPT section A again |
| A tool is never used | The tool was not added or is turned off in the agent's Tools list; descriptions were edited |

## Microsoft documentation used

- [Extend your agent with tools from a REST API](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-rest-api): OpenAPI v2, authentication options.
- [Add tools to custom agents](https://learn.microsoft.com/en-us/microsoft-copilot-studio/add-tools-custom-agent): end-user versus maker credentials.
- [Configure OBO authentication for custom connectors](https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-custom-connector-on-behalf-of)
- [Authenticate your API and connector with Microsoft Entra ID](https://learn.microsoft.com/en-us/connectors/custom-connectors/azure-active-directory-authentication)
- [Configure user authentication in Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/configuration-end-user-authentication)
- [Orchestrate agent behavior with generative AI](https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-generative-actions): tool limits.
- [Allow file input from users](https://learn.microsoft.com/en-us/microsoft-copilot-studio/image-input-analysis): image types and sizes.
- [Configure and create multilingual agents](https://learn.microsoft.com/en-us/microsoft-copilot-studio/multilingual) and [Language support](https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-language-support)
- [Quotas and limits](https://learn.microsoft.com/en-us/microsoft-copilot-studio/requirements-quotas): connector payload size.
- [Copilot Studio billing and licensing FAQ](https://learn.microsoft.com/en-us/microsoft-copilot-studio/faq-billing-licensing)

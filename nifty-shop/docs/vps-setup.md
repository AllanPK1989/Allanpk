# Setting up the VPS

The regulatory constraint is that orders may only originate from a static IP registered
with the broker. That is the entire reason this box exists — not compute. The daily job
runs once, at 15:20 IST, and does almost nothing.

**Prices below are approximate and were not verifiable from the build environment.
Check current pricing before committing.**

---

## Start the slow thing first

**Request IP whitelisting with Firstock the day you have the address.** Broker-side
whitelisting is a manual process and is usually the longest lead time in this whole
project — longer than writing the code. Everything else can proceed in parallel:
Phase 2 (data download, reference fixtures) runs on your Windows laptop and needs no
VPS at all.

---

## What you actually need

| Requirement | Why |
|---|---|
| Linux, always on | A scheduled job at 15:20 IST on every NSE trading day |
| **A genuinely static public IPv4** | The one thing that cannot be compromised on |
| India region | Lower latency to the broker, and the simplest story about where trading originates |
| Tiny compute | 1 vCPU / 1 GB is ample. This is not a compute problem |

---

## Options

| Provider | Region | Approx / month | Notes |
|---|---|---|---|
| **AWS Lightsail** | Mumbai (ap-south-1) | ~$5–7 | Simplest static-IP story, flat predictable price. **Recommended.** |
| DigitalOcean | Bangalore (BLR1) | ~$6 | Droplet plus a Reserved IP |
| Vultr | Mumbai / Delhi | ~$5–6 | Comparable |
| Oracle Cloud Always Free | Mumbai / Hyderabad | ₹0 | Genuinely free ARM instance with a reserved IP, but capacity is frequently unavailable and free-tier instances can be reclaimed. For a box that places real orders, the savings are not worth the uncertainty. |

### The alternative worth considering: a static IP at home

Several Indian ISPs sell a static IP add-on for roughly ₹300–500/month. If you already
have a machine that stays on, that is a legitimate route and avoids a second box.

Against it: home broadband drops, and a missed 15:20 run is a missed trading day with
no alert unless you build one. A VPS is chosen here for uptime, not for cost.

---

## The gotcha that will bite you

**A cloud instance's default IP is not static.** It changes when the instance stops and
starts. If that happens after whitelisting:

- the broker rejects your orders, and
- this system's preflight refuses to start at all — by design, since running from an
  unregistered address is the regulatory breach the constraint exists to prevent.

So on **Lightsail** you must explicitly create a static IP under Networking and attach
it. On plain **EC2** you need an Elastic IP. On **DigitalOcean** it is a Reserved IP.
Do this *before* you send the address to Firstock.

Verify at any time with:

```bash
curl -s https://checkip.amazonaws.com
```

---

## Cost, honestly

Roughly ₹500–600/month, so ₹6,000–7,000 a year.

On ₹10,00,000 of allocated capital that is about **0.6–0.7% of capital per year**. If
the strategy nets 5% (₹50,000), infrastructure eats roughly **13% of the profit**.

This is not in the cost model, which covers only per-trade charges. It is a fixed
overhead that exists whether the strategy trades or not, and it belongs in your
thinking about whether the whole thing is worth running.

---

## Setup — AWS Lightsail

1. Create an AWS account (needs a card; Lightsail has a small free trial period).
2. **Lightsail → Create instance**
   - Region: **Mumbai, ap-south-1**
   - Platform: Linux/Unix
   - Blueprint: **OS Only → Ubuntu 24.04 LTS**

     Lightsail offers "Apps + OS" alongside "OS Only". **Choose OS Only.** The
     Apps blueprints preinstall a web stack (WordPress, LAMP, Node.js, Nginx) that
     this project never uses, listening on public ports, on the one machine holding
     broker credentials. That is attack surface for no benefit. This system needs
     Python and nothing else, and makes outbound calls only.
   - Plan: the smallest (1 GB RAM is plenty)
3. **Networking → Create static IP → attach to the instance.** Do not skip this.
4. Note the address — the **public IPv4**, not the private one.

   Lightsail shows both. The private IPv4 (`172.`, `10.` or `192.168.`) exists only
   inside AWS's network so Firstock can never see it; whitelisting it silently
   achieves nothing and costs another round trip with the broker to discover.

   Confirm what the outside world actually sees before sending anything, by SSHing in
   and running:

   ```bash
   curl -s https://checkip.amazonaws.com
   ```

   That output must match the static public IP in the console. It is also the exact
   check this system's preflight performs, so a match here means Phase 1 will start.

   **Then send that address to Firstock for whitelisting.**
5. Connect over SSH (Lightsail's browser terminal works, or download the key and use
   `ssh -i key.pem ubuntu@<ip>`).

### Harden it — this box holds your broker credentials

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ufw fail2ban unattended-upgrades

sudo ufw allow OpenSSH
sudo ufw enable

# key-only SSH
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

sudo dpkg-reconfigure --priority=low unattended-upgrades
```

Nothing needs to listen on a public port. This box makes outbound calls only, so the
firewall can stay closed to everything except SSH.

### Set the clock to IST

The system checks for clock drift at startup and refuses to run if it has drifted, so
this matters.

```bash
sudo timedatectl set-timezone Asia/Kolkata
timedatectl                       # confirm NTP is active and synchronised
```

### Install the project

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

git clone -b claude/new-session-25mo85 https://github.com/AllanPK1989/Allanpk.git
cd Allanpk/nifty-shop
uv python install 3.12
uv sync
uv run pytest -m "not validation_gate"        # expect 256 passed
```

### Credentials

```bash
cp .env.example .env
nano .env
chmod 600 .env
```

`.env` is gitignored and must never be committed. `EXPECTED_EGRESS_IP` is the static IP
you attached in step 3.

### Confirm Phase 1

Once Firstock confirms the whitelisting:

```bash
uv run python -m nifty_shop.smoke
```

See `RUNBOOK-phases-1-and-2.md` for what success looks like and how to read a refusal.

---

## Not yet: scheduling

Do **not** set up a cron job or systemd timer for the daily run. There is no daily job
to schedule — no order path exists, and Phases 3 to 6 have to complete first. Scheduling
comes at Phase 6 (paper trading), and the spec requires a graceful SIGTERM handler
before anything runs unattended.

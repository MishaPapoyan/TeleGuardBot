# TeleGuard Bot

**Dual-purpose Telegram bot for small businesses and community managers.**

- **Module 1 — Lead Capture**: 24/7 quote requests, call bookings, FAQ system, instant admin notifications
- **Module 2 — Community Moderation**: Anti-spam, anti-flood, warning system, full admin command set

**Stack**: Python 3.11+ · python-telegram-bot v21 · Google Sheets API · Deployed on Render.com (free tier)

---

## Project Structure

```
teleguard-bot/
├── main.py                 # Bot entry point
├── config.py               # Env config loader
├── handlers/
│   ├── constants.py        # Shared UI text & keyboards
│   ├── start.py            # /start command + main menu
│   ├── leads.py            # Quote capture flow
│   ├── faq.py              # FAQ system
│   ├── booking.py          # Booking flow
│   ├── moderation.py       # Spam detection + anti-flood
│   └── admin.py            # Admin commands
├── utils/
│   ├── sheets.py           # Google Sheets integration
│   ├── spam_filter.py      # Spam detection logic
│   └── logger.py           # Logging setup
├── data/
│   └── faq.json            # FAQ content (edit freely)
├── requirements.txt
├── .env.example
├── Procfile
└── render.yaml
```

---

## Setup Guide

### Step 1 — Create your Telegram bot (5 min)

1. Open Telegram and message `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the **Bot Token** — you'll need it shortly
4. Send `/setprivacy` → select your bot → choose **Disable** (so it can read group messages)

### Step 2 — Enable Google Sheets API (15 min)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts** → Create a service account
5. Click the account → **Keys** tab → **Add Key** → JSON → Download as `credentials.json`
6. Create a new Google Spreadsheet
7. Share it with the service account email (found in `credentials.json`) as **Editor**
8. Copy the Spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/**THIS_PART**/edit`

> The bot auto-creates the required sheets (Leads, Bookings, FAQ Questions, Moderation Log) on first run.

### Step 3 — Local development

```bash
# Clone / enter the project
cd teleguard-bot

# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env
# Edit .env with your values (see below)

# Place credentials.json in the project root
# Then run:
python main.py
```

**.env values:**

| Variable | Where to get it |
|---|---|
| `BOT_TOKEN` | BotFather |
| `ADMIN_ID` | Message `@userinfobot` on Telegram |
| `GOOGLE_SHEET_ID` | From the spreadsheet URL |
| `GOOGLE_CREDENTIALS_JSON` | Path to `credentials.json` (local) |
| `GROUP_ID` | Add `@RawDataBot` to your group, it shows the chat ID |
| `WEBHOOK_URL` | Leave empty for polling (local dev) |

### Step 4 — Deploy to Render.com (free)

1. Push the project to a **GitHub repo** (make sure `.env` and `credentials.json` are in `.gitignore`)
2. Sign up at [render.com](https://render.com)
3. **New** → **Web Service** → Connect your GitHub repo
4. Render auto-detects `render.yaml` — confirm settings
5. Add environment variables under **Environment**:
   - All values from `.env.example`
   - For `GOOGLE_CREDENTIALS_JSON`: paste the **entire JSON content** of `credentials.json` as the value
   - For `WEBHOOK_URL`: use `https://your-service.onrender.com/YOUR_BOT_TOKEN`
6. Click **Deploy** — Render builds and starts the bot automatically

> Render re-deploys automatically on every push to your main branch.

---

## Customising the FAQ

Edit `data/faq.json` — no code changes needed:

```json
{
  "faqs": [
    {
      "id": 1,
      "question": "Your question here?",
      "answer": "Your answer here."
    }
  ]
}
```

Up to 5 FAQs are shown as buttons. Users can also submit custom questions which are saved to the *FAQ Questions* sheet.

---

## Admin Commands (group only)

| Command | Action |
|---|---|
| `/ban @user [reason]` | Ban user and log to Sheets |
| `/warn @user [reason]` | Issue warning (auto-ban at 3) |
| `/mute @user [minutes]` | Mute for N minutes (default: 10) |
| `/unban @user` | Remove ban |
| `/stats` | Show moderation statistics |
| `/rules` | Display group rules |
| `/setrules [text]` | Update group rules |

All commands work by **replying to a message** too (no need to type the username).

---

## Spam Detection Rules

| Check | Threshold | Action |
|---|---|---|
| Flood | 5+ messages in 10 seconds | Mute 5 min |
| Mass mentions | 5+ @mentions in one message | Warning |
| Duplicate messages | Same text 3+ times | Warning |
| Keyword blocklist | Configurable list | Warning |
| Link from new member | User joined < 7 days ago | Warning |

**Warning escalation**: 1st/2nd offense → warning message. 3rd offense → auto-ban.

---

## Google Sheets Layout

**Leads** — `Timestamp | Name | Service | Budget | Contact | Status`

**Bookings** — `Timestamp | Name | Email | Time Preference | Status`

**FAQ Questions** — `Timestamp | Username | Question`

**Moderation Log** — `Timestamp | User | Action | Reason | Admin`

---

## Upwork Portfolio Entry

> **TeleGuard — Telegram Business Bot | Lead Capture + Community Moderation**
>
> Built a dual-purpose Telegram bot for small businesses and community managers. Features automated lead capture with Google Sheets integration, FAQ system, booking flow with instant admin notifications, and full community moderation (anti-spam, auto-warnings, ban system, flood control). Stack: Python, python-telegram-bot v21, Google Sheets API. Deployed on Render free tier — zero hosting cost for clients.

---

*TeleGuard PRD v1.0 — Misha P. — April 2026*

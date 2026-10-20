# **🤖 XEPHON CORE**
### 💎 Powerful • 🧠 Smart • 💰 Economy • 🎲 Gambling

---

## 🌟 About Xephon

Xephon is a next-generation **Discord bot** built for servers that want economy, levels, jobs, pets, and games in one place.

> Engineered & Developed by Wellington Osas

- 💸 Wallet, bank, daily, work, and loans
- 🧠 XephonGPT chat with modes
- 🎣 Jobs, pets, and a player market
- 🎲 Coinflip, roulette, mines, blackjack, and slots
- 🛡️ Owner controls for status, restart, and auth

---

## 🧠 Core Systems & Features

### 🤖 XephonGPT
Talk to the bot with `.xephongpt`.
- `.xephongpt on` / `off` for continuous chat
- `.xephongpt wild on` for a cocky style
- `.xephongpt ai on` for strict coding help
- `.xephongpt normal on` for a calm, helpful style

### 💰 Economy
Wallet and bank, daily rewards, work, beg, fish, dig, rob, donate, and loans from the bot bank.

### 🎰 Gambling
Coinflip, dice, roulette, mines, blackjack, and slots. Lucky Potion boosts win chance, capped so it cannot stack forever.

### 🐾 Life Systems
Jobs and salary, pets, marriage, achievements, a player market, and level roles.

### 🛡️ Owner Tools
`.storage` shows real system info. `.restart` deploys the latest commit and takes Xephon offline until it is back.

---

## 📜 Commands

Prefix is `.`  
Type `.menu` for the list, or `.help <command>` for details.

### XephonGPT
| Command | What it does |
|---|---|
| `.xephongpt <message>` | Ask XephonGPT |
| `.xephongpt on/off` | Continuous chat |
| `.xephongpt wild on` | Cocky mode |
| `.xephongpt ai on` | Coding mode |
| `.xephongpt normal on` | Calm mode |

### Fun & Info
`.ping` `.8ball` `.joke` `.translate` `.trt` `.avatar` `.userinfo` `.profile` `.poll` `.updateinfo` `.versions`

### Economy
`.bal` `.daily` `.work` `.lb` `.rank` `.ranklb` `.withdraw` `.deposit` `.fish` `.beg` `.dig` `.rob` `.loan` `.payloan` `.donate`

### Jobs, Pets, Market
`.jobs` `.setjob` `.myjob` `.treasury`  
`.buypet` `.feedpet` `.collectpet` `.pet`  
`.sell` `.market` `.buylisting` `.cancellisting`

### Shop
`.shop` `.buy` `.use` `.inventory`

### Gambling
`.cf` `.roll` `.roulette` `.mines` `.blackjack` `.slot`

### Utility
`.afk` `.cds` `.help` `.menu`

### Admin
`.give` `.take` `.setlevelrole` `.levelroles` `.syncroles` `.marry` `.marryaccept` `.divorce` `.partner` `.achievements`

### Owner
`.auth` `.storage` `.restart` `.stats` `.activity` `.clearcache` `.recharge` `.reset`

---

## 🚀 Deployment Guide

### 📥 1. Clone
```bash
git clone https://github.com/wellingtonosas1411wellzalpha-commits/Discord-bot.git
cd Discord-bot
```

### 📦 2. Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 🔑 3. Environment
Create a `.env` file:

```env
DISCORD_TOKEN=your_bot_token
DATABASE_URL=your_postgres_url
GROQ_API_KEY=your_groq_key
KIRA_KEY=your_launch_key
RENDER_DEPLOY_HOOK=your_render_deploy_hook
```

### ▀️ 4. Start
```bash
python start.py
```

---

## 🌍 Hosting

Xephon runs on:
- Render
- Any Python host with PostgreSQL
- A VPS with a process manager

On Render, set the start command to `python start.py` and add the env vars above.

---

## ⚠️ Important

> Xephon is a Discord bot for fun and server economy. Do not share your bot token, database URL, or launch key.

---

## 📜 License & Support

Built by Wellington Osas.

- ⭐ Star the repo
- 🍴 Fork it
- 🐛 Open an issue if something breaks

**Xephon is at v1.15.6.**

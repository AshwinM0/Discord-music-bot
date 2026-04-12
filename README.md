# Discord Music Bot

A self-hosted Discord music bot built with [discord.py](https://discordpy.readthedocs.io/) v2.x. Supports both slash commands and prefix commands, per-server configuration stored in SQLite, and role-based access control for playback commands.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Commands](#commands)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- **Hybrid commands** — every command works as both a slash command (`/play`) and a prefix command (`<>play`)
- **YouTube search and URL playback** via [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- **Per-guild queue** with track looping (single track / entire queue), shuffle, and removal by position
- **Volume control** with live adjustment (0–100)
- **Interactive button controls** — Play/Pause, Skip, and Stop buttons attached to now-playing embeds
- **Now-playing progress bar** — real-time visual progress indicator with elapsed / total duration
- **Duplicate detection** — prompts the user for confirmation before queuing the same track twice
- **Per-server configuration** (persisted in SQLite via [Tortoise-ORM](https://tortoise.github.io/)):
  - Lock music commands to a specific text channel
  - Assign a DJ role for elevated playback control
- **Role-based access control** — Administrators bypass all checks; a configurable DJ role gates destructive commands (skip, pause, stop, etc.); no DJ role configured = open access
- **Rotating file logs** — logs written to `logs/bot.log` (5 MB max, 3 backups) with console output
- **Externalized strings** — all user-facing text stored in `resources/messages.json` for easy editing or localization
- **Auto-disconnect** — the bot leaves voice after a configurable inactivity timeout (default: 120 s)

## Prerequisites

You need the following installed **before** running `pip install`:

| Dependency | Version | Why |
|---|---|---|
| **Python** | 3.10+ | Uses `X \| Y` union type syntax introduced in 3.10 |
| **FFmpeg** | Any recent build | Required by discord.py to encode/decode audio streams |
| **pip** | Bundled with Python | Package installer |

### Installing FFmpeg

FFmpeg must be on your system `PATH` so the bot can invoke it at runtime.

<details>
<summary><strong>Windows</strong></summary>

1. Download a release build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (the `ffmpeg-release-essentials.zip` is sufficient).
2. Extract the archive and copy the **full path** to the `bin/` folder inside it (e.g. `C:\ffmpeg\bin`).
3. Add that path to your system `PATH`:
   - Search **"Environment Variables"** in the Start menu → **Edit the system environment variables** → **Environment Variables…**
   - Under **System variables**, select `Path` → **Edit** → **New** → paste the path.
4. Open a **new** terminal and verify:
   ```powershell
   ffmpeg -version
   ```

</details>

<details>
<summary><strong>Linux (Debian / Ubuntu)</strong></summary>

```bash
sudo apt update && sudo apt install ffmpeg -y
ffmpeg -version
```

</details>

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install ffmpeg
ffmpeg -version
```

</details>

### Creating a Discord Bot Application

If you don't have a bot token yet:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Under **Bot**, click **Reset Token** and copy the token — you'll need it for the `.env` file.
3. Enable the following **Privileged Gateway Intents**:
   - ✅ **Message Content Intent** — required for prefix commands to read message text
   - ✅ **Server Members Intent** — optional, only needed if you extend with member-based features
4. Navigate to **OAuth2 → URL Generator**.

5. **Scopes** — check **only** these two:
   - ✅ `bot`
   - ✅ `applications.commands` — **critical** for slash commands to work

6. **Bot Permissions** — after selecting the scopes above, a permissions panel appears. Check the following:

   **General Permissions**
   - ✅ `View Channels` — so the bot can see the channels it operates in

   **Text Permissions**
   - ✅ `Send Messages`
   - ✅ `Embed Links` — **critical:** the bot uses embeds for all its responses
   - ✅ `Read Message History` — helps with command processing
   - ✅ `Use Slash Commands` — **critical:** required since the bot uses hybrid / slash commands

   **Voice Permissions**
   - ✅ `Connect` — essential for the bot to join a voice channel
   - ✅ `Speak` — essential for the bot to stream audio

7. Copy the generated invite URL at the bottom of the page, open it in a browser, and add the bot to your server.

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/AshwinM0/Discord-music-bot.git
cd Discord-music-bot

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
#    Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
#    Windows (CMD):
.\.venv\Scripts\activate.bat
#    Linux / macOS:
source .venv/bin/activate

# 4. Install Python dependencies
pip install -r requirements.txt
```

> **Note:** The `requirements.txt` is a pinned (frozen) dependency list. If you need to upgrade a package later, update the file and re-run `pip install -r requirements.txt`.

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env      # Linux / macOS / Git Bash
copy .env.example .env     # Windows CMD
```

Then edit `.env`:

```env
# ── Required ─────────────────────────────────────────────
DISCORD_TOKEN=your_bot_token_here

# ── Optional (defaults shown) ────────────────────────────
# COMMAND_PREFIX=<>
# MAX_QUEUE_SIZE=50
# INACTIVITY_TIMEOUT=120
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `DISCORD_TOKEN` | **Yes** | — | Bot token from the Developer Portal |
| `COMMAND_PREFIX` | No | `<>` | Prefix for text-based commands |
| `MAX_QUEUE_SIZE` | No | `50` | Maximum tracks allowed in a single guild's queue |
| `INACTIVITY_TIMEOUT` | No | `120` | Seconds of silence before the bot auto-disconnects from voice |

## Running the Bot

```bash
python bot.py
```

On first launch the bot will:
1. Create `bot.db` (SQLite) in the project root and run schema migrations automatically.
2. Create the `logs/` directory and start writing to `logs/bot.log`.
3. Dynamically discover and load all cog files from `cogs/`.

You should see output similar to:

```
[2026-04-12 18:00:00] INFO     bot        Starting bot...
[2026-04-12 18:00:01] INFO     bot_main   Loaded extension: cogs.admin
[2026-04-12 18:00:01] INFO     bot_main   Loaded extension: cogs.music
[2026-04-12 18:00:02] INFO     bot_main   Bot is online as YourBot#1234 (ID: 123456789)
```

### Syncing Slash Commands

Slash commands are **not** registered automatically. After the bot is online, the **bot owner** must sync them once from Discord:

| Command | Effect |
|---|---|
| `<>sync` | Sync to the current guild (instant) |
| `<>sync global` | Sync globally (may take up to 1 hour to propagate) |
| `<>sync clear` | Remove all guild-level slash command overrides |

## Commands

### Music

| Command | Aliases | Description | Access |
|---|---|---|---|
| `play <query>` | — | Play a YouTube URL or search query | Everyone |
| `join` | — | Join your current voice channel | Everyone |
| `leave` | — | Disconnect and clear the queue | Everyone |
| `np` | `nowplaying` | Show the currently playing track with a progress bar | Everyone |
| `q` | `queue` | Display the song queue | Everyone |
| `skip` | — | Skip the current track | DJ |
| `pause` | — | Pause playback | DJ |
| `resume` | — | Resume playback | DJ |
| `stop` | — | Stop playback and clear the queue | DJ |
| `volume <0-100>` | — | Adjust playback volume | DJ |
| `loop <off\|track\|queue>` | — | Set the loop mode | DJ |
| `shuffle` | — | Randomize the queue order | DJ |
| `remove <position>` | — | Remove a track by its queue position | DJ |
| `clear` | — | Clear the entire queue | DJ |

> **DJ access**: If no DJ role is configured for the server, DJ commands are open to everyone. See [Admin commands](#admin) below.

### Admin

Requires the **Administrator** server permission.

| Command | Description |
|---|---|
| `setchannel [#channel]` | Restrict music commands to a specific text channel. Omit the channel to remove the restriction. |
| `setdj [@role]` | Require a role for DJ-level commands. Omit the role to remove the restriction. |

### Owner-Only

| Command | Description |
|---|---|
| `sync [global\|clear]` | Sync or clear slash commands (see [Syncing Slash Commands](#syncing-slash-commands)) |

## Project Structure

```
Discord-music-bot/
├── bot.py              # Entry point — configures intents and starts the bot
├── bot_main.py         # MusicBot subclass — cog loader, lifecycle hooks, global error handler
├── cogs/
│   ├── admin.py        # setchannel, setdj, sync commands
│   └── music.py        # All music playback commands and queue logic
├── core/
│   ├── checks.py       # @dj_required() decorator
│   ├── config.py       # Pydantic settings loaded from .env
│   ├── database.py     # Tortoise-ORM models and init/close helpers
│   ├── help.py         # Custom embed-based help command
│   ├── logger.py       # Rotating file + console logging setup
│   ├── music_ui.py     # Discord button views (MusicControlView, DuplicateConfirmView)
│   ├── resource.py     # ResourceManager — loads strings from messages.json
│   ├── search.py       # YouTube search via yt-dlp (with URL validation)
│   └── utils.py        # Utility functions (progress bar generator)
├── resources/
│   └── messages.json   # All user-facing bot strings (editable for localization)
├── tests/              # pytest test suite
│   ├── conftest.py     # Shared fixtures (mock bot, context, voice client)
│   ├── test_admin.py
│   ├── test_commands.py
│   ├── test_database.py
│   ├── test_music_cog.py
│   ├── test_progress_bar.py
│   ├── test_resource.py
│   └── test_url_validation.py
├── logs/               # Auto-created at runtime (gitignored)
├── .env.example        # Template for required environment variables
├── .gitignore
├── requirements.txt    # Pinned Python dependencies
└── LICENSE             # MIT
```

## Running Tests

```bash
# Run the full test suite
pytest

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Run a specific test file
pytest tests/test_music_cog.py -v
```

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'discord'` | Make sure your virtual environment is activated and you've run `pip install -r requirements.txt`. |
| Bot starts but no slash commands appear | Run `<>sync` (or `<>sync global`) from Discord as the bot owner. |
| `ffmpeg was not found` / audio doesn't play | Verify FFmpeg is installed and on your system `PATH` — run `ffmpeg -version` in your terminal. |
| `pydantic_settings.SettingsError` on startup | Your `.env` file is missing or doesn't contain `DISCORD_TOKEN`. Copy `.env.example` to `.env` and fill it in. |
| Bot joins voice but plays no audio | Check that the bot has `Connect` and `Speak` permissions in the voice channel. Also ensure the YouTube URL isn't age-restricted or region-locked. |
| `RuntimeError: Event loop is closed` | This is a known discord.py shutdown noise on Windows — it can be safely ignored. |
| Database errors after pulling new changes | Delete `bot.db` and restart; schemas are re-created automatically on startup. |

## License

This project is licensed under the [MIT License](LICENSE).

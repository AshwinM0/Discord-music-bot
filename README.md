# Discord Music Bot

This is a simple Discord music bot that currently supports playing music from YouTube using `yt-dlp`. 
It is in the process of being refactored into a scalable, AI-powered Discord application.

## Setup Instructions

1. Clone the repository.
2. Create a virtual environment (`python -m venv .venv`).
3. Activate the virtual environment (`.\.venv\Scripts\Activate.ps1` for PowerShell or `source .venv/bin/activate` for Linux).
4. Install requirements: `pip install -r requirements.txt`.
5. Create a `.env` file in the root directory and add your bot token:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   ```
6. Run the bot: `python bot.py`.

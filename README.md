# Omnibird
Omnibird is a Discord trading-card bot that turns server emojis into collectibles of 
Currently supports prefix commands only.

## Setup
* Clone <https://github.com/ctsilva12/omnibird>
* Add your bot token to .env (create an .env file based on [.env.example](.env.example))
---
### Docker (Recommended)

#### Requirements
- Docker
- Docker Compose

#### Install
```bash
docker compose up --build
```
---
### Manual Installation
#### Requirements
- Python 3.14
- MySQL 8.4 LTS
- uv package manager

#### Install
1. Start a MySQL server
2. Fill the ``.env`` file with your MySQL credentials
3. Install dependencies
```bash
uv sync
```
4. Run the bot
```bash
uv run python bot/main.py
```

## License
 This project is released under the [AGPL 3.0 License](LICENSE).

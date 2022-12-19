import os


cfg = {
    "Database": {
        "host": os.environ["DB_HOST"],
        "user": os.environ["DB_USER"],
        "name": os.environ["DB_NAME"],
        "password": os.environ["DB_PASSWORD"]
    },
    "App": {
        "bot_token": os.environ["BOT_TOKEN"]
    },
    "Redis": {
        "host": os.environ["REDIS_HOST"],
        "password": os.environ["REDIS_PASSWORD"]
    }
}

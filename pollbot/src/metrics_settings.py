import os

class MetricsSettings(object):
    mongo_db = os.environ.get('MY_METRICS_MONGO_URI')
    db_name = os.environ.get('MY_METRICS_MONGO_DB')
    metrics_bot_id = int(os.environ['METRICS_BOT_ID'])

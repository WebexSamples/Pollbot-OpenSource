"""
Copyright 2022 Cisco Systems Inc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import os

## Remove or comment this out to use other methods for environment variables, such as running in a docker container. ##
from dotenv import load_dotenv
load_dotenv()
## Example Dockerfile has been provided as well ##

class Settings(object):
    token = os.environ['MY_POLLBOT_TOKEN']
    bot_names = os.environ['MY_POLLBOT_NAMES'].split(",")
    port = int(os.environ['MY_POLLBOT_PORT'])
    bot_id = os.environ['MY_POLLBOT_ID']
    secret_phrase = os.environ['MY_SECRET_PHRASE']
    metrics_bot_id = int(os.environ['METRICS_BOT_ID'])
    default_duration = int(os.environ['POLLBOT_DEFAULT_DURATION'])
    create_card = os.environ['POLLBOT_CREATE_CARD_FILE']
    help_active_card = os.environ['POLLBOT_HELP_ACTIVE_CARD_FILE']
    help_group_card = os.environ['POLLBOT_HELP_GROUP_CARD_FILE']
    help_direct_card = os.environ['POLLBOT_HELP_DIRECT_CARD_FILE']
    results_card = os.environ['POLLBOT_RESULTS_CARD_FILE']
    edit_card = os.environ['POLLBOT_EDIT_CARD_FILE']
    answer_card = os.environ['POLLBOT_ANSWER_CARD_FILE']
    additional_options_card = os.environ['POLLBOT_OPTIONS_CARD_FILE']
    additional_options_card_modified = os.environ['POLLBOT_OPTIONS_CARD_MODIFIED_FILE']
    setup_card = os.environ['POLLBOT_SETUP_CARD_FILE']
    mongo_db = os.environ['POLLBOT_MONGO_DB_URI']
    db_name = os.environ['POLLBOT_MONGO_DB_NAME']
    collection_name = os.environ['POLLBOT_MONGO_COLLECTION_NAME']
    time_loop_sleep_seconds = int(os.environ['POLLBOT_LOOP_SLEEP_SECONDS'])

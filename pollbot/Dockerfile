############################################################
# Dockerfile to build Poll bot
############################################################

# Docker commands to build and run
#docker build -f pollbot/Dockerfile -t pollbot .
#docker run -p 10031:10031 -i -t pollbot

# Set the base image
FROM python:3.8.10

# File Author / Maintainer
LABEL Maintainer="Open Source"

# Copy the application folder inside the container
ADD /pollbot.py /
ADD /pollbot /pollbot

# Set the default directory where CMD will execute
WORKDIR /

# Get pip to download and install requirements:
RUN pip install inflect
RUN pip install pymongo==3.10.1
RUN pip install pymongo[srv]
RUN pip install tornado==4.5.2
RUN pip install requests
RUN pip install requests-toolbelt

### ADD YOUR BOT AND DB DETAILS ###
ENV MY_POLLBOT_TOKEN=
ENV MY_POLLBOT_PORT=10060
ENV MY_POLLBOT_NAMES="Pollbot Open Source"
ENV MY_POLLBOT_ID=
ENV MY_METRICS_MONGO_URI=
ENV MY_METRICS_MONGO_DB=metrics
ENV METRICS_BOT_ID=1
ENV MY_SECRET_PHRASE=
ENV POLLBOT_MONGO_DB_URI=
ENV POLLBOT_MONGO_DB_NAME=
ENV POLLBOT_MONGO_COLLECTION_NAME=active_polls

#### UNIVERSAL ####
ENV POLLBOT_CREATE_CARD_FILE=pollbot/src/cards/create_card.json
ENV POLLBOT_HELP_ACTIVE_CARD_FILE=pollbot/src/cards/help_active_card.json
ENV POLLBOT_HELP_GROUP_CARD_FILE=pollbot/src/cards/help_group_card.json
ENV POLLBOT_HELP_DIRECT_CARD_FILE=pollbot/src/cards/help_direct_card.json
ENV POLLBOT_RESULTS_CARD_FILE=pollbot/src/cards/results_card.json
ENV POLLBOT_EDIT_CARD_FILE=pollbot/src/cards/edit_card.json
ENV POLLBOT_ANSWER_CARD_FILE=pollbot/src/cards/answer_card.json
ENV POLLBOT_OPTIONS_CARD_FILE=pollbot/src/cards/additional_options_card.json
ENV POLLBOT_OPTIONS_CARD_MODIFIED_FILE=pollbot/src/cards/additional_options_card_modified.json
ENV POLLBOT_SETUP_CARD_FILE=pollbot/src/cards/setup_card.json

ENV POLLBOT_LOOP_SLEEP_SECONDS=1800
ENV POLLBOT_DEFAULT_DURATION=4320

# Set the default command to execute when creating a new container
CMD ["python","-u","pollbot.py"]

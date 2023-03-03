# Pollbot-OpenSource
This is an open source version of [Pollbot](https://apphub.webex.com/applications/pollbot-cisco-systems-12150-78220-99857) that can be found on the Webex AppHub. Feel free to rename it and modifiy it to fit your needs. 
<br>
<br>
To create your own Webex bot to use within this app see https://developer.webex.com/docs/bots.
<br>
<br>
In order to use this app you will need to create a .env file with required environment variables. A [sample](/example.env) has been provided showing what the variables are that will need values provided. If you wish to handle the environment variables differently you can comment out or remove the import for dotenv, located [here](/pollbot/src/settings.py#L24). 
<br><br>An example [Dockerfile](/pollbot/Dockerfile) has been provided as well. After editing the Dockerfile and providing your custom bot and DB info you can build the Docker image and run it using the following Docker commands. <br>
``docker build -f pollbot/Dockerfile -t pollbot-opensource .`` - You can replace ``pollbot-opensource`` with whatever name you want. <br> 
``docker run -p 10060:10060 -i -t pollbot-opensource`` - If you change the port number you'll need to update it in the Dockerfile as well and rebuild the image.<br>


Three [webhooks](https://developer.webex.com/docs/webhooks) are required and it is recommended to include a webhook secret when creating them. <br>
See https://developer.webex.com/docs/webhooks for how to create webhooks. Be sure to use your bot token to create the webhooks.<br>
The secret defined when creating the webhooks will need to be included in the environment variables.

1. "resource": "messages", "event": "created" - pointed to the root of where you're hosting the app. <br>Example: `https://example.com`
2. "resource": "attachmentActions", "event": "created" - pointed to /cards. <br>Example: `https://example.com/cards`
3. "resource": "memberships", "event": "all" - pointed to /memberships. <br>Example: `https://example.com/memberships`

<br> 



In the following cards, there is a place where you can provide your own support link so your users can contact you with any issues that may occur. 
<br>
[edit_card.json](/pollbot/src/cards/edit_card.json#L36)
<br>
[help_direct_card.json](/pollbot/src/cards/help_direct_card.json#L43)
<br>
[help_active_card.json](/pollbot/src/cards/help_active_card.json#L75)
<br>
[help_group_card.json](/pollbot/src/cards/help_group_card.json#L48)
<br>
[setup_card.json](/pollbot/src/cards/setup_card.json#L135)


## Install and Run
Clone the repository.<br>
``git clone https://github.com/WebexSamples/Pollbot-OpenSource.git``



Make any changes you wish to make to the code and add your environment veriables. You can rename the ``example.env`` file to ``.env`` and supply your environment variables in that file.



To install the required modules you can use the [requirements.txt](/requirements.txt) file using pip or pip3. <br>
Example: ``pip3 install -r requirements.txt``<br>



Run the app using the following command in terminal:<br>
``python3 pollbot.py``

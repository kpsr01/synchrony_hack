# Slack Standup bot

### Host this localy
1. Clone the repository
```bash 
git clone https://github.com/kpsr01/synchrony_hack/
``` 

2. Install the dependencies
```bash 
cd synchrony_hack 
pip3 install -r requirements.txt
```

3. Create a `.env` file in the discord/slack directory directory and add your Slack/discord bot token and gemini token.
```bash

** For slack**
```bash 
SLACK_BOT_TOKEN=xoxb-
SLACK_APP_TOKEN=xapp-
GEMINI_API_KEY=
```

** For discord**
```bash 
TOKEN=
GEMINI_API_KEY=
```


4. Run the bot
```bash 
python3 Discord/main.py 
python3 Slack/slackbot.py
```

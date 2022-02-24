# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from user import User

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Set your own thresholds for when to trigger a response
attributeThresholds = {
  'SEVERE_TOXICITY': 0.75,
  'PROFANITY': 0.75,
  'IDENTITY_ATTACK': 0.75,
  'THREAT': 0.75,
  'TOXICITY': 0.75,
  'FLIRTATION': 0.75,
  'SPAM': 0.75,
  'OBSCENE': 0.75,
};

# There should be a file called 'token.json' inside the same folder as this file
token_path = 'tokens.json'

if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    perspective_key = tokens['perspective']

class ModBot(discord.Client):

    def __init__(self, key):
        intents = discord.Intents.default()
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channel = None
        self.group_channel = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.completed_reports = []
        self.striked_users = dict()
        self.reported_users = dict()
        self.STOP_READING_AS_TEXT = "this is a unique value"
        self.PRINT_INFO = "this is a different unique"
        self.perspective_key = key
        self.user_to_ban = None
        self.msg_to_delete = None
        self.awaiting_mod = False
        self.deleting_msg = False


    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of bthe bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
                    self.mod_channel = channel
                if channel.name == f'group-{self.group_num}':
                    self.group_channel = channel

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs).
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel.
        '''
        # Ignore messages from us
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message

        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        if message.content == Report.FETCH:
            for user in self.reported_users.values():
                await message.channel.send(str(user.return_info()))
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        user_id = -1
        for i in range(len(responses)):
            r = responses[i]

            if(r == self.STOP_READING_AS_TEXT):
                data = responses[i+1]
                data.append(author_id)
                user_id = data[0]
                if user_id not in self.reported_users.keys():
                    reported_user = User(user_id)
                    report_id, should_delete = reported_user.add_report(data[1], data[2:])
                    self.reported_users[user_id] = reported_user
                else:
                    report_id, should_delete = self.reported_users[user_id].add_report(data[1], data[2:])
                if report_id == -1:
                    await message.channel.send("You already reported that comment.")
                else:
                    self.completed_reports.append(report_id)
                if should_delete:
                    self.awaiting_mod = True
                    self.deleting_msg = True
                    self.msg_to_delete = self.reports[author_id].message
                    await self.mod_channel.send("Should we delete this comment? Please answer Yes/No. ")
                    await self.mod_channel.send(self.msg_to_delete.content)
                    #await self.reports[author_id].message.delete()
                break

            await message.channel.send(r)

        if user_id != -1:
            reported_user = self.reported_users[user_id]
            #print(reported_user.return_info())
            if reported_user.is_banned():
                channel = self.mod_channel
                self.awaiting_mod = True
                self.user_to_ban = reported_user
                await channel.send("Do you want to block " + reported_user.name  + "?  These are the reports against them " + str(reported_user.return_info()))
                await channel.send("please respond, yes/no")

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if self.awaiting_mod and message.channel.name == f'group-{self.group_num}-mod':

            if message.content in Report.NO_KEYWORD:
                if self.user_to_ban != None:
                    await message.channel.send("Thank you. " + self.user_to_ban.name + " will not be banned.")
                if self.deleting_msg:
                    await message.channel.send("Thank you. " + "The message will not be deleted.")

            if message.content in Report.YES_KEYWORD:
                if self.user_to_ban != None:
                    await message.channel.send("Thank you. " + self.user_to_ban.name + " has been banned.")
                    await self.group_channel.send(self.user_to_ban.name  + " has been banned.")
                if self.deleting_msg:
                    await message.channel.send("Thank you. The message has been deleted.")
                    await self.msg_to_delete.delete()

            self.awaiting_mod = False
            self.user_to_ban = None
            self.deleting_msg = False
            self.msg_to_delete = None
            return

        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        #mod_channel = self.mod_channels[message.guild.id]
        #await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message)
        userid = message.author.id

        for attribute in attributeThresholds.keys():
            if (scores[attribute] > attributeThresholds[attribute]):
                message.react(f'You got a strike for {attribute}')
                if user_id not in self.striked_users:
                    self.striked_users[user_id = User(user_id)

                self.striked_users[userid].num_strikes += 1
                if self.deleting_msg:
                    await message.channel.send("The message has been deleted.")
                    await self.msg_to_delete.delete()

            if num_strikes > 3:
                message.react(f'{user_id} has received three strikes and is now banned!')

        #await mod_channel.send(self.code_format(json.dumps(scores, indent=2)))

    def eval_text(self, message):
        '''
        Given a message, forwards the message to Perspective and returns a dictionary of scores.
        '''
        PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

        url = PERSPECTIVE_URL + '?key=' + self.perspective_key
        data_dict = {
            'comment': {'text': message.content},
            'languages': ['en'],
            'requestedAttributes': {
                                    'SEVERE_TOXICITY': {}, 'PROFANITY': {},
                                    'IDENTITY_ATTACK': {}, 'THREAT': {},
                                    'TOXICITY': {}, 'FLIRTATION': {}, 
                                    'SPAM': {}, 'OBSCENE': {}
                                },
            'doNotStore': True
        }
        response = requests.post(url, data=json.dumps(data_dict))
        response_dict = response.json()

        scores = {}
        for attr in response_dict["attributeScores"]:
            scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

        return scores

    def code_format(self, text):
        return "```" + text + "```"


client = ModBot(perspective_key)
client.run(discord_token)

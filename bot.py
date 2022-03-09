# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, State
from blacklist import Blacklist, Categories
from user import User

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Set your own thresholds for when to trigger a response
attributeThresholds = {
  'SEVERE_TOXICITY': 0.8,
  'PROFANITY': 0.8,
  'IDENTITY_ATTACK': 0.8,
  'THREAT': 0.8,
  'TOXICITY': 0.8,
  'FLIRTATION': 0.8,
  'SPAM': 0.7,
  'OBSCENE': 0.8,
}

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
        self.term_to_ban = None
        self.term_reason = None
        self.perspective_key = key
        self.user_to_ban = None
        self.waiting = False
        self.msg_to_delete = None
        self.awaiting_mod = False
        self.deleting_msg = False
        self.blacklistClass = Blacklist()

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

    async def on_message_edit(self, message_before, message_after):
        message = message_after
        if message.author.id == self.user.id:
            return
        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.automated(message)
        return

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
        if author_id not in self.reports and not (message.content.startswith(Report.START_KEYWORD) or message.content.startswith(Report.BAN_TERM_KEYWORD)):
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
                #handle keyword banning

                if isinstance(data, str):
                    if self.reports[author_id].state == State.EXPLAIN_KEYWORD:
                        self.term_to_ban = data
                        break
                    if self.reports[author_id].state == State.REPORT_COMPLETE:
                        self.term_reason = data
                        await self.mod_channel.send("Should we ban the term --- " + self.term_to_ban + " --- for the following reason?")
                        await self.mod_channel.send(self.term_reason + " --- please answer yes/no")
                        self.awaiting_mod = True
                        break


                #handle report filing
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
                if self.msg_to_delete == None:
                    await channel.send("Do you want to block " + reported_user.name  + "?  These are the reports against them " + str(reported_user.return_info()))
                    await channel.send("please respond, yes/no")

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        channel = message.channel
        if self.awaiting_mod and message.channel.name == f'group-{self.group_num}-mod':
            if message.content in Report.NO_KEYWORD:
                if self.term_to_ban != None:
                    await message.channel.send("Thank you. The keyword --" + self.term_to_ban + "-- will not be banned.")
                if self.deleting_msg:
                    await message.channel.send("Thank you. " + "The message will not be deleted.")
                    self.deleting_msg = False
                    self.msg_to_delete = None
                    if self.user_to_ban != None:
                        await channel.send("Do you want to block " + self.user_to_ban.name  + "?  These are the reports against them " + str(self.user_to_ban.return_info()))
                        await channel.send("please respond, yes/no")
                elif self.user_to_ban != None:
                    await message.channel.send("Thank you. " + self.user_to_ban.name + " will not be banned.")
                    self.user_to_ban = None

            if message.content in Report.YES_KEYWORD:
                if self.term_to_ban != None and self.term_reason != None:
                    self.blacklistClass.add_with_description(self.term_to_ban, self.term_reason)
                    await message.channel.send("Thank you. " + self.term_to_ban + " has been banned.")
                    censored_term = self.term_to_ban[:2] + '*'*(len(self.term_to_ban)-2)
                    self.term_to_ban = None
                    self.term_reason = None
                    await self.group_channel.send( "The term --- " + censored_term + " --- has been banned from our server.  Messages containing it will be deleted.")
                if self.deleting_msg:
                    await message.channel.send("Thank you. The message has been deleted.")
                    await self.msg_to_delete.delete()
                    self.deleting_msg = False
                    self.msg_to_delete = None
                    if self.user_to_ban != None:
                        await channel.send("Do you want to block " + self.user_to_ban.name  + "?  These are the reports against them " + str(self.user_to_ban.return_info()))
                        await channel.send("please respond, yes/no")
                elif self.user_to_ban != None:
                    await message.channel.send("Thank you. " + self.user_to_ban.name + " has been banned.")
                    await self.group_channel.send(self.user_to_ban.name  + " has been banned.")
                    self.user_to_ban = None

            if (self.user_to_ban == None and self.term_to_ban == None and self.deleting_msg == False):
                self.awaiting_mod = False
            return

        if not message.channel.name == f'group-{self.group_num}':
            return

        await self.automated(message)



    async def automated(self, message):
        #Blacklist comes preloaded with regex for bitcoin addresses as well as some dummy keywords like "Send Bitcoin".
        #Ability for mods to add new keywords will be
        for pattern, description in self.blacklistClass.blacklist.items():
            if re.search(pattern , message.content) != None:
                await self.group_channel.send(f"A message from \"" + message.author.name + f"\" has been flagged because -- {description}")
                await message.delete()
                #await self.mod_channel.send(f"Would you like us to delete the message.  Please respond with yes/no")
                #self.msg_to_delete = message
                #self.deleting_msg = True
                #self.awaiting_mod = True
        scores = self.eval_text(message)
        user_id = message.author.id
        msg = message
        violated_atts = [attribute for  attribute in attributeThresholds.keys() if scores[attribute] > attributeThresholds[attribute]]
        if len(violated_atts) > 0:
            await msg.reply(f'You got a strike for {violated_atts}')
            if user_id not in self.striked_users.keys():
                self.striked_users[user_id] = User(user_id)
            self.striked_users[user_id].num_strikes += 1
            if self.striked_users[user_id].num_strikes >= 3 and (not self.striked_users[user_id].is_banned()):
                self.striked_users[user_id].ban()
                await msg.reply(f'{user_id} has received three strikes and is now banned!')
        return

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

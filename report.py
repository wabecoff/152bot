from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    ABUSE_TYPE_RESPONSE = auto()
    ASK_FOR_CONTEXT = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    FETCH_KEYWORD = "fetch"
    HELP_KEYWORD = "help"
    YES_KEYWORD = {"yes","Yes","y","YES"}
    NO_KEYWORD = "no"
    ABUSE_TYPE = {"a","b","c","d"}
    STOP_READING_AS_TEXT = "this is a unique value"
    FETCH = "print users"
    PRINT_INFO = "this is a different unique"



    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.link = None
        self.reported_id = None
        self.type = ""
        self.context = ""
        self.file_report = False



    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord.
        '''
        while(True):
            if message.content == self.FETCH:
                self.file_report = False
                self.state = State.REPORT_COMPLETE
                return [self.PRINT_INFO]

            if message.content == self.CANCEL_KEYWORD:
                self.file_report = False
                self.state = State.REPORT_COMPLETE
                return ["Report cancelled.", [self.reported_id, self.type, self.context]]

            if self.state == State.REPORT_START:
                reply =  "Thank you for starting the reporting process. "
                reply += "Say `help` at any time for more information.\n\n"
                reply += "Please copy paste the link to the message you want to report.\n"
                reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
                self.state = State.AWAITING_MESSAGE
                return [reply]

            if self.state == State.AWAITING_MESSAGE:
                # Parse out the three ID strings from the message link
                m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
                if not m:
                    return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
                guild = self.client.get_guild(int(m.group(1)))
                if not guild:
                    return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
                channel = guild.get_channel(int(m.group(2)))
                if not channel:
                    return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
                try:
                    self.link = message.content
                    message = await channel.fetch_message(int(m.group(3)))
                except discord.errors.NotFound:
                    return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

                # Here we've found the message - it's up to you to decide what to do next!
                self.state = State.MESSAGE_IDENTIFIED
                self.reported_id = message.author.id
                val = ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                        "Is this the correct message? Answer yes/no."]
                await message.delete()
                return val

            if self.state == State.MESSAGE_IDENTIFIED:
                if message.content in(self.YES_KEYWORD):
                    self.state = State.ABUSE_TYPE_RESPONSE
                    return ["What type of abuse does this fall under? Type a for [], b for [], c for [], d for []"]
                if message.content == self.NO_KEYWORD:
                    self.state = State.AWAITING_MESSAGE
                    continue
            if self.state == State.ABUSE_TYPE_RESPONSE:
                if message.content in(self.ABUSE_TYPE):
                    self.type = message.content
                    self.state = State.ASK_FOR_CONTEXT
                    return ["Would you like to tell us more about why you reported this message? Please leave your comments or type 'none'."]
            if self.state == State.ASK_FOR_CONTEXT:
                self.context = message.content
                self.file_report = True
                data = [self.reported_id, self.link, self.type, self.context]
                return["Thank you for your report.", self.STOP_READING_AS_TEXT, data]
                self.State = State.REPORT_COMPLETE
            return ["this is a message"]


        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

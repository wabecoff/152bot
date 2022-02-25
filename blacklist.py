from enum import Enum, auto
from data import Data

class Categories:
    category_descriptions = {}
    OBVIOUS_FRAUD = auto()
    HATESPEECH = auto()
    SPAM = auto()


class Blacklist:

    def __init__(self):
        self.blacklist = Data.raw
        self.category_descs = {}
        #26-35 alphanumeric characters, starts with

        def add_with_description(pattern, description):
            self.blacklist[pattern] = description
            return

        def add_with_category(pattern, category):
            self.blacklist[pattern] = Categories.category_descriptions(category)
            return

        def remove_from_list(pattern):
            return

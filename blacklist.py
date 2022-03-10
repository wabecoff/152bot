from enum import Enum, auto
from data import Data
import os

class Categories:
    category_descriptions = {}
    OBVIOUS_FRAUD = auto()
    HATESPEECH = auto()
    SPAM = auto()


class Blacklist:

    def __init__(self):
        self.blacklist = Data.raw
        self.char_map = {'a': '[aA@]', 'A': '[aA@]', 'b': '[bB]', 'B': '[bB]', 'c': '[cCKk]', 'C': '[cCKk]', 'd': '[dD]', 'D': '[dD]', 'e': '[eE]', 'E': '[eE]', 'f': '[fF]', 'F': '[fF]', 'g': '[gG]', 'G': '[gG]', 'h': '[hH]', 'H': '[hH]', 'i': '[iI!]', 'I': '[iI!]', 'j': '[jJ]', 'J': '[jJ]', 'k': '[kKcC]', 'K': '[kKcC]', 'l': '[lL]', 'L': '[lL]', 'm': '[mM]', 'M': '[mM]', 'n': '[nN]', 'N': '[nN]', 'o': '[oO0]', 'O': '[oO0]', 'p': '[pP]', 'P': '[pP]', 'q': '[qQ]', 'Q': '[qQ]', 'r': '[rR]', 'R': '[rR]', 's': '[sS$]', 'S': '[sS$]', 't': '[tT]', 'T': '[tT]', 'u': '[uU]', 'U': '[uU]', 'v': '[vV]', 'V': '[vV]', 'w': '[wW]', 'W': '[wW]', 'x': '[xX]', 'X': '[xX]', 'y': '[yY]', 'Y': '[yY]', 'z': '[zZ]', 'Z': '[zZ]', '0':'[0oO]','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9','.':'\.','?':'\?',' ':' '}
        self.path = "data.txt"
        self.read_in(self.path)
        self.category_descs = {}

        #26-35 alphanumeric characters, starts with


    def read_in(self, path):
        with open(path, 'r') as f:
            for line in f:
                pair = line.split(':')
                if len(pair) == 2:
                    self.blacklist[pair[0]] = pair[1]


    def to_reg(self, keyword):
        reg = "( |^|\.|\!|,|\?)"
        end = "( |$|\.|\!|,|\?)"
        for char in keyword:
            if not char.isalnum() or char == ' ': continue
            reg += self.char_map[char] + self.char_map[char] + "?"
        reg += end
        return reg


    def add_with_description(self, keyword, description, add2file = "True"):
        reg = self.to_reg(keyword)
        self.blacklist[reg] = description
        if add2file:
            with open(self.path, 'a') as f:
                f.write(reg + ':' + description +'\n')
        #with open(path, 'r') as f:
        return

    def add_with_category(self, pattern, category):
        self.blacklist[pattern] = Categories.category_descriptions(category)
        return

    def remove_from_list(self, pattern):
        return

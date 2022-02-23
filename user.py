import uuid

class User:

    reports_to_strike = 2
    strikes_to_ban = 1
    report_id_ind = 0

    def __init__(self, id):
        self.id = id
        self.name = None
        self.num_strikes = 0
        self.link_dict = dict()
        self.banned = False

    def add_report(self, comment, data):
        should_delete = False
        report_id = uuid.uuid4()
        if comment not in self.link_dict.keys():
            self.link_dict[comment] = [data]
            self.name = data[0]
        else:
            for report in self.link_dict[comment]:
                #if author_id is the same
                if report[-1] == data[-1]:
                    return -1, should_delete
            self.link_dict[comment].append(data)
        if len(self.link_dict[comment]) == self.reports_to_strike:
            self.num_strikes += 1
            should_delete = True
        if self.num_strikes >= self.strikes_to_ban:
            self.banned = True
        return report_id, should_delete

    def remove_report(self, comment, report_id):
        report_list = self.link_dict[comment]
        for report in report_list:
            if report[report_id_ind] == report_id:
                report_list.remove(report)
        self.link_dict[comment] = self.report_list
        if len(self.link_dict[comment]) == (reports_to_strike-1):
            self.num_strikes -= 1
        if self.num_strikes <= self.strikes_to_ban:
            self.banned = False

    def hello(self):
        print("you're amazing, what you thought I'd say hello?")

    def print_out(self):
        print([self.id, self.num_strikes, self.link_dict, self.banned])

    def return_info(self):
        return [self.id, self.num_strikes, self.link_dict, self.num_strikes, self.banned]

    #def return_info(self):
        #return self.link_dict.items()

    def is_banned(self):
        return self.banned

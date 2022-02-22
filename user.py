import uuid

class User:

    reports_to_strike = 2
    strikes_to_ban = 2
    report_id_ind = 0

    def __init__(self, id):
        self.id = id
        self.num_strikes = 0
        self.link_dict = dict()
        self.banned = False

    def add_report(self, comment, data):
        if comment not in self.link_dict.keys():
            self.link_dict[comment] = [data]
            report_id = uuid.uuid4()
        else:
            for report in self.link_dict[comment]:
                #if author_id is the same
                if report[-1] == data[-1]:
                    return -1
            self.link_dict[comment].append(data)
            if len(link_dict[comment]) == reports_to_strike:
                self.num_strikes += 1
            if self.num_strikes >= strikes_to_ban:
                self.banned = True
        return report_id

    def remove_report(self, comment, report_id):
        report_list = self.link_dict[comment]
        for report in report_list:
            if report[report_id_ind] == report_id:
                report_list.remove(report)
        self.link_dict[comment] = report_list
        if len(link_dict[comment]) == (reports_to_strike-1):
            self.num_strikes -= 1
        if self.num_strikes <= strikes_to_ban:
            self.banned = False

    def hello(self):
        print("you suck, what you thought I'd say hello?????????")

    def print_out(self):
        print([self.id, self.num_strikes, self.link_dict, self.banned])

    def return_info(self):
        return [self.id, self.num_strikes, self.link_dict, self.num_strikes, self.banned]

    def return_info(self):
        return self.link_dict.items()

    def is_banned(self):
        return self.banned

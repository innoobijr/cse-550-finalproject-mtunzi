from collections import namedtuple
from collections import defaultdict

Session = namedtuple('Session', ['mac_addr', 'ipv4_addr', 'state', 'out_port', 'datapath'])

class SessionTable():

    def __init__(self):
        self.sessions = defaultdict(lambda: None)
        

    def add_session(self, session):
        self.sessions[session.ipv4_addr] = session

    def remove_session(self, session):
        return self.sessions.pop(session.ipv4_addr, None)

    def update_session_elem(self, ipv4_addr, elem, new_val):
        tmp = self.sessions[ipv4_addr]._asdict()
        tmp[elem] = new_val
        self.sessions[ipv4_addr] = Session(**tmp)
        return self.sessions[ipv4_addr]



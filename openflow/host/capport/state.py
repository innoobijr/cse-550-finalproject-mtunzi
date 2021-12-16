from enum import Enum


class SessionState(Enum):
    UNAUTHENTICATED = 1
    AUTHENTICATED = 2

class Messages(Enum):
    AUTHENTICATE_CLIENT = 1
    CLIENT_FLOW_READY = 2
    CLIENT_FLOW_FAIL = 3
    INFORM_AUTHENTICATOR = 4
    INFORM_CONTROLLER = 5

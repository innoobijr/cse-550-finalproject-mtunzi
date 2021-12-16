from os import write
import eventlet
from enum import Enum
import json 

eventlet.monkey_patch(socket=True)

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 5050        # Port to listen on (non-privileged ports are > 1023)


# set up sockets
#   turns internal socket api to green threads
# eventlet.monkey_patch(socket=True)
class Message(Enum):
    DISCONNECT_MSG = 1

    # sends from capport to auth
    AUTHENTICATE_CLIENT = 2

    # sends from auth to controller
    INFORM_CONTROLLER = 3

    # sends messages to auth 
    INFORM_AUTH = 4

    # sends messages to captive portal 
    INFORM_CAPPORT = 5

    # authentication process
    USER_AUTHENTICATED = 6
    USER_NOT_AUTHENTICATED = 7

    # sends from authenticators to each (DONE)
    CAPPORT_NOTIFICATION = 8
    CONTROLLER_NOTIFICATION = 9

    # for controller flow rules
    FLOW_SUCCESSFUL = 10
    FLOW_UNSUCCESSFUL = 11

    LOCAL_TEST = 9999


stub_capport_msg = {
                    "type": Message.INFORM_AUTH.value,
                    "data": {
                        "status": Message.FLOW_SUCCESSFUL.value,
                        "email": "firn@test.com",
                        'password': '1234',
                        "user_ip": '127.0.0.1',
                        }
                    }

def handle_as_capport(writer, msg):

    stub_capport_msg = {
            "type": Message.INFORM_AUTH.value,
            "data": {
                "status": Message.USER_AUTHENTICATED.value,
                "email": "firn@test.com",
                }
        }

    writer.write(json.dumps(stub_capport_msg))
    writer.write("\n")
    writer.flush()


def handle_as_controller(writer, msg):

    stub_controller_msg = {
                    "type": Message.CONTROLLER_NOTIFICATION.value,
                    "data": {
                        "status": Message.FLOW_SUCCESSFUL.value,
                        "email": msg['data']['email'],
                        "user_ip": msg['data']['user_ip'],
                        }
                    }

    writer.write(json.dumps(stub_controller_msg))
    writer.write("\n")
    writer.flush()

def handle(reader, writer):
    ## write to authenticator
    writer.write(json.dumps(stub_capport_msg))
    writer.write("\n")
    writer.flush()

    ## Now listen
    line = reader.readline()
    while line:
        msg = line.strip()
        msg = json.loads(msg)
            
        print("--------got data-------")
        
        if msg['type'] == Message.INFORM_CONTROLLER.value:
            
            status = msg['data']['status']
            print("------- in inform contrl-------")

            if (status == Message.USER_AUTHENTICATED.value):
                eventlet.spawn_n(handle_as_capport, writer, msg)

                print("------- in auth client-------")
            else: 
                print("------- not in auth client-------")
                eventlet.spawn_n(handle_as_controller, writer, msg)
        else:
           print("------- %s -------" % msg['data']['message'])

        line = reader.readline()

def connect_to_authenticator(ip_addr, port):
    conn = eventlet.connect((ip_addr, port))

    reader = conn.makefile("r")
    writer = conn.makefile("w")
    tok = eventlet.spawn(handle, reader, writer)

    tok.wait()

    print("[CONNECTING TO THE AUTH SOCKET ]: creating a conn from test")



if __name__ == "__main__":
    connect_to_authenticator(HOST, PORT)
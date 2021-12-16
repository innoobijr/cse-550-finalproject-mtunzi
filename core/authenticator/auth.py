import radius 
import json
from enum import Enum
import eventlet


# set up sockets
#   turns internal socket api to green threads
eventlet.monkey_patch(socket=True)


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



class Authenticator():

    def __init__(self, kwargs):
        self.addr = kwargs['server']
        self.port = kwargs['port']
        self.format = 'utf-8'
        self.secret = kwargs['secret']
        self.buf_size = 1024
        self.server = None
        self.ips = { 
             'controller': kwargs['controller_ip'],
             'capport': kwargs['capport_ip']
         }
        self.conns = {}

        # TODO: need to match everytime ip changes
        self.radius = radius.Radius(self.secret, host='10.18.231.160', port=1812)

        print(f"[RAD SOCKET CONNECTED]: A radius socket is connected on {self.radius}")

    def start(self):
        self.create_server_socket()

        # # TODO: ONLY for TESTING
        # self.listen_to_server_socket_stub()

        self.listen_to_server_socket()


    def create_server_socket(self):


        # self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.server.bind( (self.addr, self.port) )


        #   socket to Authenticator
        addr = self.addr
        port = self.port
        self.server = eventlet.listen((addr, port))

        print(f"[SOCKET CREATED]: A socket is created on {self.addr}")

    def listen_on_read(self, name):
        print("---------ready to read------------")
        reader = self.conns[name]['reader']
        line = reader.readline()
        print("---------ready to read-10-----------%s")

        while line:
            print("---------ready to read-1-----------")

            msg = line.strip()
            msg = json.loads(msg)

            # TODO: comparing value or type?????

            print("-----msg['type']------", msg['type'])
            print("----Message.INFORM_AUTH.value------", Message.INFORM_AUTH.value)

            if msg['type'] == Message.INFORM_AUTH.value:

                status = msg['data']['status']
                print(f"----STATUS: {status}")
                print(f"----Message.AUTHENTICATE_CLIENT.value: {Message.AUTHENTICATE_CLIENT.value}")

                if (status == Message.AUTHENTICATE_CLIENT.value): 
                    eventlet.spawn_n(self.do_on_authenticate_client, msg)

                    print("-------!!!! in auth client !!!-------")
                else:
                    # do after the controller adds rules
                    self.do_on_controller_notify(msg)

            elif msg['type'] == Message.LOCAL_TEST.value:
                print('--------LOCAL_TEST -----------')
                print(msg['data'])

            else:
                pass
            line = reader.readline()

    # TODO: ONLY FOR TESTING PURPOSES
    def listen_to_server_socket_stub(self):
        conn, addr = self.server.accept()		# accept the connection 
        reader = conn.makefile('r')
        writer = conn.makefile('w')
        print("--------conneciton-------")
        
        # TODO there is no name, listen_on_read won't work
        name = None
        print("--------conneciton2-------")

        self.conns['controller'] = {
            "sock": conn, 
            "reader": reader,
            "writer": writer
        }
        print("--------conneciton-3------")

        self.conns['localhost'] = {
            "sock": conn, 
            "reader": reader,
            "writer": writer
        }
        print("--------conneciton-4------")
        self.conns['capport'] = {
            "sock": conn, 
            "reader": reader,
            "writer": writer
        }
        
        name = 'localhost'
            
        # TODO: create a green thread
        h =  eventlet.spawn(self.listen_on_read, name)
        h.wait()
        print("--------conneciton-5------")


    def listen_to_server_socket(self):
        self.server.listen()

        while True:
            conn, addr = self.server.accept()		# accept the connection 
            name = None
            if addr == self.ips['controller']:
                name = 'controller'
                self.conns['controller'] = {
                    "sock": conn, 
                    "reader": conn.makefile('r'),
                    "writer": conn.makefile('w')}

            elif addr == '127.0.0.1':
                name = 'localhost'
                self.conns['localhost'] = {
                    "sock": conn, 
                    "reader": conn.makefile('r'),
                    "writer": conn.makefile('w')}
            else:
                name = 'capport'
                self.conns['capport'] = {
                    "sock": conn, 
                    "reader": conn.makefile('r'),
                    "writer": conn.makefile('w')}
            
            # TODO: create a green thread
            eventlet.spawn_n(self.listen_on_read,(name))

    def do_on_authenticate_client(self, msg):
        username = msg['data']['email']
        password = msg['data']['password']

        if self.radius.authenticate(username, password):
            msg['data']['status'] =  Message.USER_AUTHENTICATED.value
            print('-----------> user is authenticated')
            
        else:
            msg['data']['status'] = Message.USER_NOT_AUTHENTICATED.value
            print('----xxxxxx-------> authentication failed')

        self.do_inform_controller(msg)
        
        # print('success' if self.radius.authenticate(username, password) else 'failure')

        '''data = {
            "type": "",
            "data": {
                "ipv4_adr": "",
                "status": ""
            }
        }
        self.do_inform_controller(data)
        '''
        

    def do_inform_controller(self, d):
        
        conn_writer = self.conns['controller']['writer']
        d['type'] = Message.INFORM_CONTROLLER.value

        if (len(d) != 0):
            conn_writer.write(json.dumps(d))
            conn_writer.write('\n')    
            conn_writer.flush()
            print('Data is sent to the controller.')


    def do_on_controller_notify(self, msg):
        status = msg['data']['status']
        writer = self.conns['capport']['writer']

        status_message = lambda x: "Authenticated, you're good to go!" if x == Message.FLOW_SUCCESSFUL.value else "Authentication failed"

        print(status_message)
        msg = {
            "type": Message.INFORM_CAPPORT.value,
            "data": {
                "ipv4_adr": "127.0.0.1",
                "status": Message.USER_AUTHENTICATED.value,
                "message": status_message(status)
            }
        }
        writer.write(json.dumps(msg))
        writer.write("\n")
        writer.flush()


if __name__ == "__main__":
    print("[STARTING] Server is starting...")

    test = {
        'secret': 'testing123',
        'server': '127.0.0.1',
        'port': 5050,
        'controller_ip': '127.0.0.1',
        'capport_ip': '127.0.0.1'
    }

    authenticator_inst = Authenticator(test)
    authenticator_inst.start()
    #do_on_server_req()
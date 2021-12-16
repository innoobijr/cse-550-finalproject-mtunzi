import socket
import sys
import json
import threading
import eventlet
from enum import Enum
import time
from capport.state import Messages, SessionState

eventlet.monkey_patch(socket=True)


data = {
        'type': Messages.INFORM_AUTHENTICATOR.value,
        'data': {
            'status': SessionState.AUTHENTICATED.value,
             'ip': '192.168.2.90'
             }
        }

def main(*args, **kwargs):
    sock = create_socket('192.168.2.99', 8081)
    listen_on_socket(sock)

def create_socket(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    print("Created the socket")
    return server


def handle_client_conn(writer, reader): 
    line = reader.readline()
    while line:
            msg = line.strip()
            if (len(msg) > 0):
                #print('{"type": "AUTH"}' == str(data))
                msg = json.loads(msg)
                print(msg)
            line = reader.readline()

def stub_writer(writer):
    print("Stub writer running")
    eventlet.sleep(15)
    tmp = data
    tmp['type'] = Messages.INFORM_CONTROLLER.value
    tmp['data']['status'] = SessionState.AUTHENTICATED.value
    tmp['data']['ipv4_addr'] = '10.0.0.1'
    rx = json.dumps(tmp)
    #writer.write(rx)
    #writer.write('\n')
    #writer.flush()
    print("Stub writer written")


def listen_on_socket(listen_sock):
    listen_sock.listen()
    print("Listening")
    while True:
        conn, addr = listen_sock.accept()
        writer = conn.makefile('w')
        reader = conn.makefile('r')
        eventlet.spawn_n(handle_client_conn, writer, reader)
        eventlet.spawn_n(stub_writer, writer)
        #writer.write(json.dumps(data))
        #writer.write("\n")
        #writer.flush()
        print("Connected client {}. Now Forking thread".format(addr))

if __name__ == "__main__":
    main()



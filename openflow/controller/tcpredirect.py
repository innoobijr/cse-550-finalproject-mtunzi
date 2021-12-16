from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import addrconv
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4, tcp, udp
from ryu.lib import hub
import eventlet
import socket
import json
import configparser

from basil.mods import Session, SessionTable
from basil.state import SessionState, Messages

eventlet.monkey_patch(socket=True)

class TCPRedirect(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TCPRedirect, self).__init__(*args, **kwargs)
        config = configparser.ConfigParser()
        config.read('capport.ini')

        self.datapath = None

        self.cap_mac = config['captive_portal']['mac_address']
        self.cap_ip = config['captive_portal']['ipv4_addr']
        self.cap_oport = int(config['captive_portal']['output_port'])
        self.cap_port = int(config['captive_portal']['ip_port'])
        self.nat = config['nat']
        self.session_table = SessionTable()
        self.authenticator = {'writer':None, 'reader':None}

        self.green_pile = eventlet.GreenPile()
        self.addr = (config['authenticator']['ipv4_addr'], int(config['authenticator']['ip_port']))
        self.name = "tcpredirect"
        self.auth_thread = hub.spawn(self._monitor)
        self.mac_to_port = {}
        self.mac_to_ports = {}
        self.mac_pairs = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        self.datapath = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port=ofproto.OFPP_CONTROLLER,
                                          max_len=ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(type_=ofproto.OFPIT_APPLY_ACTIONS,
                                             actions=actions)]
        inst_fd = [parser.OFPInstructionActions(type_=ofproto.OFPIT_APPLY_ACTIONS,
            actions=[parser.OFPActionOutput(port=ofproto.OFPP_FLOOD)])]

        
        instruction = [
        parser.OFPInstructionActions(ofproto.OFPIT_CLEAR_ACTIONS, [])
        ]
        
        mod_all = parser.OFPFlowMod(datapath=datapath,
                                priority=1,
                                command = ofproto.OFPFC_ADD,
                                match=parser.OFPMatch(),
                                instructions=inst)

        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=1,
                                command = ofproto.OFPFC_ADD,
                                match=parser.OFPMatch(
                                    eth_type=0x800,
                                    ip_proto=17,
                                    udp_dst=53),
                                instructions=instruction)

        mod_http = parser.OFPFlowMod(datapath=datapath,
                                priority=1,
                                match=parser.OFPMatch(
                                    eth_type=0x800,
                                    ip_proto=6,
                                    tcp_dst=80
                                    ),
                                instructions=inst)

        mod_http2 = parser.OFPFlowMod(datapath=datapath,
                                priority=1,
                                match=parser.OFPMatch(
                                    eth_type=0x800,
                                    ip_proto=6,
                                    tcp_dst=443
                                    ),
                                instructions=inst)

        mod_https = parser.OFPFlowMod(datapath=datapath,
                                priority=1,
                                match=parser.OFPMatch(
                                    eth_type=0x800,
                                    ip_proto=6,
                                    tcp_dst=8080
                                    ),
                                instructions=inst)

        mod_arp = parser.OFPFlowMod(datapath=datapath,
                                    priority=0,
                                    match=parser.OFPMatch(
                                                            eth_type=0x806),
                                    instructions=inst_fd)

        mod_udp_fd = parser.OFPFlowMod(datapath=datapath,
                                    priority=0,
                                    match=parser.OFPMatch(
                                                            eth_type=0x800,
                                                            ip_proto=17,
                                                            udp_src=68,
                                                            udp_dst=67),
                                    instructions=inst_fd)

        mod_udp_rv = parser.OFPFlowMod(datapath=datapath,
                                    priority=0,
                                    match=parser.OFPMatch(
                                                            eth_type=0x800,
                                                            ip_proto=17,
                                                            udp_src=67,
                                                            udp_dst=68),
                                    instructions=inst_fd)

        inst_cap = [
        parser.OFPInstructionActions(type_=ofproto.OFPIT_APPLY_ACTIONS, actions=[parser.OFPActionOutput(port=self.cap_oport)])]

        match_there = parser.OFPMatch(
                eth_type = 0x800,
                eth_dst = self.cap_mac,
                ipv4_dst = self.cap_ip

        )

        mod_cap = parser.OFPFlowMod(datapath=datapath,
                                    priority=2100,
                                    match=match_there,
                                    instructions=inst_cap)

       # datapath.send_msg(mod_cap)
        #datapath.send_msg(mod_udp_rv)
        datapath.send_msg(mod_http)
        datapath.send_msg(mod_http2)
        datapath.send_msg(mod_https)
        #datapath.send_msg(mod_all)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        self.logger.info("Getting a packet")
        pkt = packet.Packet(data=msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        udp_pkt = pkt.get_protocol(udp.udp)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        eth_src = eth_pkt.src
        eth_dst = eth_pkt.dst

        
        if self.mac_pairs.get(eth_src+eth_dst, False):
            self.logger.info("%s: Seeing an rule again" % self.name)
            self.clear_double_rules(datapath, eth_src, eth_dst)
            if eth_dst in self.mac_to_port:
                del self.mac_to_port[eth_dst]
                del self.mac_to_port[eth_src]

        else:
            self.mac_pairs[eth_src+eth_dst] = True

        self.logger.info("%s: Port is %s" % (self.name, in_port))

        self.mac_to_port[eth_src] = in_port

        if eth_dst in self.mac_to_port:
            out_port = self.mac_to_port[eth_dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if udp_pkt:
            self.logger.info("%s: UDP Packet : port %s " % (self.name, udp_pkt.src_port))
        if tcp_pkt:
            if not ('10.0' in ipv4_pkt.src):
                self.logger.info("%s: packet is not from subnet" % self.name)
                return

            if tcp_pkt.dst_port == 80:
                self.logger.info("%s: HTTP Packet" % self.name)
            elif tcp_pkt.dst_port == 8080:
                self.logger.info("%s: HTTP2 Packet" % self.name)
            else:
                self.logger.info("%s: HTTPS Packet" % self.name)

            # check if session exists
            if not self.session_table.sessions.get(ipv4_pkt.src, False):
                self.logger.info("%s: USer not in table" % (self.name))

                self.session_table.add_session(Session(eth_src, ipv4_pkt.src, SessionState.UNAUTHENTICATED, in_port, datapath))
            self._handle_tcp(datapath, in_port, pkt)
            if ipv4_pkt.dst != self.cap_ip:
                self._handle_tcp(datapath, in_port, pkt)
            else:
                self.logger.info("%s: ***DETAILS**\n\n\t %s\n\t %s" % 
                        (self.name,
                            ipv4_pkt.src, 
                            ipv4_pkt.dst
                            ))
                        #self.allow_portal_flow(datapath, pkt, in_port)
            if out_port != ofproto.OFPP_FLOOD:
                self.logger.info("%s: OFPP_FLOOD" % self.name)
                match = parser.OFPMatch(in_port=in_port, eth_dst=eth_dst)
                self.add_flow(datapath, 2, match, actions)
            
        self.logger.info("%s: %s" %(self.name, "construct packet_out message and send it."))
        out = parser.OFPPacketOut(datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port, actions=actions,
                data=msg.data)
                
        datapath.send_msg(out)
        
    def allow_portal_flow(self, datapath, pkt,in_port):
        
        parser = datapath.ofproto_parser
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        src = eth_pkt.src
        dst = eth_pkt.dst
        ip_src = ipv4_pkt.src
        ip_dst = ipv4_pkt.dst


        match_back = parser.OFPMatch(
                eth_type = 0x800,
                eth_dst = self.cap_mac,
                ipv4_dst = self.cap_ip,
                eth_src = src,
                ipv4_src = ip_src
        )

        actions_back=[parser.OFPActionOutput(port=self.cap_oport)]

        self.logger.info("%s: adding capport rule" % self.name)

        self.add_flow(datapath, 2100, match_back, actions_back)

    def add_forward_flow(self, pkt, datapath, priority, port):
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        src = eth_pkt.src
        dst = eth_pkt.dst
        ip_src = ipv4_pkt.src
        ip_dst = ipv4_pkt.dst

        parser = datapath.ofproto_parser

        self.logger.info("%s: creating the matches i| IP TYPE is: %s %s" % (self.name, type(ip_src), ip_src))

        #if src == dst:
        #    return

        match = parser.OFPMatch(
                eth_type = 0x800,
                eth_src = src, 
                eth_dst = dst,
                ipv4_src = ip_src,
                ipv4_dst = ip_dst
        )

        actions = [
                parser.OFPActionSetField(eth_dst=self.cap_mac),
                parser.OFPActionSetField(ipv4_dst=self.cap_ip),
                parser.OFPActionOutput(self.cap_oport)]
        self.logger.info("%s: adding forward flow rule" % self.name)

        #if (dst == self.cap_mac) and (ip_dst == self.cap_ip):
        #    return

        self.add_flow(datapath, priority, match, actions)

    def add_reverse_flow(self, pkt, datapath, priority, port):
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        src = eth_pkt.src
        dst = eth_pkt.dst
        ip_src = ipv4_pkt.src
        ip_dst = ipv4_pkt.dst

        parser = datapath.ofproto_parser

        self.logger.info("%s: creating the matches i| IP TYPE is: %s %s" % (self.name, type(ip_src), ip_src))

       #if self.cap_mac == src:
       #     return

        match = parser.OFPMatch(
                eth_type = 0x800,
                eth_src = self.cap_mac, 
                eth_dst = src,
                ipv4_src = self.cap_ip,
                ipv4_dst = ip_src
        )

        actions = [
                parser.OFPActionSetField(eth_src=dst),
                parser.OFPActionSetField(ipv4_src=ip_dst),
                parser.OFPActionOutput(port)]
        self.logger.info("%s: adding reverse flow rule" % self.name)

        #if (self.cap_mac == dst) and (self.cap_ip == ip_dst):
        #    ## avoid cycles
        #    return

        self.add_flow(datapath, priority, match, actions)

       
    def _handle_tcp(self,datapath, port, pkt):
        self.logger.info("%s: Handling TCP stuff")
        eth_pkt_src = pkt.get_protocol(ethernet.ethernet).src
        eth_pkt_dst = pkt.get_protocol(ethernet.ethernet).dst
        ip_pkt_src =  pkt.get_protocol(ipv4.ipv4).src

        #self.allow_portal_flow(datapath, pkt,  port)

        self.logger.info("%s: session-table %s" % (self.name, self.session_table.sessions[ip_pkt_src]))
        session =  self.session_table.sessions[ip_pkt_src]

        if (eth_pkt_src == self.nat['mac_addr'] and eth_pkt_dst == self.nat['mac_addr']):
            return

        if session.state == SessionState.UNAUTHENTICATED:
            self.logger.info("%s: reading a new or unauthenticatged client, setting default rules" % self.name)
            self.add_reverse_flow(pkt, datapath, 2000, port)
            self.add_forward_flow(pkt, datapath, 2000, port)
    
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
            actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,match=match, instructions=inst)

        self.logger.info("%s: rule sent to switch" % self.name)
        datapath.send_msg(mod)

    def clear_double_rules(self, datapath, eth_src, eth_dst):
        # add to session_table: update status to authenticated
        # remove all rule where user is src or target
        # on next run use will gt directed to controller with will allow learning switch
        # to pass user through
        self.logger.info("%s: %s | clearing double rules" %( self.name, 'fn:clear_capport_rules'))
        parser = datapath.ofproto_parser
        match_eth_src = parser.OFPMatch(
                eth_type = 0x800,
                eth_src = eth_src,
                eth_dst = eth_dst
        )

        match_eth_dst = parser.OFPMatch(
                eth_type = 0x800,
                eth_src = eth_dst,
                eth_dst = eth_src
        )
        self.logger.info("%s: %s | modifying the session table" %( self.name, 'fn:clear_capport_rules'))
        # Now with matches update session table (do this in a transaction)
        self.del_flow(datapath, match_eth_src)
        self.del_flow(datapath, match_eth_dst)



    def clear_capport_rules(self, session):
        # add to session_table: update status to authenticated
        # remove all rule where user is src or target
        # on next run use will gt directed to controller with will allow learning switch
        # to pass user through
        self.logger.info("%s: %s | clearing capport rules" %( self.name, 'fn:clear_capport_rules'))
        parser = self.datapath.ofproto_parser
        match_eth_src = parser.OFPMatch(
                eth_type = 0x800,
                eth_src = session.mac_addr,
                ipv4_src = session.ipv4_addr
        )

        match_eth_dst = parser.OFPMatch(
                eth_type = 0x800,
                eth_dst = session.mac_addr,
                ipv4_dst = session.ipv4_addr
        )
        self.logger.info("%s: %s | modifying the session table" %( self.name, 'fn:clear_capport_rules'))
        # Now with matches update session table (do this in a transaction)
        self.session_table.update_session_elem(session.ipv4_addr, "state", SessionState.AUTHENTICATED)

        self.logger.info("%s: %s" % (self.name, self.session_table.sessions[session.ipv4_addr]))
        self.logger.info("%s: %s | deleting the rules" %( self.name, 'fn:clear_capport_rules'))

        # Delete Rules
        self.del_flow(session.datapath, match_eth_src)
        self.del_flow(session.datapath, match_eth_dst)


    def del_flow(self, datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        mod = parser.OFPFlowMod(datapath=datapath,
                command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
                match=match)

        datapath.send_msg(mod)


    def send_packet(self, datapath, port, pkt):
        
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        
        out = parser.OFPPacketOut(datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=ofproto.OFPP_CONTROLLER,
                actions=actions,
                data=data)

        datapath.send_msg(out)


    def _handle_authenticator(self, auth):
        line = auth['reader'].readline()
        while line:
            self.logger.info("%s: Getting a message" % self.name)
            msg = line.strip()
            if (len(msg) > 0):
                msg = json.loads(msg)
                self.logger.info("%s: %s" % (self.name, msg['type']))
                if msg['type'] == Messages.INFORM_CONTROLLER.value:
                    if msg['data']['status'] == SessionState.AUTHENTICATED.value:
                        tmp = self.session_table.sessions[msg['data']['ipv4_addr']]
                        self.logger.info("%s: %s" % (self.name, tmp))
                        self.clear_capport_rules(tmp)
                        # flood the rest of the traffic 
            line = auth['reader'].readline()

    def _monitor(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger.info("%s: %s" % (self.name, self.addr))
        client.connect(self.addr)
        self.authenticator['reader'] = client.makefile('r')
        self.authenticator['writer'] = client.makefile('w')
        eventlet.spawn_n(self._handle_authenticator, self.authenticator)
        self.logger.info("%s: Monitoring thread started and connected to authenticator at %s" % (self.name, self.addr[0]))

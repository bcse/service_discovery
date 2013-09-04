#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket


class BroadcastSocket(socket.socket):

    def __init__(self, max_packet_size=8192):
        self.max_packet_size = max_packet_size

        # create socket
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_DGRAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.setblocking(0)

    def write(self, datagram, addr):
        self.sendto(datagram, addr)

    def read(self):
        while True:
            data, addr = self.recvfrom(self.max_packet_size)
            yield (data, addr)


if __name__ == '__main__':
    broadcast_addresses = ('<broadcast>', '255.255.255.255', '127.0.0.1')

    # Plex GDM
    broadcast_sockets = []
    for addr in broadcast_addresses:
        print addr
        s = BroadcastSocket()
        s.sender = addr
        s.settimeout(1.0)
        try:
            s.write('M-SEARCH * HTTP/1.0', (addr, 32414))
            broadcast_sockets.append(s)
        except socket.error, e:
            print e

    import email
    server_list = {}
    for s in broadcast_sockets:
        try:
            for data, server in s.read():
                response_status, header = data.split('\r\n', 1)
                headers = email.message_from_string(header)
                print s.sender, server
                res_id = headers.get('Resource-Identifier')
                if res_id is not None and res_id not in server_list:
                    server_info = dict(headers.items())
                    server_info['Address'] = server[0]
                    server_list[res_id] = server_info
        except socket.timeout:
            pass
        finally:
            s.close()

    for server in server_list.values():
        for k, v in server.iteritems():
            print k, '=', v
        print


    # SSDP
    msg = ('M-SEARCH * HTTP/1.1\r\n'
           'MX: 3\r\n'
           'ST: upnp:rootdevice\r\n'
           'HOST: 239.255.255.250:1900\r\n'
           'MAN: "ssdp:discover"\r\n'
           '\r\n')

    broadcast_sockets = []
    for addr in broadcast_addresses:
        s = BroadcastSocket()
        s.settimeout(1.0)
        try:
            s.write(msg, (addr, 1900))
            broadcast_sockets.append(s)
        except socket.error, e:
            print e

    import email
    server_list = {}
    for s in broadcast_sockets:
        try:
            for data, server in s.read():
                response_status, header = data.split('\r\n', 1)
                headers = email.message_from_string(header)
                res_id = headers.get('USN')
                if res_id is not None and res_id not in server_list:
                    server_info = dict(headers.items())
                    server_list[res_id] = server_info
        except socket.timeout:
            pass
        finally:
            s.close()

    for server in server_list.values():
        for k, v in server.iteritems():
            print k, '=', v
        print

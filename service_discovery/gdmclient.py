#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import email

from broadcast_socket import BroadcastSocket
from multicast_socket import MulticastSocket


def discover(interface=None, timeout=1.0):
    gdm_group = ('239.0.0.250', 32414)
    msg = 'M-SEARCH * HTTP/1.0'

    sockets = []

    # discover with multicast
    s = MulticastSocket(interface=interface)
    s.set_outgoing_interface()
    s.set_ttl(1)  # multicast will cross router hops if TTL > 1
    s.settimeout(timeout)
    try:
        s.join_group(gdm_group[0])
        s.write(msg, gdm_group)
        sockets.append(s)
    except socket.error:
        pass

    # discover with broadcast
    broadcast_addresses = ['<broadcast>', '255.255.255.255', '127.0.0.1']
    if interface is None:
        pass
    elif interface.startswith('192.168.'):
        addr = '.'.join(interface.split('.')[:3] + ['255'])
        broadcast_addresses.insert(0, addr)
    elif interface.startswith('10.'):
        broadcast_addresses.insert(0, '10.255.255.255')

    for addr in broadcast_addresses:
        s = BroadcastSocket()
        s.settimeout(timeout)
        try:
            s.write(msg, (addr, gdm_group[1]))
            sockets.append(s)
        except socket.error:
            pass

    server_list = {}
    for s in sockets:
        try:
            for data, server in s.read():
                response_status, header = data.split('\r\n', 1)
                headers = email.message_from_string(header)
                res_id = headers.get('Resource-Identifier')
                if res_id is not None and res_id not in server_list:
                    server_info = dict(headers.items())
                    server_info['Address'] = server[0]
                    server_list[res_id] = server_info
        except socket.timeout:
            pass
        finally:
            if hasattr(s, 'leave_group'):
                s.leave_group(gdm_group[0])
            s.close()

    return server_list


if __name__ == '__main__':
    interface = socket.gethostbyname(socket.gethostname())

    server_list = discover(interface)
    print 'Discoverd %d server(s)' % len(server_list)
    print

    for server in server_list.values():
        for k, v in server.iteritems():
            print k, '=', v
        print

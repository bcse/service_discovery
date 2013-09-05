#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import email

from broadcast_socket import BroadcastSocket
from multicast_socket import MulticastSocket


def discover(interface=None, timeout=1.0):
    ssdp_group = ('239.255.255.250', 1900)
    msg = ('M-SEARCH * HTTP/1.1\r\n'
           'MX: 3\r\n'
           'ST: upnp:rootdevice\r\n'
           'HOST: %s:%s\r\n'
           'MAN: "ssdp:discover"\r\n'
           '\r\n') % ssdp_group

    sockets = []

    # discover with multicast
    s = MulticastSocket(interface=interface)
    s.set_outgoing_interface()
    s.set_ttl(1)  # multicast will cross router hops if TTL > 1
    s.settimeout(timeout)
    s.join_group(ssdp_group[0])
    try:
        s.write(msg, ssdp_group)
    except socket.error:
        s.leave_group(ssdp_group[0])
        s.close()
    else:
        sockets.append(s)

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
            s.write(msg, (addr, ssdp_group[1]))
        except socket.error:
            s.close()
        else:
            sockets.append(s)

    server_list = {}
    for s in sockets:
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
            if hasattr(s, 'leave_group'):
                s.leave_group(ssdp_group[0])
            s.close()

    return server_list


if __name__ == '__main__':
    import sys
    interface = socket.gethostbyname(socket.gethostname())

    server_list = discover(interface)
    print 'Discoverd %d server(s)' % len(server_list)
    print

    if '--verbose' in sys.argv:
        for server in server_list.values():
            for k, v in server.iteritems():
                print k, '=', v
            print

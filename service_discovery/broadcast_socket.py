#!/usr/bin/env python
# -*- coding: utf-8 -*-

# BroadcastSocket is implemented based on Twisted <http://twistedmatrix.com/>.

# Twisted, the Framework of Your Internet
# Copyright (c) 2001-2013 Twisted Matrix Laboratories.
# See LICENSE for details.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import socket

if os.name in ('nt', 'ce'):
    from errno import (WSAEWOULDBLOCK as EAGAIN,
                       WSAEINTR as EINTR,
                       WSAEMSGSIZE as EMSGSIZE,
                       WSAETIMEDOUT as ETIMEDOUT,
                       WSAECONNREFUSED as ECONNREFUSED,
                       WSAECONNRESET as ECONNRESET,
                       WSAENETRESET as ENETRESET,
                       WSAEINPROGRESS as EINPROGRESS)

    # Classify read and write errors
    _sockErrReadIgnore = (EAGAIN, EINTR, EMSGSIZE, EINPROGRESS)
    _sockErrReadRefuse = (ECONNREFUSED, ECONNRESET, ENETRESET, ETIMEDOUT)
else:
    from errno import (EWOULDBLOCK, EINTR, EMSGSIZE, ECONNREFUSED, EAGAIN)
    _sockErrReadIgnore = (EAGAIN, EINTR, EWOULDBLOCK)
    _sockErrReadRefuse = (ECONNREFUSED,)


class BroadcastSocket(socket.socket):

    def __init__(self, max_packet_size=8192):
        self.max_packet_size = max_packet_size

        # create socket
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_DGRAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.setblocking(0)

    def write(self, datagram, addr):
        try:
            self.sendto(datagram, addr)
        except socket.error, e:
            no = e.args[0]
            if no == EINTR:
                return self.write(datagram, addr)
            # elif no == EMSGSIZE:
            #     raise error.MessageLengthError("message too long")
            elif no == ECONNREFUSED:
                # in non-connected UDP ECONNREFUSED is platform dependent, I
                # think and the info is not necessarily useful. Nevertheless
                # maybe we should call connectionRefused? XXX
                return
            else:
                raise

    def read(self):
        while True:
            try:
                data, addr = self.recvfrom(self.max_packet_size)
            except socket.error, e:
                no = e.args[0]
                if no in _sockErrReadIgnore:
                    break
                if no in _sockErrReadRefuse:
                    break
                raise
            else:
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

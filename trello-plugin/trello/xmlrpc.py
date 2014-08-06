'''
@author: matteo@magni.me
'''

import xmlrpclib

class XmlRpc():

    server = None

    '''
    ticket.update(int id, string comment, struct attributes={}, boolean notify=False, string author="", DateTime when=None)
    '''
    def addComment(self, idTicket, comment, author = "", when = None, attributes = {}, notify = False):
        self.server.ticket.update(idTicket, comment, attributes, notify, author)

    def login(self, user, password, url, protocol):
        self.server = xmlrpclib.ServerProxy(protocol + '://' + user + ':' + password + '@' + url)


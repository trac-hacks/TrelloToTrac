'''
@author: matteo@magni.me
'''
import json
from trolly.client import Client
from trolly.organisation import Organisation
from trolly.board import Board
from trolly.list import List
from trolly.card import Card
from trolly.checklist import Checklist
from trolly.member import Member
from trolly.trelloobject import TrelloObject
from trolly import ResourceUnavailable

import urllib2

class TrelloClient(Client):
    def __init__(self, apiKey, userAuthToken):
        Client.__init__(self, apiKey, userAuthToken )
        #super(TrelloClient, self).__init__( apiKey, userAuthToken )

    def cardExist(self, cardId):
        try:
            query_params = {}
            query_params = self.addAuthorisation(query_params)
            uri_path = '/cards/' + cardId
            uri = self.buildUri( uri_path, query_params )
            fileHandle = urllib2.urlopen(uri)
            data = fileHandle.read()
            fileHandle.close()
            return {'res':True}
        except urllib2.URLError, e:
            return {'res':False}

    def cardShortIdExist(self, cardShortId, boardId):
        try:
            query_params = {}
            query_params = self.addAuthorisation(query_params)
            uri_path = '/boards/' + boardId + '/cards/' + cardShortId
            uri = self.buildUri( uri_path, query_params )
            fileHandle = urllib2.urlopen(uri)
            data = fileHandle.read()
            fileHandle.close()
            data = json.loads( data )
            return {'res':True,'id':data['id']}
        except urllib2.URLError, e:
            return {'res':False}

    def boardExist(self, boardId):
        try:
            query_params = {}
            query_params = self.addAuthorisation(query_params)
            uri_path = '/boards/' + boardId
            uri = self.buildUri( uri_path, query_params )
            fileHandle = urllib2.urlopen(uri)
            data = fileHandle.read()
            fileHandle.close()
            return {'res':True}
        except urllib2.URLError, e:
            return {'res':False}

    def listExist(self, listId):
        try:
            query_params = {}
            query_params = self.addAuthorisation(query_params)
            uri_path = '/lists/' + listId
            uri = self.buildUri( uri_path, query_params )
            fileHandle = urllib2.urlopen(uri)
            data = fileHandle.read()
            fileHandle.close()
            data = json.loads( data )
            return {'res':True, 'boardId':data['idBoard']}
        except urllib2.URLError, e:
            return {'res':False}


class TrelloBoard(Board):
    def __init__(self, trelloClient, boardId):
        Board.__init__(self, trelloClient, boardId )
        #super(TrelloBoard, self).__init__( trelloClient, boardId )
    def getCardByShortId(self, shortId):
        return self.fetchJson(
            uri_path = self.base_uri+'/cards/'+shortId,
            query_params = {}
        )


class TrelloList(List):
    def __init__(self, trelloClient, listId):
        List.__init__(self, trelloClient, listId )
        #super(TrelloList, self).__init__( trelloClient, listId )

    def getActions(self):
        return self.fetchJson(
            uri_path = self.base_uri+'/actions',
            query_params = {'fields' : 'all'}
        )

class TrelloCard(Card):
    def __init__(self, trelloCard, cardId):
        Card.__init__(self, trelloCard, cardId)
        #super(TrelloCard, self).__init__( trelloClient, cardId )

    def getComments(self):
        return self.fetchJson(
            uri_path = self.base_uri+'/actions',
            query_params = {'filter':'commentCard'}
        )

    def getChecklists(self):
        return self.fetchJson(
            uri_path = self.base_uri+'/idChecklists',
            query_params = {}
        )

    def getAttachments(self):
        return self.fetchJson(
            uri_path = self.base_uri+'/attachments',
            query_params = {}
        )

    def getMembers(self):
        response = self.fetchJson(
        uri_path = self.base_uri,
            query_params = {'members' : 'true', 'limit' : 300}
        )
        return response['members']

    def getCreateCard(self):
        response =  self.fetchJson(
            uri_path = self.base_uri,
            query_params = {'actions' : 'createCard'}
        )
        if len(response['actions']) != 0:
            return response
        else:
            # date
            json_action = """
            {
                "idMemberCreator": "",
                "date":""
            }"""
            response['actions'].insert(0,json.loads(json_action))
        return response

    def addLinkAttachment(self, link):
        return self.fetchJson(
            uri_path=self.base_uri + '/attachments',
            http_method='POST',
            query_params={'url': link, 'name': link}
        )


class TrelloChecklist(Checklist):
    def __init__(self, trelloClient, checklistId):
        Checklist.__init__(self, trelloClient, checklistId )
        #super(TrelloChecklist, self).__init__( trelloClient, checklistId )


class TrelloWebhook(TrelloObject):
    def __init__(self, trelloClient, webhookId):
        super(TrelloWebhook, self).__init__(trelloClient)
        self.id = webhookId
        self.base_uri = '/webhook/' + self.id


class TrelloWebhookAction(TrelloObject):
    def __init__(self, trelloClient, actionId):
        super(TrelloWebhookAction, self).__init__(trelloClient)
        self.id = actionId

    def loadJson(self, json):
        self.type = json['action']['type']
        self.date = json['action']['date']
        self.idMemberCreator = json['action']['memberCreator']['id']
        self.data = json['action']['data']
        self.json = json


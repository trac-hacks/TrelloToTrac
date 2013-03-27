from trolly.client import Client
from trolly.organisation import Organisation
from trolly.board import Board
from trolly.list import List
from trolly.card import Card
from trolly.checklist import Checklist
from trolly.member import Member
from trolly import ResourceUnavailable

class TrelloClient(Client):
    def __init__(self, apiKey, userAuthToken):
        Client.__init__(self, apiKey, userAuthToken )
        #super(TrelloClient, self).__init__( apiKey, userAuthToken )

class TrelloBoard(Board):
    def __init__(self, trelloClient, boardId):
        Board.__init__(self, trelloClient, boardId )
        #super(TrelloBoard, self).__init__( trelloClient, boardId )

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
        return response


class TrelloChecklist(Checklist):
    def __init__(self, trelloClient, checklistId):
        Checklist.__init__(self, trelloClient, checklistId )
        #super(TrelloChecklist, self).__init__( trelloClient, checklistId )

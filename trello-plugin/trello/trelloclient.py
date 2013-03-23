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

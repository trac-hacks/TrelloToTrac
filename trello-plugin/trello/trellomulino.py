from trolly.client import Client
from trolly.organisation import Organisation
from trolly.board import Board
from trolly.list import List
from trolly.card import Card
from trolly.checklist import Checklist
from trolly.member import Member
from trolly import ResourceUnavailable

class TrelloMulino():
    
    def __init__( self, api_key, user_auth_token):
        self.client = Client( api_key, user_auth_token )

    def getBoards( self, board_id ):
        self.board = Board( self.client, board_id )
        result = self.board.getBoardInformation();
        return result;



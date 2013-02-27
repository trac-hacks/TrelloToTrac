import configparser
from trolly.client import Client
from trolly.organisation import Organisation
from trolly.board import Board
from trolly.list import List
from trolly.card import Card
from trolly.checklist import Checklist
from trolly.member import Member
from trolly import ResourceUnavailable

config = configparser.ConfigParser()
config.read('config/config.ini')
api_key = config.get('trello', 'api_key') 
user_auth_token = config.get('trello', 'user_auth_token') 
board_id = config.get('trello', 'board_id') 

class TracHello():
    
    def __init__( self ):
        self.client = Client( api_key, user_auth_token )
        self.board = Board( self.client, board_id )

    def test_org_02_getBoards( self ):
        result = self.board.getBoardInformation();
        print result;


trac = TracHello()
trac.test_org_02_getBoards();

import re
from genshi.builder import tag
from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider

import trelloclient

class TracTrelloPlugin(Component):

    implements(INavigationContributor, IRequestHandler, ITemplateProvider)
   
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'Trello'
    
    def get_navigation_items(self, req):
        if 'TRAC_ADMIN' in req.perm: 
            yield ('mainnav', 'trello',
                tag.a('Trello', href=req.href.trello()))
    
    # IRequestHandler methods
    def match_request(self, req):
	if 'TRAC_ADMIN' in req.perm: 
        	return re.match(r'/trello(?:_trac)?(?:/.*)?$', req.path_info)
    def process_request(self, req):
        data = {}
        apiKey = self.config.get('trello', 'api_key') 
        userAuthToken = self.config.get('trello', 'user_auth_token') 
        boardId = self.config.get('trello', 'board_id') 
        listId = self.config.get('trello', 'list_id') 
        data['board_id'] = boardId
        data['list_id'] = listId

        trello = trelloclient.TrelloClient(apiKey,userAuthToken)
        board = trelloclient.TrelloBoard(trello, boardId)
        theList = trelloclient.TrelloList(trello, listId)

        boardInformation = board.getBoardInformation()
        data['board_name'] = boardInformation['name']

        listInformation = theList.getListInformation()
        data['list_name'] = listInformation['name']

        #elenco liste
        listsView = []
        boardLists = board.getLists()
        for l in boardLists:
            listInfo = l.getListInformation()
            listsView.append(listInfo)
        data['lists'] = listsView
            
        cardsView = []
        cards = theList.getCards()
        for c in cards:
            cardInformation = c.getCardInformation()
            cardsView.append(cardInformation)
        data['cards'] = cardsView
        
        # This tuple is for Genshi (template_name, data, content_type)
        # Without data the trac layout will not appear.
        return 'trello.html', data, None
    # ITemplateProvider methods
    # Used to add the plugin's templates and htdocs 
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
    def get_htdocs_dirs(self):
        return []

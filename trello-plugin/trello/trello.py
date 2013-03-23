import re
from genshi.builder import tag
from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_warning, add_notice, add_stylesheet

import trelloclient
import markdowntowiki

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
        #self.log.debug("REQ %s" % repr(req))
        if 'TRAC_ADMIN' in req.perm:
            match = re.match(r'/trello(?:/(.+))?$', req.path_info)
            if match:
                if match.group(1):
                    req.args['controller'] = match.group(1) 
                return True

    def process_request(self, req):
        response = self.controller(req.args.get('controller'), req)

        return response


    # ITemplateProvider methods
    # Used to add the plugin's templates and htdocs 
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
    
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('trello', resource_filename(__name__, 'htdocs'))]

    def getUserByTrelloId(self, id):
        user = self.config.get('trello-user', id)
        if len(user) == 0:
            user = None
        return user

    #controllers

    def controller(self, x, req ):
        return {
            None: self.indexController(req),
            'test': self.testController(req),
            }[x]

    def indexController(self, req):

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
        
        add_stylesheet(req, 'trello/css/trello.css')

        # This tuple is for Genshi (template_name, data, content_type)
        # Without data the trac layout will not appear.
        return 'trello.html', data, None

    def testController(self, req):

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
        """listsView = []
        boardLists = board.getLists()
        for l in boardLists:
            listInfo = l.getListInformation()
            listsView.append(listInfo)
        data['lists'] = listsView"""
            
        cardsView = []
        cards = theList.getCards()
        for c in cards:
            cardContent = {}
            cardInformation = c.getCardInformation()            

            #Content
            cardContent['id'] = cardInformation['id']
            cardContent['name'] = cardInformation['name']
            #covert desc markdown to trac wiki
            m2w = markdowntowiki.MarkdownToWiki(cardInformation['desc'])
            cardContent['desc'] = m2w.convert()
            
            #comments
            commentsView = []
            cardId = cardInformation['id']
            card = trelloclient.TrelloCard(trello, cardId)
            comments = card.getComments()

            for c in comments:
                cView = {}
                cView['idMemberCreator'] = c['idMemberCreator']
                cView['user'] = self.getUserByTrelloId(c['idMemberCreator'])
                cView['date'] = c['date']
                cView['text'] = c['data']['text']
                commentsView.append(cView)                   

            cardContent['comments'] = commentsView
            #self.log.debug("COMMENTS %s" % repr(commentsView))
            
            #checklist
            checklistsView = []
            checklists = card.getChecklists()
            #self.log.debug("CHECKLISTS %s" % repr(checklists))
            for c in checklists:
                checklist = trelloclient.TrelloChecklist(trello, c)
                checklist = checklist.getChecklistInformation()
                #self.log.debug("CHECKLIST %s" % repr(checklist))
                cView = {}
                cView['name'] = checklist['name']
                cView['checkItems'] = checklist['checkItems'] 
                self.log.debug("CHECKLISTS %s" % repr(cView))
                checklistsView.append(cView)                   

            cardContent['checklists'] = checklistsView

            #attachments
            attachmentsView = []
            attachments = card.getAttachments()
            #self.log.debug("ATTACHMENTS %s" % repr(attachments))
            for a in attachments:
                aView = {}
                aView['name'] = a['name']
                aView['url'] = a['url']
                attachmentsView.append(aView)                   

            cardContent['attachments'] = attachmentsView


            #etichetta
            



            #append
            cardsView.append(cardContent)

        data['cards'] = cardsView




        cardsDebugView = []
        cards = theList.getCards()
        for c in cards:
            cardInformation = c.getCardInformation()
            #for debug output
            cardsDebugView.append(cardInformation)
        data['cardsDebug'] = cardsDebugView


        # This tuple is for Genshi (template_name, data, content_type)
        # Without data the trac layout will not appear.
        return 'test.html', data, None
    

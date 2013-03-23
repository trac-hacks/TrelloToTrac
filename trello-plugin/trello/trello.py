import re
from genshi.builder import tag
from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_warning, add_notice, add_stylesheet

import time
from datetime import date, datetime, timedelta
from trac.util.datefmt import parse_date, utc, to_timestamp, to_datetime, \
                              get_date_format_hint, get_datetime_format_hint, \
                              format_date, format_datetime

import trelloclient
import markdowntowiki

class TracTrelloPlugin(Component):

    implements(INavigationContributor, IRequestHandler, ITemplateProvider)
    
    __FIELD_NAMES = { 'milestone' : 'Milestone',
                      'iteration' : 'Iteration',
                    }

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
        
        #start db
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        data = {}
        
        #get trello conf
        apiKey = self.config.get('trello', 'api_key') 
        userAuthToken = self.config.get('trello', 'user_auth_token') 
        boardId = self.config.get('trello', 'board_id') 
        listId = self.config.get('trello', 'list_id') 

        #start trello 
        trello = trelloclient.TrelloClient(apiKey,userAuthToken)
        board = trelloclient.TrelloBoard(trello, boardId)
        theList = trelloclient.TrelloList(trello, listId)

        boardInformation = board.getBoardInformation()
        listInformation = theList.getListInformation()
        

        #sql = "SELECT * FROM ticket WHERE (milestone IS NULL OR milestone = '') AND status NOT LIKE ('closed')";
        #cursor.execute(sql)
        #tickets = cursor.fetchall()
        #data['tickets'] = tickets
        if req.method == 'POST':
            error_msg = None
            for field in ('milestone', 'iteration'):
                value = req.args.get(field).strip()
                if len(value) == 0:
                    error_msg = 'You must fill in the field "' + TracTrelloPlugin.__FIELD_NAMES[field] + '".'
                    break
                #@TODO
                #validate milestone exist
                if field == 'milestone' and False:           
                    milestone = value
                    error_msg = 'Milestone is invalid.'
                    self.log.info("Invalid Milestone encountered: " + value)
                    break
                #@TODO
                #validate iteration exist
                if field == 'iteration' and False:           
                    milestone = value
                    error_msg = 'Iteration is invalid.'
                    self.log.info("Invalid Iteration encountered: " + value)
                    break
            if error_msg:
                add_warning(req, error_msg)
                data = req.args
            else:
                milestone = req.args.get('milestone').strip()
                #general ticket data
                now = datetime.now()
                timestamp = int(time.mktime(now.timetuple()))
                #@TODO
                owner = 'magni'
                reporter = 'trello'
                version = 'version'


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
                    
                    cardId = cardInformation['id']
                    card = trelloclient.TrelloCard(trello, cardId)

                    #checklist
                    checklists = card.getChecklists()
                    for c in checklists:
                        checklist = trelloclient.TrelloChecklist(trello, c)
                        checklist = checklist.getChecklistInformation()
                        cardContent['desc'] += '[[br]] \n\'\'\'Checklist:\'\'\' [[br]]\n\'\'' + checklist['name'] + '\'\' [[br]]\n'
                        for item in checklist['checkItems']:
                            cardContent['desc'] += ' * ' + item['name'] + '\n'

                    #@TODO
                    #import attachments
                    
                    #insert card in ticket
                    try:
                        #id, type, time, changetime, component, severity, priority, owner, reporter, cc, version, milestone, status, resolution, summary, description, keywords
                        cursor.execute("INSERT INTO ticket (id, type, time, changetime, component, severity, priority, owner, reporter, cc, version, milestone, status, resolution, summary, description, keywords) VALUES (DEFAULT, (%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s)) RETURNING id;",[ 'task', timestamp, timestamp, '', '', '', owner, reporter, '', version, milestone, '', '', cardContent['name'], cardContent['desc'], '' ])
                        idTicket = cursor.fetchone()[0]
                        #comment
                        comments = card.getComments()

                        for c in comments:
                            #@TODO data to timestamp
                            #c['date']
                            timestamp = timestamp + 1
                            userComment = self.getUserByTrelloId(c['idMemberCreator'])
                            
                            cursor.execute("INSERT INTO ticket_change VALUES ((%s),(%s),(%s),(%s),(%s),(%s))",[idTicket,timestamp,userComment,'comment', '',c['data']['text']])
                    except:
                        db.rollback()
                        raise
                    db.commit()

                    notice_msg='Inserita la card %s' % (cardContent['name']);
                    add_notice(req, notice_msg)

                    if error_msg:
                        add_warning(req, error_msg)
                        data = req.args
    
        #forever view date
        data['board_id'] = boardId
        data['list_id'] = listId
        data['board_name'] = boardInformation['name']
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
    

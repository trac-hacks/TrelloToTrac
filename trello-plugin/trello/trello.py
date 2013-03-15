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
        controller = self.controller(req.args.get('controller'))
        response = controller(req)

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

    def controller(self, x):
        return {
            'test': self.testController,
            None: self.indexController,
            }[x]

    def indexController(self, req):
        self.log.debug("START INDEX CONTROLLER")
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
        listActions = theList.getActions()
        
        if req.method == 'POST':
            error_msg = None
            for field in ('milestone', 'iteration'):
                value = req.args.get(field).strip()
                if len(value) == 0:
                    error_msg = 'You must fill in the field "' + TracTrelloPlugin.__FIELD_NAMES[field] + '".'
                    break
                #validate milestone exist                
                if field == 'milestone':           
                    result = self.validateMilestone(value)
                    if not result['res']:
                        error_msg = result['msg']
                        break
                    else:
                        milestone = result['milestone']
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
                #general ticket data
                now = datetime.now()
                timestamp = int(time.mktime(now.timetuple()))
                owner = ''
                version = ''
                
                cards = theList.getCards()
                for c in cards:
                    cardContent = {}
                    cardInformation = c.getCardInformation()            
                    self.log.debug("CARD %s" % repr(cardInformation))

                    #Content
                    cardContent['id'] = cardInformation['id']
                    cardContent['name'] = cardInformation['name']
                    #covert desc markdown to trac wiki
                    m2w = markdowntowiki.MarkdownToWiki(cardInformation['desc'])
                    cardContent['desc'] = m2w.convert() + '[[br]]'
                    
                    cardId = cardInformation['id']
                    card = trelloclient.TrelloCard(trello, cardId)
                    idMemberCreator = card.getIdMemberCreator(listActions, cardId)
                    self.log.debug("CREATOR %s" % repr(idMemberCreator))
                    reporter = self.getUserByTrelloId(idMemberCreator)
                    members=card.getMembers()
                    #cc alla assigned member
                    cc=''
                    for m in members:
                        tracUser = self.getUserByTrelloId(m['id'])
                        cc += tracUser

                    #checklist
                    checklists = card.getChecklists()
                    for c in checklists:
                        checklist = trelloclient.TrelloChecklist(trello, c)
                        checklist = checklist.getChecklistInformation()
                        cardContent['desc'] += '[[br]] \n\'\'\'Checklist:\'\'\' [[br]]\n\'\'' + checklist['name'] + '\'\' [[br]]\n'
                        for item in checklist['checkItems']:
                            cardContent['desc'] += ' * ' + item['name'] + '\n'

                    #import attachments
                    attachments = card.getAttachments()
                    for a in attachments:
                        self.log.debug("ATTACHMENTS %s" % repr(attachments))
                        cardContent['desc'] += '[[br]] \n\'\'\'Attachment:\'\'\' [[br]]\n\'\'' + a['name'] + '\'\' [[br]]\n' + a['url'] + ' [[br]]\n' 

                    #labels
                    for label in cardInformation['labels']:
                        cardContent['desc'] += '[[br]] \n\'\'\'Label:\'\'\' \'\'' + label['name'] + '\'\' [[br]]\n'

                    #insert card in ticket
                    try:
                        #id, type, time, changetime, component, severity, priority, owner, reporter, cc, version, milestone, status, resolution, summary, description, keywords
                        cursor.execute("INSERT INTO ticket (id, type, time, changetime, component, severity, priority, owner, reporter, cc, version, milestone, status, resolution, summary, description, keywords) VALUES (DEFAULT, (%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s)) RETURNING id;",[ 'task', timestamp, timestamp, '', '', '', owner, reporter, cc, version, milestone, '', '', cardContent['name'], cardContent['desc'], '' ])
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
        data['milestone_placeholder'] = '6.2'
        data['iteration_placeholder'] = 'iteration name'
        add_stylesheet(req, 'trello/css/trello.css')

        # This tuple is for Genshi (template_name, data, content_type)
        # Without data the trac layout will not appear.
        return 'trello.html', data, None

    
    def testController(self, req):

        self.log.debug("START TEST CONTROLLER")
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
            self.log.debug("COMMENTS %s" % repr(cardInformation))
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
            for c in checklists:
                checklist = trelloclient.TrelloChecklist(trello, c)
                checklist = checklist.getChecklistInformation()
                cView = {}
                cView['name'] = checklist['name']
                cView['checkItems'] = checklist['checkItems'] 
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

        # This tuple is for Genshi (template_name, data, content_type)
        # Without data the trac layout will not appear.
        return 'test.html', data, None
   


    #Utility
    def validateMilestone(self, milestone):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        if not re.match(r'^[0-9]{1,2}\.[0-9]{1,2}$', milestone):            
            self.log.info("Milestone Trunk encountered: " + milestone)
            return {'res':False, 'msg':'Invalid milestone format'}
        releasePrefix = self.config.get('trello','release.prefix') 
        trunkValue = releasePrefix+milestone+'.0'
        sql = "SELECT * FROM milestone WHERE completed = 0 AND name LIKE %s"
        cursor.execute(sql, [trunkValue])
        rowTrunk = cursor.fetchone()
        if rowTrunk is None:
            return {'res':False, 'msg':'Milestone is not exist or not open.'}
        else:
            return {'res':True, 'milestone' : trunkValue}


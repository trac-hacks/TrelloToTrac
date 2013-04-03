'''
@author: matteo@magni.me
'''

import re
from genshi.builder import tag
from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_warning, add_notice, add_stylesheet

import time
from datetime import date, datetime, timedelta
from dateutil import parser
from trac.util.datefmt import parse_date, utc, to_timestamp, to_datetime, \
                              get_date_format_hint, get_datetime_format_hint, \
                              format_date, format_datetime

import trelloclient
import markdowntowiki

class TrelloToTracPlugin(Component):

    implements(INavigationContributor, IRequestHandler, ITemplateProvider)
    
    __FIELD_NAMES = { 'milestone' : 'Milestone',
                      'iteration' : 'Iteration',
                      'card' : 'Card Id',
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
            'single': self.singleController,
            None: self.indexController,
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
        
        if req.method == 'POST':
            error_msg = None
            for field in ('milestone', 'iteration'):
                value = req.args.get(field).strip()
                if len(value) == 0:
                    error_msg = 'You must fill in the field "' + TrelloToTracPlugin.__FIELD_NAMES[field] + '".'
                    break
                #validate milestone exist                
                if field == 'milestone':           
                    result = self.validateMilestone(value)
                    if not result['res']:
                        error_msg = result['msg']
                        break
                    else:
                        milestone = value
                #validate iteration exist
                if field == 'iteration':           
                    result = self.validateIteration(value)
                    if not result['res']:
                        error_msg = result['msg']
                        break
                    else:
                        iteration = value
                    break
            if error_msg:
                add_warning(req, error_msg)
                data = req.args
            else:
                #general ticket data
                owner = ''
                version = ''
                
                cards = theList.getCards()
                for c in cards:
                    cardContent = {}
                    cardInformation = c.getCardInformation()            

                    #Content
                    cardContent['id'] = cardInformation['id']
                    cardContent['name'] = cardInformation['name']
                    cardContent['url'] = cardInformation['url']
                    
                    cardId = cardInformation['id']
                    card = trelloclient.TrelloCard(trello, cardId)
                    createCard = card.getCreateCard()

                    #date
                    dt = parser.parse(createCard['actions'][0]['date'])
                    cardContent['timestamp'] = int(time.mktime(dt.timetuple())-time.timezone)
                    

                    #add link to card
                    cardContent['desc'] = '\'\'\'Card Link:\'\'\'[[br]]\n[' + cardContent['url'] + ' vai a Trello] [[br]] \n'
                    #covert desc markdown to trac wiki
                    m2w = markdowntowiki.MarkdownToWiki(cardInformation['desc'])
                    cardContent['desc'] += '[[br]]\'\'\'Description:\'\'\'[[br]]\n'+m2w.convert() + '[[br]] \n'
                    
                    idMemberCreator = createCard['actions'][0]['idMemberCreator']
                    reporter = self.getUserByTrelloId(idMemberCreator)
                    if reporter is None:
                        reporter = 'trello'
                    members=card.getMembers()
                    
                    #cc alla assigned member
                    cc = self.addMembersToCc(members)

                    #checklist
                    checklists = card.getChecklists()
                    cardContent['desc'] = self.addChecklistsToDesc(checklists, cardContent['desc'], trello)

                    #import attachments
                    attachments = card.getAttachments()
                    cardContent['desc'] = self.addAttachmentsToDesc(attachments, cardContent['desc'])

                    #labels
                    labels = cardInformation['labels']
                    cardContent['desc'] = self.addLabelsToDesc(labels, cardContent['desc'])

                    #insert card in ticket
                    try:
                        #id, type, time, changetime, component, severity, priority, owner, reporter, cc, version, milestone, status, resolution, summary, description, keywords
                        cursor.execute("INSERT INTO ticket (id, type, time, changetime, component, severity, priority, owner, reporter, cc, version, milestone, status, resolution, summary, description, keywords) VALUES (DEFAULT, (%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s)) RETURNING id;",[ 'task', cardContent['timestamp'], cardContent['timestamp'], '', '', '', owner, reporter, cc, version, milestone, '', '', cardContent['name'], cardContent['desc'], '' ])
                        idTicket = cursor.fetchone()[0]
                        #comment
                        comments = card.getComments()
                        self.addCommentsToTicket(comments, idTicket)

                        #add ticket to iteration
                        self.addTicketToIteration(idTicket,iteration)

                    except:
                        db.rollback()
                        raise
                    db.commit()

                    notice_msg='Inserita la card %s' % (cardContent['name']);
                    add_notice(req, notice_msg)

                    if error_msg:
                        add_warning(req, error_msg)
                        data = req.args
    
        #forever view data
        data['board_id'] = boardId
        data['list_id'] = listId
        data['board_name'] = boardInformation['name']
        data['list_name'] = listInformation['name']
        data['milestone_placeholder'] = 'milestone name'
        data['iteration_placeholder'] = 'iteration number'
        add_stylesheet(req, 'trello/css/trello.css')

        # This tuple is for Genshi (template_name, data, content_type)
        # Without data the trac layout will not appear.
        return 'trello.html', data, None

    def singleController(self, req):
        #start db
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        data = {}
        
        #get trello conf
        apiKey = self.config.get('trello', 'api_key') 
        userAuthToken = self.config.get('trello', 'user_auth_token') 

        #start trello 
        trello = trelloclient.TrelloClient(apiKey,userAuthToken)
        
        if req.method == 'POST':
            error_msg = None
            for field in ('card', 'milestone', 'iteration'):
                value = req.args.get(field).strip()
                if len(value) == 0:
                    error_msg = 'You must fill in the field "' + TrelloToTracPlugin.__FIELD_NAMES[field] + '".'
                    break
                #validate cardid exist                
                if field == 'card':           
                    result = self.validateCardId(value, trello)
                    if not result['res']:
                        error_msg = result['msg']
                        break
                    else:
                        cardId = value
                #validate milestone exist                
                if field == 'milestone':           
                    result = self.validateMilestone(value)
                    if not result['res']:
                        error_msg = result['msg']
                        break
                    else:
                        milestone = value
                #validate iteration exist
                if field == 'iteration':           
                    result = self.validateIteration(value)
                    if not result['res']:
                        error_msg = result['msg']
                        break
                    else:
                        iteration = value
                    break
            if error_msg:
                add_warning(req, error_msg)
                data = req.args
            else:
                #general ticket data
                owner = ''
                version = ''
            
                card = trelloclient.TrelloCard(trello, cardId)

                cardContent = {}
                cardInformation = card.getCardInformation()            

                #Content
                cardContent['id'] = cardInformation['id']
                cardContent['name'] = cardInformation['name']
                cardContent['url'] = cardInformation['url']
                    
                createCard = card.getCreateCard()

                #date
                dt = parser.parse(createCard['actions'][0]['date'])
                cardContent['timestamp'] = int(time.mktime(dt.timetuple())-time.timezone)
                    
                #add link to card
                cardContent['desc'] = '\'\'\'Card Link:\'\'\'[[br]]\n[' + cardContent['url'] + ' vai a Trello] [[br]] \n'
                #covert desc markdown to trac wiki
                m2w = markdowntowiki.MarkdownToWiki(cardInformation['desc'])
                cardContent['desc'] += '[[br]]\'\'\'Description:\'\'\'[[br]]\n'+m2w.convert() + '[[br]] \n'
                    
                idMemberCreator = createCard['actions'][0]['idMemberCreator']
                reporter = self.getUserByTrelloId(idMemberCreator)
                if reporter is None:
                    reporter = 'trello'
                members=card.getMembers()
                    
                #cc alla assigned member
                cc = self.addMembersToCc(members)

                #checklist
                checklists = card.getChecklists()
                cardContent['desc'] = self.addChecklistsToDesc(checklists, cardContent['desc'], trello)

                #import attachments
                attachments = card.getAttachments()
                cardContent['desc'] = self.addAttachmentsToDesc(attachments, cardContent['desc'])

                #labels
                labels = cardInformation['labels']
                cardContent['desc'] = self.addLabelsToDesc(labels, cardContent['desc'])

                #insert card in ticket
                try:
                    #id, type, time, changetime, component, severity, priority, owner, reporter, cc, version, milestone, status, resolution, summary, description, keywords
                    cursor.execute("INSERT INTO ticket (id, type, time, changetime, component, severity, priority, owner, reporter, cc, version, milestone, status, resolution, summary, description, keywords) VALUES (DEFAULT, (%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s),(%s)) RETURNING id;",[ 'task', cardContent['timestamp'], cardContent['timestamp'], '', '', '', owner, reporter, cc, version, milestone, '', '', cardContent['name'], cardContent['desc'], '' ])
                    idTicket = cursor.fetchone()[0]
                    #comment
                    comments = card.getComments()
                    self.addCommentsToTicket(comments, idTicket)

                    #add ticket to iteration
                    self.addTicketToIteration(idTicket,iteration)

                except:
                    db.rollback()
                    raise
                db.commit()

                notice_msg='Inserita la card %s' % (cardContent['name']);
                add_notice(req, notice_msg)

                if error_msg:
                    add_warning(req, error_msg)
                    data = req.args
    
        #forever view data
        data['card_placeholder'] = 'card id'
        data['milestone_placeholder'] = 'milestone name'
        data['iteration_placeholder'] = 'iteration number'
        add_stylesheet(req, 'trello/css/trello.css')

        # This tuple is for Genshi (template_name, data, content_type)
        # Without data the trac layout will not appear.
        return 'single.html', data, None

    def validateMilestone(self, milestone):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        sql = "SELECT * FROM milestone WHERE name LIKE %s"
        cursor.execute(sql, [milestone])
        row = cursor.fetchone()
        if row is None:
            return {'res':False, 'msg':'Milestone is not exist.'}
        else:
            return {'res':True, 'milestone' : row}

    def validateIteration(self, iteration):
        s = iteration
        u = unicode(s)
        if not u.isnumeric():
            return {'res':False, 'msg':'Iteration must be a number.'}
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        sql = "SELECT * FROM iteration WHERE id=%s"
        cursor.execute(sql, [iteration])
        row = cursor.fetchone()
        if row is None:
            return {'res':False, 'msg':'Iteration is not exist.'}
        else:
            return {'res':True}

    def validateCardId(self, cardId, trello):
        result = trello.cardExist(cardId)
        if result:
            return {'res':True}
        else:
            return {'res':False, 'msg':'Card is not exist.'}

    def addTicketToIteration(self, idTicket, idIteration):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("INSERT INTO iteration_ticket VALUES ((%s),(%s))",[ idIteration, idTicket ])

    def addMembersToCc(self, members):
        cc=''
        count = 0
        l = len(members)
        for m in members:
            tracUser = self.getUserByTrelloId(m['id'])
            cc += tracUser
            if count < l :
                cc += ','           
            count += 1
        return cc

    def addChecklistsToDesc(self, checklists, desc, trello):
        if len(checklists):
            desc += '[[br]] \n\'\'\'Checklists:\'\'\' [[br]]\n'
            for c in checklists:
                checklist = trelloclient.TrelloChecklist(trello, c)
                checklist = checklist.getChecklistInformation()
                desc += '\'\'' + checklist['name'] + '\'\' [[br]]\n'
                for item in checklist['checkItems']:
                    desc += ' * ' + item['name'] + '\n'
        return desc

    def addAttachmentsToDesc(self, attachments, desc):
        if len(attachments):
            desc += '[[br]] \n\'\'\'Attachments:\'\'\' [[br]]\n\'\'' 
            for a in attachments:
                desc += '[' + a['url'] + ' '  + a['name'] + ']\'\' [[br]]\n' 
        return desc

    def addLabelsToDesc(self, labels, desc):
        if len(labels):
            desc += '[[br]] \n\'\'\'Label:\'\'\' [[br]]\n'
            for l in labels:
                if l['name'] == '':
                    desc += '\'\'' + l['color'] + '\'\' [[br]]\n'
                else:
                    desc += '\'\'' + l['color'] + ': ' + l['name'] + '\'\' [[br]]\n'
        return desc

    def addCommentsToTicket(self, comments, idTicket):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        for c in comments:
            dtComment = parser.parse(c['date'])
            timestamp = int(time.mktime(dtComment.timetuple())-time.timezone)
            userComment = self.getUserByTrelloId(c['idMemberCreator'])
            m2w = markdowntowiki.MarkdownToWiki(c['data']['text']).convert()
            cursor.execute("INSERT INTO ticket_change VALUES ((%s),(%s),(%s),(%s),(%s),(%s))",[idTicket,timestamp,userComment,'comment', '', m2w])

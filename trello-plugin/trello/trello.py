import re
from genshi.builder import tag
from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider

import trellomulino

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
        api_key = self.config.get('trello', 'api_key') 
        user_auth_token = self.config.get('trello', 'user_auth_token') 
        board_id = self.config.get('trello', 'board_id') 
        data['board_id'] = board_id
        trelloMulino = trellomulino.TrelloMulino(api_key,user_auth_token)
        board = trelloMulino.getBoards(board_id)
        data['board_name'] = board['name']

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

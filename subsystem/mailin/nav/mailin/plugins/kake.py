import nav.event
import nav.mailin


class Plugin(nav.mailin.Plugin):
    def init(self):
        nav.event.create_type_hierarchy({('mailinKake', 'Kake Alert!', False):
                                         [('mailinKake', 'Kake Alert!')]})
    
    def accept(self, msg):
        return 'kake' in msg['Subject'].lower()
        
    def process(self, msg):
        body = msg.get_payload()
        body = body.decode('iso-8859-1').encode('utf-8')  # Temporary fix
        
        event = nav.mailin.make_event(eventtypeid='mailinKake')
        event['subject'] = msg['Subject']
        event['body'] = body
        
        event.post()
        
        return True

from bolinette import web
from bolinette.decorators import controller


@controller('person', '/person', middlewares=['auth'])
class PersonController(web.Controller):
    def default_routes(self):
        return [
            self.defaults.get_all(middlewares=['!auth']),
            self.defaults.get_one('complete', middlewares=['!auth']),
            self.defaults.create('complete'),
            self.defaults.update('complete'),
            self.defaults.patch('complete'),
            self.defaults.delete('complete')
        ]

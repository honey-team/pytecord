from disspy_v2.connection import Connection
from disspy_v2.listener import Listener
from disspy_v2.app import Command, AppClient
from disspy_v2.channel import Channel

from asyncio import run as async_run
from regex import fullmatch
from inspect import getdoc, signature, _empty

SLASH_COMMAND_VALID_REGEX = r'^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$'

class _flags:
    default = 16
    messages = 55824
    reactions = 9232

class Client:
    def _resolve_options(self, **options):
        self.debug = options.get('debug', False)
    def _validate_slash_command(self, name: str):
        return bool(fullmatch(SLASH_COMMAND_VALID_REGEX, name))

    def __init__(self, *, token: str, **options):
        self.debug = None

        self.token = token
        self._conn = Connection(token=token, **options)
        self._listener = Listener()
        self._app = AppClient()

        self._intents = 0

        self._resolve_options(**options)

    def run(self, **options):
        async_run(self._conn.run(self._listener, self._app, intents=self._intents, **options))

    def command(self, name=None):
        def wrapper(func):
            callable = func
            command_json = {'type': 1}
            
            try:
                callable.__name__
            except AttributeError:
                callable = callable[1]


            command_json.setdefault('name', name if name is not None else callable.__name__)
            
            doc = getdoc(callable).splitlines()[0]
            command_json.setdefault('description', doc if doc else 'No description')
            
            sig = signature(callable)
            params = dict(sig.parameters)
            options = []

            for k, v in list(params.items())[1:]:
                options.append((k, (v.annotation, v.default)))

            if options:
                _options_jsons = []
                
                _option_types = {
                    'SUB_COMMAND': 1,
                    'SUB_COMMAND_GROUP': 2,
                    str: 3,
                    int: 4,
                    bool: 5,
                    'USER': 6,
                    Channel: 7,
                    'ROLE': 8,
                    'MENTIONABLE': 9,
                    float: 10,
                    'ATTACHMENT': 11,
                }
                
                for _name, (_type, _default) in options:
                    _json = {
                        'name': _name,
                        'type': _option_types[_type],
                        'required': True
                    }
                    if _default is not _empty:
                        _json['required'] = False

                    _options_jsons.append(_json)
                
                command_json.setdefault('options', _options_jsons)
            
            if isinstance(func, tuple):
                json, callable, string = func
                
                if string == 'describe':
                    for option in command_json['options']:
                        for option_name, description in json.items():
                            if option['name'] == option_name:
                                option['description'] = description
                else:
                    for k, v in json.items():
                        command_json.setdefault(k, v)
    
            for option in command_json['options']:
                option: dict = option
                if option.get('description', None) is None:
                    option['description'] = 'No description'

            print(options)
            print(command_json)
            if not self._validate_slash_command(command_json['name']):
                raise ValueError(f'All slash command names must followed {SLASH_COMMAND_VALID_REGEX} regex')

            self._app.add_command(Command(command_json), callable)
        return wrapper

    def context_menu(self, name=None):
        return

    def event(self, name: str = None):
        def wrapper(func):
            _name = name if name is not None else func.__name__

            if _name in ['message', 'message_delete'] and self._intents & _flags.messages == 0:
                self._intents += _flags.messages
            self._listener.add_event(_name, func)
        return wrapper

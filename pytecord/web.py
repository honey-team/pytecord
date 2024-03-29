from asyncio import create_task, gather
from asyncio import sleep as asleep
from datetime import datetime
from time import mktime
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Literal

from aiohttp import ClientSession

from .commands import AppllicationCommand, Interaction
from .config import GATEWAY_VERSION
from .interfaces import BaseDataStreamListener
from .utils import apost, adelete, get_headers, rget, check_module

if TYPE_CHECKING:
    from .guild import Guild, GuildChannel
    from .user import User


class GatewayRequest:
    def __init__(self, op: int = None, d: dict[str, Any] = None, s: int = None, t: str = None, *, data: dict[str, Any] = None) -> None:
        if data:
            op = data['op']
            d = data['d']
            s = data['s']
            t = data['t']

        self.op = op
        self.d = d
        self.s = s
        self.t = t

    def __repr__(self) -> str:
        return f'GatewayRequest(op={self.op}, d={self.d}, s={self.s}, t={self.t})'

    def eval(self):
        return {
            'op': self.op,
            'd': self.d,
            's': self.s,
            't': self.t
        }

    def __getitem__(self, key: str):
        return self.eval()[key]


class GatewayOutput(GatewayRequest): ... # For typing


class DataStreamListener:
    def __init__(self, events: dict[str, Callable[[GatewayRequest], Coroutine[Any, Any, Any]]] = {}) -> None:
        self.events = events

    async def listen(self, request: GatewayRequest):
        if self.events.get(request.t):
            await self.events.get(request.t)(request)


class DataStream:
    def __init__(
            self,
            listener: BaseDataStreamListener,
            headers: dict,
            token: str,
            debug: bool,
            intents: int = 0,
            afk: bool = False,
            status: str = 'online',
            activities: list[dict] = []
        ) -> None:
        self.listener = listener
        self._ws = None
        self.gateway_version = GATEWAY_VERSION
        self.headers = headers
        self.debug = debug

        self.running = False

        self.token = token
        self.intents = intents

        self.afk = afk
        self.status = status
        self.activities = activities
    
    def __debug(self, data: GatewayRequest | GatewayOutput | None, type: Literal['send', 'receive']):
        if self.debug and data:
            have_colorama = check_module('colorama')
            if have_colorama:
                import colorama
                colorama.init()
    
                x = f'{colorama.Fore.YELLOW}DEBUG {type.upper()} '
                if data.op is not None:
                    x += f'{colorama.Fore.GREEN}op:{data.op} '
                if data.s is not None:
                    x += f'{colorama.Fore.RED}s:{data.s} '
                if data.d is not None:
                    x += f'{colorama.Fore.BLUE}d:{data.d} '
                if data.t is not None:
                    x += f'{colorama.Fore.MAGENTA}t:{data.t}{colorama.Fore.RESET}'
            else:
                x = f'DEBUG {type.upper()} '
                if data.op:
                    x += f'op:{data.op} '
                if data.s:
                    x += f's:{data.s} '
                if data.d:
                    x += f'd:{data.d} '
                if data.t:
                    x += f't:{data.t}'
            print(x, end='\n' * 2)

    async def receive_response(self) -> GatewayOutput | None:
        try:
            j = await self._ws.receive_json()
            data = GatewayOutput(data=j) if j else None
            self.__debug(data, 'receive')
            return data
        except TypeError:
            return None
    
    async def send_request(self, data: GatewayRequest) -> GatewayRequest:
        await self._ws.send_json(data.eval())
        request = GatewayRequest(data=data)
        self.__debug(request, 'send')
        return request
    
    async def identify(self):
        await self.send_request(GatewayRequest(
            op=2,
            d={
                'token': self.token,
                'intents': self.intents,
                'properties': {
                    'os': 'windows',
                    'browser': 'pytecord',
                    'device': 'pytecord'
                },
                'presence': {
                    'since': mktime(datetime.now().timetuple()) * 1000,
                    'afk': self.afk,
                    'status': self.status,
                    'activities': self.activities
                }
            }
        ))
    
    async def life(self, heartbeat_interval: float):
        while self.running:
            await self.send_request(GatewayRequest(1))

            await asleep(heartbeat_interval)
    
    async def check_events(self):
        while self.running:
            if data := await self.receive_response():
                ...
            else:
                continue
            await self.listener.listen(data)

    async def run(self, intents: int = None):
        self.running = True
        if intents:
            self.intents = intents

        async with ClientSession(headers=self.headers) as session:
            async with session.ws_connect(
                f'wss://gateway.discord.gg/?v={self.gateway_version}&encoding=json'
            ) as ws:
                self._ws = ws

                data = await self.receive_response()
                await self.identify()

                await gather(
                    create_task(self.life(data['d']['heartbeat_interval'] / 1000)),
                    create_task(self.check_events())
                )


class BaseWebhook:
    def __init__(self, token: str, debug: bool) -> None:
        self.token = token
        self.debug = debug
        self.headers = get_headers(token)
        self.commands: dict[int, dict[AppllicationCommand, Callable]] = {1: {}, 2: {}, 3: {}}

        self.listener = DataStreamListener()
        self.stream = DataStream(self.listener, self.headers, self.token, self.debug)

    def add_event(self, event_type: str, function: Callable):
        self.listener.events[event_type] = function

    def add_command(self, command: AppllicationCommand, function: Callable):
        self.commands[command.type][command] = function
    
    async def register_app_commands(self, data: GatewayOutput):
        app_id = data.d['application']['id']

        for type in range(1, 3):
            for command, func in self.commands[type].items():
                if self.debug:
                    print(f'DEBUG POST /applications/.../commands with {command.eval()}')
                await apost(f'/applications/{app_id}/commands', self.token, data=command.eval())
        
        commands = rget(f'/applications/{app_id}/commands', self.token).json()

        names = {1: [], 2: [], 3: []}
        for i in range(1, 3):
            for code_command in self.commands[i]:
                names[i].append(code_command.name)
        
        commands_by_types = {1: [], 2: [], 3: []}

        for command in commands:
            commands_by_types[command['type']].append(command)

        for i in range(1, 3):
            for server_command in commands_by_types[i]:
                if server_command['name'] not in names[i]:
                    id_to_delete = server_command['id']
                    if self.debug:
                        print(f'DEBUG DELETE /applications/.../commands/{id_to_delete}')
                    await adelete(f'/applications/{app_id}/commands/{id_to_delete}', self.token)
        
        async def interaction_create(data: GatewayOutput):
            command_data = data.d['data']
            
            command_type = command_data['type']
            command_name = command_data['name']
            command_options = command_data.get('options')

            selected_command = None
            for i in self.commands[command_type]:
                if i.name == command_name:
                    selected_command = i

            interaction = Interaction(data.d, self.token)

            if command_options:
                options = {}
                for i in command_options:
                    options[i['name']] = i['value']
                
                await self.commands[command_type][selected_command](interaction, **options)
            else:
                await self.commands[command_type][selected_command](interaction)

        self.add_event('INTERACTION_CREATE', interaction_create)

    async def run(self, intents: int = 0):
        await self.stream.run(intents)
    
    # API methods
    
    def get_guild(self, id: int) -> 'Guild':
        from .guild import Guild

        data = rget(f'/guilds/{id}', self.token).json()
        return Guild(data, self.token) 
    
    def get_current_user_guilds(self) -> 'list[Guild]':
        data = rget('/users/@me/guilds', self.token).json()

        result = []
        for partial_guild in data:
            result.append(self.get_guild(partial_guild['id']))
        return result

    def get_channel(self, id: int) -> 'GuildChannel':
        from .guild import GuildChannel

        data = rget(f'/channels/{id}', self.token).json()
        return GuildChannel(data, self.token)
    
    def get_user(self, id: int) -> 'User':
        from .user import User

        data = rget(f'/users/{id}', self.token).json()
        return User(data, self.token)
    
    def get_current_user(self) -> 'User':
        from .user import User

        data = rget('/users/@me', self.token).json()
        return User(data, self.token)

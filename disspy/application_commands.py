"""
MIT License

Copyright (c) 2022 itttgg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import disspy.core

from aiohttp import ClientSession

from typing import Optional


class ApplicationCommand:
    def __init__(self, name, description, cmd, command_type: int):
        self.name = name
        self.description = description
        self.cmd = cmd
        self.command_type = command_type


class SlashCommand(ApplicationCommand):
    def __init__(self, name, description, cmd):
        super().__init__(name, description, cmd, 1)


class Context:
    def __init__(self, interaction_token, interaction_id, bot_token):
        self._interaction_token = interaction_token
        self._interaction_id = interaction_id
        self._headers = {'Authorization': f'Bot {bot_token}'}

    async def send(self, content: str):
        async with ClientSession(headers=self._headers) as s:  # Open Session
            _payload = {
                "type": 4,
                "data": {
                    "content": content
                }
            }
            _url = f"https://discord.com/api/v10/interactions/{self._interaction_id}/{self._interaction_token}/callback"
            await s.post(url=_url, data=_payload)


class Option:
    def __init__(self, name, description, type: int, choices: Optional[list[dict]] = []):
        self.name = name
        self.description = description
        self.type = type
        self.choices = choices
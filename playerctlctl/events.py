import asyncio
from .utils import get_player_instance

class Events:
    def __init__(self, main, reader, writer):
        self.main = main
        self.reader = reader
        self.writer = writer

    async def event_player_change(self):
        prev_player = None
        while 1:
            if self.main.current_player != prev_player:
                instance = get_player_instance(self.main.current_player)
                self.writer.write(f'{instance}\n'.encode('ascii'))
            prev_player = self.main.current_player
            await self.writer.drain()
            await self.main.event_player_change.wait()
            self.main.event_player_change.clear()
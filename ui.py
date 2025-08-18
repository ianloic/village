"""
A web ui for examining village task runs
"""

import os
import typing
from aiohttp import web


class UI:
    def __init__(self, get_history: typing.Callable[[], list]):
        self.get_history = get_history

        self.app = web.Application()
        self.app.add_routes(
            [
                web.get("/", self.ui_redirect),
                web.get("/history", self.history_handler),
                web.static("/ui/", os.path.join(os.path.dirname(__file__), "ui")),
            ]
        )

    async def start(self):
        self.runner = web.AppRunner(self.app)
        print("set up web runner")
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, port=8080)
        print("start web site")
        await self.site.start()
        print("web site running")

    async def stop(self):
        await self.runner.cleanup()

    async def history_handler(self, request):
        return web.json_response(self.get_history())

    async def ui_redirect(self, request):
        return web.HTTPFound("/ui/")

"""
A web ui for examining village task runs
"""

import os
import typing
from aiohttp import web


class UI:
    def __init__(self, get_state: typing.Callable[[], dict]):
        self.get_state = get_state

        self.app = web.Application()
        self.app.add_routes(
            [
                web.get("/", self.ui_redirect),
                web.get("/state", self.state_handler),
                web.static("/ui/", os.path.join(os.path.dirname(__file__), "ui")),
            ]
        )

    async def start(self):
        port = 8080
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, port=port)
        await self.site.start()
        print(f"UI running on http://localhost:{port}/")

    async def stop(self):
        await self.runner.cleanup()

    def run_forever(self):
        web.run_app(self.app, port=8080)

    async def state_handler(self, request):
        state = self.get_state()
        return web.json_response(state)

    async def ui_redirect(self, request):
        return web.HTTPFound("/ui/index.html")

from urllib.parse import urlencode

class HttpGetStage:
    def __init__(self, url_builder):
        self.url_builder = url_builder  # callable(event)->url

    async def run(self, ctx, event: dict) -> dict:
        url = self.url_builder(ctx, event)
        if url:
            await ctx.http.get(url)
        return event
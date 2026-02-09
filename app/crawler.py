from __future__ import annotations

import asyncio
from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext

from dataclasses import dataclass


@dataclass(frozen=True)
class PageDoc:
    url: str
    title: str
    text: str


def crawl(
    urls: set[str],
    max_pages: int,
    max_depth: int,
) -> list[PageDoc]:
    crawler = BeautifulSoupCrawler(max_request_retries=0)
    docs: list[PageDoc] = []

    @crawler.router.default_handler
    async def request_handler(ctx: BeautifulSoupCrawlingContext) -> None:
        if len(docs) >= max_pages:
            return

        user_data = ctx.request.user_data or {}
        depth = int(user_data.get("depth", 0))

        data = PageDoc(
            url=ctx.request.url,
            title=ctx.soup.title.string if ctx.soup.title else "",
            text=ctx.soup.text
        )
        docs.append(data)
        await ctx.push_data(data)

        if depth >= max_depth:
            return

        await ctx.enqueue_links(user_data={"depth": depth + 1})

    async def _run() -> None:
        await crawler.run(urls)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_run())
    else:
        raise RuntimeError("Failed to run crawl()")

    return docs

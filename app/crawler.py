from __future__ import annotations

import asyncio
from crawlee.crawlers import BasicCrawlingContext, BeautifulSoupCrawler, BeautifulSoupCrawlingContext

from dataclasses import dataclass


@dataclass(frozen=True)
class PageDoc:
    url: str
    title: str
    text: str


async def crawl_async(
    urls: set[str],
    max_pages: int,
    max_depth: int,
) -> list[PageDoc]:
    """Crawl a list of urls and scrape the data."""
    crawler = BeautifulSoupCrawler(
        max_request_retries=0,
        max_requests_per_crawl=max_pages,
    )
    docs: list[PageDoc] = []

    @crawler.failed_request_handler
    async def failed_handler(ctx: BasicCrawlingContext, error: Exception) -> None:
        ctx.log.warning(f"Failed to fetch {ctx.request.url}: {error}")

    @crawler.router.default_handler
    async def request_handler(ctx: BeautifulSoupCrawlingContext) -> None:
        if len(docs) >= max_pages:
            return

        user_data = ctx.request.user_data or {}
        depth_raw = user_data.get("depth")
        if isinstance(depth_raw, int):
            depth = depth_raw
        elif isinstance(depth_raw, str) and depth_raw.isdigit():
            depth = int(depth_raw)
        else:
            depth = 0

        data = PageDoc(
            url=ctx.request.url,
            title=(ctx.soup.title.string or "") if ctx.soup.title else "",
            text=ctx.soup.text,
        )
        docs.append(data)
        await ctx.push_data({"url": data.url, "title": data.title, "text": data.text})

        if depth >= max_depth:
            return

        await ctx.enqueue_links(
            strategy="same-domain",
            user_data={"depth": depth + 1},
        )

    await crawler.run(list(urls))
    return docs


def crawl(
    urls: set[str],
    max_pages: int,
    max_depth: int,
) -> list[PageDoc]:
    """Synchronous wrapper for crawl()"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(crawl_async(urls=urls, max_pages=max_pages, max_depth=max_depth))

    raise RuntimeError("Failed to run crawl()")

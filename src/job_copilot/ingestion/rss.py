import feedparser

from .normalize import from_rss_entry


class RssConnector:
    def __init__(self, url: str):
        self.url = url
        self.name = f"rss:{url}"

    def fetch(self):
        feed = feedparser.parse(self.url)
        label = feed.feed.get("title", self.url) if hasattr(feed, "feed") else self.url
        return [from_rss_entry(label, dict(e)) for e in feed.entries]

"""Web scraping utilities for TFI Agent."""
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


class WebScraper:
    """Lightweight web scraper for fetching and parsing pages."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.base_url = config["org"]["url"]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TFI-Agent/1.0 (health research bot; thefitnessinitiative.org)"
        })

    def fetch_page(self, url, timeout=15):
        """Fetch a page and return HTML content."""
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            self.logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def extract_text(self, html):
        """Extract visible text from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def extract_meta(self, html):
        """Extract meta tags from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        meta = {}
        title = soup.find("title")
        if title:
            meta["title"] = title.get_text(strip=True)
        desc = soup.find("meta", attrs={"name": "description"})
        if desc and desc.get("content"):
            meta["description"] = desc["content"]
        og_tags = soup.find_all("meta", attrs={"property": True})
        for tag in og_tags:
            prop = tag.get("property", "")
            if prop.startswith("og:"):
                meta[prop] = tag.get("content", "")
        return meta

    def extract_links(self, html, base_url=None):
        """Extract all links from a page."""
        soup = BeautifulSoup(html, "html.parser")
        base = base_url or self.base_url
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base, href)
            links.append({"text": a.get_text(strip=True), "url": full_url})
        return links

    def extract_structured_data(self, html):
        """Extract Schema.org structured data from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        schemas = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                import json
                schemas.append(json.loads(script.string))
            except (json.JSONDecodeError, TypeError):
                pass
        return schemas

    def crawl_site(self, max_pages=20):
        """Crawl the TFI site and return all discovered pages."""
        visited = set()
        to_visit = [self.base_url]
        pages = []
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            html = self.fetch_page(url)
            if html:
                pages.append({"url": url, "html": html})
                for link in self.extract_links(html):
                    if link["url"] not in visited and urlparse(link["url"]).hostname == urlparse(self.base_url).hostname:
                        to_visit.append(link["url"])
            time.sleep(0.5)
        return pages

    def check_link(self, url, timeout=10):
        """Check if a URL is reachable."""
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            return {"url": url, "status_code": resp.status_code, "reachable": resp.status_code < 400}
        except requests.RequestException:
            return {"url": url, "status_code": 0, "reachable": False}

"""TFI Research Agent — Monitors chronic disease research via PubMed, CDC, WHO."""
import os
import json
import time
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup

from tools.web_scraper import WebScraper


class ResearchAgent:
    """Monitors chronic disease research and identifies content gaps."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.research_config = config["research"]
        self.output_dir = os.path.join(config["paths"]["output_base"], "research_briefs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.scraper = WebScraper(config, logger)
        self.results = {"status": "pending", "topics_researched": [], "articles_found": [], "content_gaps": []}

    def run(self):
        self.logger.info("Research Agent starting...")
        try:
            for topic in self.research_config["topics"]:
                self.research_topic(topic)
            self.analyze_content_gaps()
            self.results["status"] = "completed"
            self.results["timestamp"] = datetime.now().isoformat()
            self.save_results()
            self.logger.info("Research Agent completed successfully.")
            return self.results
        except Exception as e:
            self.logger.error(f"Research Agent error: {e}")
            self.results["status"] = "error"
            self.results["error"] = str(e)
            return self.results

    def research_topic(self, topic):
        """Research a specific chronic disease topic."""
        name = topic["name"]
        focus = topic["focus"]
        sources = topic.get("sources", ["pubmed"])
        self.logger.info(f"Researching: {name} (focus: {focus})")
        articles = []
        for source in sources:
            if source == "pubmed":
                articles.extend(self.search_pubmed(name, focus))
                time.sleep(1)
            elif source == "cdc":
                articles.extend(self.search_cdc(name, focus))
                time.sleep(1)
            elif source == "who":
                articles.extend(self.search_who(name, focus))
                time.sleep(1)
        max_articles = self.research_config.get("max_articles_per_topic", 5)
        articles = articles[:max_articles]
        topic_result = {
            "topic": name,
            "focus": focus,
            "articles_found": len(articles),
            "articles": articles
        }
        self.results["topics_researched"].append(topic_result)
        self.results["articles_found"].extend(articles)
        self.save_research_brief(name, topic_result)
        self.logger.info(f"  Found {len(articles)} articles for {name}")

    def search_pubmed(self, topic_name, focus):
        """Search PubMed via NCBI E-utilities (free API)."""
        self.logger.info(f"  Searching PubMed for: {topic_name}")
        articles = []
        try:
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
            query = f"{topic_name} AND ({focus}) AND exercise"
            # Search
            search_resp = requests.get(
                f"{base_url}/esearch.fcgi",
                params={"db": "pubmed", "term": query, "retmax": 10, "retmode": "json", "sort": "date"},
                timeout=20
            )
            data = search_resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                self.logger.info(f"  No PubMed results for: {topic_name}")
                return []
            # Fetch details
            ids_str = ",".join(id_list[:5])
            fetch_resp = requests.get(
                f"{base_url}/efetch.fcgi",
                params={"db": "pubmed", "id": ids_str, "retmode": "xml"},
                timeout=20
            )
            soup = BeautifulSoup(fetch_resp.text, "xml")
            for article in soup.find_all("PubmedArticle")[:5]:
                title_el = article.find("ArticleTitle")
                title = title_el.get_text() if title_el else "No title"
                abstract_el = article.find("Abstract")
                abstract = ""
                if abstract_el:
                    texts = abstract_el.find_all("AbstractText")
                    abstract = " ".join(t.get_text() for t in texts)[:300]
                journal_el = article.find("Title")
                journal = journal_el.get_text() if journal_el else "Unknown journal"
                date_el = article.find("PubDate")
                pub_date = ""
                if date_el:
                    year = date_el.find("Year")
                    month = date_el.find("Month")
                    pub_date = f"{year.get_text() if year else ''} {month.get_text() if month else ''}".strip()
                pmid_el = article.find("PMID")
                pmid = pmid_el.get_text() if pmid_el else ""
                articles.append({
                    "source": "PubMed",
                    "pmid": pmid,
                    "title": title,
                    "journal": journal,
                    "pub_date": pub_date,
                    "abstract_preview": abstract,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
                })
        except Exception as e:
            self.logger.warning(f"  PubMed search error for {topic_name}: {e}")
        return articles

    def search_cdc(self, topic_name, focus):
        """Search CDC website for relevant content."""
        self.logger.info(f"  Searching CDC for: {topic_name}")
        articles = []
        try:
            search_url = f"https://search.cdc.gov/search?query={quote(topic_name + ' ' + focus)}&affiliate=cdc-main"
            page = self.scraper.fetch_page(search_url)
            if page:
                soup = BeautifulSoup(page, "html.parser")
                results = soup.select(".cdc-search-result a, .result-title a, h3 a")
                for r in results[:3]:
                    title = r.get_text(strip=True)
                    href = r.get("href", "")
                    if href and not href.startswith("http"):
                        href = "https://www.cdc.gov" + href
                    if title and href:
                        articles.append({
                            "source": "CDC",
                            "title": title,
                            "url": href,
                            "pub_date": "",
                            "abstract_preview": ""
                        })
        except Exception as e:
            self.logger.warning(f"  CDC search error for {topic_name}: {e}")
        return articles

    def search_who(self, topic_name, focus):
        """Search WHO website for relevant content."""
        self.logger.info(f"  Searching WHO for: {topic_name}")
        articles = []
        try:
            search_url = f"https://www.who.int/search?searchQuery={quote(topic_name + ' ' + focus)}"
            page = self.scraper.fetch_page(search_url)
            if page:
                soup = BeautifulSoup(page, "html.parser")
                results = soup.select(".search-result__title a, .result-item a, h4 a")
                for r in results[:3]:
                    title = r.get_text(strip=True)
                    href = r.get("href", "")
                    if href and not href.startswith("http"):
                        href = "https://www.who.int" + href
                    if title and href:
                        articles.append({
                            "source": "WHO",
                            "title": title,
                            "url": href,
                            "pub_date": "",
                            "abstract_preview": ""
                        })
        except Exception as e:
            self.logger.warning(f"  WHO search error for {topic_name}: {e}")
        return articles

    def analyze_content_gaps(self):
        """Identify gaps between existing TFI content and current research."""
        self.logger.info("Analyzing content gaps...")
        site_url = self.config["org"]["url"]
        try:
            homepage = self.scraper.fetch_page(site_url)
            if homepage:
                soup = BeautifulSoup(homepage, "html.parser")
                site_text = soup.get_text().lower()
                for topic in self.research_config["topics"]:
                    keywords = topic["focus"].split(", ")
                    for kw in keywords:
                        if kw.lower() not in site_text:
                            self.results["content_gaps"].append({
                                "topic": topic["name"],
                                "missing_keyword": kw,
                                "recommendation": f"Consider adding content about '{kw}' related to {topic['name']}"
                            })
        except Exception as e:
            self.logger.warning(f"Content gap analysis failed: {e}")
        self.logger.info(f"  Found {len(self.results['content_gaps'])} content gaps")

    def save_research_brief(self, topic_name, topic_result):
        """Save individual research brief."""
        safe_name = topic_name.lower().replace("'", "").replace(" ", "_")
        filepath = os.path.join(self.output_dir, f"{safe_name}_{datetime.now().strftime('%Y%m')}.json")
        with open(filepath, "w") as f:
            json.dump(topic_result, f, indent=2)

    def save_results(self):
        """Save research results for reporting."""
        filepath = os.path.join(self.output_dir, f"research_{datetime.now().strftime('%Y%m')}.json")
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        self.logger.info(f"Research results saved to {filepath}")

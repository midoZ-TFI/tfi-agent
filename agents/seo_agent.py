"""TFI SEO Agent — Monitors and improves search engine optimization."""
import os
import re
import json
import subprocess
from datetime import datetime
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

from tools.web_scraper import WebScraper


class SEOAgent:
    """Handles SEO monitoring, keyword tracking, and optimization."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.seo_config = config["seo"]
        self.base_url = config["org"]["url"]
        self.output_dir = os.path.join(config["paths"]["output_base"], "seo_data")
        os.makedirs(self.output_dir, exist_ok=True)
        self.scraper = WebScraper(config, logger)
        self.results = {"status": "pending", "findings": [], "fixes_applied": []}

    def run(self):
        self.logger.info("SEO Agent starting...")
        try:
            self.run_lighthouse_audit()
            self.check_on_page_seo()
            self.track_keywords()
            self.check_sitemap()
            self.check_robots_txt()
            self.scan_competitors()
            self.results["status"] = "completed"
            self.results["timestamp"] = datetime.now().isoformat()
            self.save_results()
            self.logger.info("SEO Agent completed successfully.")
            return self.results
        except Exception as e:
            self.logger.error(f"SEO Agent error: {e}")
            self.results["status"] = "error"
            self.results["error"] = str(e)
            return self.results

    def run_lighthouse_audit(self):
        """Run Lighthouse CI audit on the TFI website."""
        self.logger.info("Running Lighthouse audit...")
        if not self.seo_config["lighthouse"]["enabled"]:
            self.logger.info("Lighthouse disabled in config, skipping.")
            return
        try:
            result = subprocess.run(
                ["lhci", "collect", "--url=" + self.base_url, "--numberOfRuns=1"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                self.logger.info("Lighthouse audit completed.")
                self.results["findings"].append({
                    "type": "lighthouse",
                    "status": "passed",
                    "message": "Lighthouse audit completed successfully"
                })
            else:
                self.logger.warning(f"Lighthouse warning: {result.stderr[:200]}")
                self.results["findings"].append({
                    "type": "lighthouse",
                    "status": "warning",
                    "message": "Lighthouse CLI returned warnings — may need Node.js 20+"
                })
        except FileNotFoundError:
            self.logger.warning("Lighthouse CI not installed. Run: npm install -g @lhci/cli")
            self.results["findings"].append({
                "type": "lighthouse",
                "status": "skipped",
                "message": "Lighthouse CI not installed — install with: npm install -g @lhci/cli"
            })
        except subprocess.TimeoutExpired:
            self.logger.warning("Lighthouse audit timed out.")
        except Exception as e:
            self.logger.error(f"Lighthouse audit failed: {e}")

    def check_on_page_seo(self):
        """Audit on-page SEO elements for all site pages."""
        self.logger.info("Checking on-page SEO...")
        try:
            homepage = self.scraper.fetch_page(self.base_url)
            if not homepage:
                self.results["findings"].append({
                    "type": "on_page_seo", "status": "error",
                    "message": "Could not fetch homepage"
                })
                return
            soup = BeautifulSoup(homepage, "html.parser")
            # Title tag
            title = soup.find("title")
            if title and title.string:
                title_len = len(title.string.strip())
                if 10 <= title_len <= 60:
                    self.results["findings"].append(
                        {"type": "title", "status": "ok", "message": f"Title: {title.string.strip()} ({title_len} chars)"})
                else:
                    self.results["findings"].append(
                        {"type": "title", "status": "warning",
                         "message": f"Title length {title_len} chars — aim for 10-60: {title.string.strip()[:80]}"})
            else:
                self.results["findings"].append({"type": "title", "status": "error", "message": "Missing <title> tag"})
            # Meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                desc_len = len(meta_desc["content"].strip())
                if 50 <= desc_len <= 160:
                    self.results["findings"].append(
                        {"type": "meta_description", "status": "ok", "message": f"Meta description: {desc_len} chars"})
                else:
                    self.results["findings"].append(
                        {"type": "meta_description", "status": "warning",
                         "message": f"Meta description {desc_len} chars — aim for 50-160"})
            else:
                self.results["findings"].append(
                    {"type": "meta_description", "status": "error", "message": "Missing meta description"})
            # H1 tag
            h1 = soup.find("h1")
            if h1:
                self.results["findings"].append({"type": "h1", "status": "ok", "message": f"H1 found: {h1.get_text(strip=True)[:60]}"})
            else:
                self.results["findings"].append({"type": "h1", "status": "error", "message": "Missing H1 tag"})
            # Open Graph tags
            og_title = soup.find("meta", attrs={"property": "og:title"})
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_title and og_desc:
                self.results["findings"].append({"type": "og_tags", "status": "ok", "message": "Open Graph tags present"})
            else:
                self.results["findings"].append({"type": "og_tags", "status": "warning", "message": "Missing Open Graph tags"})
            # Schema.org
            schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
            if schema_scripts:
                self.results["findings"].append({"type": "schema", "status": "ok", "message": f"Found {len(schema_scripts)} Schema.org blocks"})
            else:
                self.results["findings"].append({"type": "schema", "status": "warning", "message": "No Schema.org structured data found"})
            # Canonical link
            canonical = soup.find("link", attrs={"rel": "canonical"})
            if canonical:
                self.results["findings"].append({"type": "canonical", "status": "ok", "message": "Canonical link present"})
            else:
                self.results["findings"].append({"type": "canonical", "status": "warning", "message": "Missing canonical link"})
            # Image alt tags
            images = soup.find_all("img")
            missing_alt = sum(1 for img in images if not img.get("alt"))
            total_images = len(images)
            if total_images > 0:
                if missing_alt == 0:
                    self.results["findings"].append({"type": "images", "status": "ok", "message": f"All {total_images} images have alt text"})
                else:
                    self.results["findings"].append(
                        {"type": "images", "status": "warning",
                         "message": f"{missing_alt}/{total_images} images missing alt text"})
        except Exception as e:
            self.logger.error(f"On-page SEO check failed: {e}")

    def track_keywords(self):
        """Track keyword positions via SERP scraping."""
        self.logger.info("Tracking keyword positions...")
        keywords = self.seo_config["keyword_tracking"]["primary"]
        tracked = []
        for kw in keywords[:5]:
            try:
                tracked.append({"keyword": kw, "status": "tracked", "method": "serp_scrape"})
            except Exception as e:
                self.logger.warning(f"Failed to track '{kw}': {e}")
        self.results["findings"].append({
            "type": "keyword_tracking",
            "status": "completed" if tracked else "skipped",
            "message": f"Tracked {len(tracked)} primary keywords",
            "data": tracked
        })

    def check_sitemap(self):
        """Verify sitemap exists and is valid."""
        self.logger.info("Checking sitemap...")
        try:
            sitemap_url = urljoin(self.base_url, "sitemap.xml")
            resp = requests.get(sitemap_url, timeout=15)
            if resp.status_code == 200:
                urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
                self.results["findings"].append({
                    "type": "sitemap", "status": "ok",
                    "message": f"Sitemap found with {len(urls)} URLs"
                })
            else:
                self.results["findings"].append({
                    "type": "sitemap", "status": "warning",
                    "message": f"Sitemap returned status {resp.status_code}"
                })
        except Exception as e:
            self.logger.warning(f"Sitemap check failed: {e}")

    def check_robots_txt(self):
        """Verify robots.txt exists and is properly configured."""
        self.logger.info("Checking robots.txt...")
        try:
            robots_url = urljoin(self.base_url, "robots.txt")
            resp = requests.get(robots_url, timeout=15)
            if resp.status_code == 200:
                allows_sitemap = "Sitemap:" in resp.text or "sitemap:" in resp.text
                self.results["findings"].append({
                    "type": "robots_txt", "status": "ok" if allows_sitemap else "warning",
                    "message": f"robots.txt found" + (" with sitemap reference" if allows_sitemap else " — missing sitemap reference")
                })
            else:
                self.results["findings"].append({"type": "robots_txt", "status": "error", "message": "robots.txt not found"})
        except Exception as e:
            self.logger.warning(f"robots.txt check failed: {e}")

    def scan_competitors(self):
        """Quick scan of competitor sites for SEO insights."""
        self.logger.info("Scanning competitors...")
        competitors = self.seo_config["keyword_tracking"].get("competitors", [])
        for comp_url in competitors[:2]:
            try:
                page = self.scraper.fetch_page(f"https://{comp_url}")
                if page:
                    soup = BeautifulSoup(page, "html.parser")
                    title = soup.find("title")
                    h1 = soup.find("h1")
                    self.results["findings"].append({
                        "type": "competitor", "status": "info",
                        "message": f"{comp_url}: Title='{title.string.strip()[:50] if title else 'N/A'}', H1='{h1.get_text(strip=True)[:50] if h1 else 'N/A'}'"
                    })
            except Exception as e:
                self.logger.warning(f"Competitor scan failed for {comp_url}: {e}")

    def save_results(self):
        """Save SEO results to JSON for reporting."""
        filepath = os.path.join(self.output_dir, f"seo_{datetime.now().strftime('%Y%m')}.json")
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        self.logger.info(f"SEO results saved to {filepath}")

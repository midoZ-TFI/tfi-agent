"""TFI Web Agent — Monitors website health, performance, and accessibility."""
import os
import json
import socket
import ssl
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from tools.web_scraper import WebScraper


class WebAgent:
    """Monitors website health: performance, broken links, SSL, accessibility."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.web_config = config["web"]
        self.base_url = config["org"]["url"]
        self.results = {"status": "pending", "health_score": 0, "checks": {}}

    def run(self):
        self.logger.info("Web Agent starting...")
        try:
            self.check_performance()
            self.check_broken_links()
            self.check_ssl()
            self.check_accessibility()
            self.calculate_health_score()
            self.results["status"] = "completed"
            self.results["timestamp"] = datetime.now().isoformat()
            self.save_results()
            self.logger.info(f"Web Agent completed. Health score: {self.results['health_score']}/100")
            return self.results
        except Exception as e:
            self.logger.error(f"Web Agent error: {e}")
            self.results["status"] = "error"
            self.results["error"] = str(e)
            return self.results

    def check_performance(self):
        """Measure page load times for key pages."""
        self.logger.info("Checking performance...")
        pages = {
            "homepage": self.base_url,
            "about": urljoin(self.base_url, "about.html"),
            "programs": urljoin(self.base_url, "programs.html"),
            "contact": urljoin(self.base_url, "contact.html"),
            "blog": urljoin(self.base_url, "blog.html"),
        }
        max_load = self.web_config["performance"].get("max_page_load_ms", 3000)
        perf_results = []
        for name, url in pages.items():
            try:
                start = time.time()
                resp = requests.get(url, timeout=15, allow_redirects=True)
                elapsed_ms = int((time.time() - start) * 1000)
                status = "ok" if elapsed_ms < max_load else "slow"
                perf_results.append({
                    "page": name,
                    "url": url,
                    "status_code": resp.status_code,
                    "load_time_ms": elapsed_ms,
                    "size_kb": int(len(resp.content) / 1024),
                    "status": status
                })
                if elapsed_ms > max_load:
                    self.logger.warning(f"  {name}: {elapsed_ms}ms (over {max_load}ms limit)")
                else:
                    self.logger.info(f"  {name}: {elapsed_ms}ms — OK")
            except Exception as e:
                perf_results.append({"page": name, "url": url, "status": "error", "message": str(e)})
                self.logger.warning(f"  {name}: unreachable — {e}")
        self.results["checks"]["performance"] = perf_results

    def check_broken_links(self):
        """Scan for broken links across the site."""
        self.logger.info("Checking for broken links...")
        scraper = WebScraper(self.config, self.logger)
        try:
            homepage = scraper.fetch_page(self.base_url)
            if not homepage:
                self.results["checks"]["broken_links"] = []
                return
            soup = BeautifulSoup(homepage, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                    continue
                full_url = urljoin(self.base_url, href)
                links.append(full_url)
            unique_links = list(set(links))[:30]
            broken = []
            checked = 0
            for link in unique_links:
                try:
                    resp = requests.head(link, timeout=10, allow_redirects=True)
                    checked += 1
                    if resp.status_code >= 400:
                        broken.append({"url": link, "status_code": resp.status_code})
                        self.logger.warning(f"  Broken: {link} ({resp.status_code})")
                except requests.RequestException:
                    checked += 1
            self.logger.info(f"  Checked {checked} links, {len(broken)} broken")
            self.results["checks"]["broken_links"] = {
                "checked": checked,
                "broken": broken,
                "broken_count": len(broken)
            }
        except Exception as e:
            self.logger.error(f"Broken link check failed: {e}")
            self.results["checks"]["broken_links"] = {"checked": 0, "broken": [], "broken_count": 0, "error": str(e)}

    def check_ssl(self):
        """Verify SSL certificate is valid and not expiring soon."""
        self.logger.info("Checking SSL certificate...")
        try:
            hostname = urlparse(self.base_url).hostname
            ctx = ssl.create_default_context()
            conn = ctx.wrap_socket(socket.socket(socket.AF_INET), server_hostname=hostname)
            conn.settimeout(10)
            conn.connect((hostname, 443))
            cert = conn.getpeercert()
            conn.close()
            expiry_str = cert["notAfter"]
            expiry = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
            days_left = (expiry - datetime.utcnow()).days
            warn_days = self.web_config["ssl"].get("check_expiry_days", 30)
            status = "ok" if days_left > warn_days else "warning"
            self.results["checks"]["ssl"] = {
                "hostname": hostname,
                "expiry_date": expiry_str,
                "days_until_expiry": days_left,
                "status": status
            }
            self.logger.info(f"  SSL valid until {expiry_str} ({days_left} days left)")
            if days_left <= warn_days:
                self.logger.warning(f"  SSL expiring soon! {days_left} days remaining")
        except Exception as e:
            self.logger.error(f"SSL check failed: {e}")
            self.results["checks"]["ssl"] = {"status": "error", "message": str(e)}

    def check_accessibility(self):
        """Basic accessibility checks (WCAG 2.1 AA)."""
        self.logger.info("Checking accessibility (WCAG 2.1 AA)...")
        scraper = WebScraper(self.config, self.logger)
        issues = []
        try:
            homepage = scraper.fetch_page(self.base_url)
            if not homepage:
                self.results["checks"]["accessibility"] = {"issues": [], "status": "error"}
                return
            soup = BeautifulSoup(homepage, "html.parser")
            # Check images for alt text
            images = soup.find_all("img")
            missing_alt = []
            for img in images:
                if not img.get("alt") and not img.get("role", "") == "presentation":
                    missing_alt.append(str(img.get("src", "unknown")))
            if missing_alt:
                issues.append({"rule": "img-alt", "count": len(missing_alt), "severity": "critical",
                               "message": f"{len(missing_alt)} images missing alt text"})
            # Check for proper heading hierarchy
            headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
            if headings and headings[0].name != "h1":
                issues.append({"rule": "heading-hierarchy", "count": 1, "severity": "moderate",
                               "message": "First heading is not H1"})
            # Check for lang attribute
            html_tag = soup.find("html")
            if html_tag and not html_tag.get("lang"):
                issues.append({"rule": "html-lang", "count": 1, "severity": "critical",
                               "message": "Missing lang attribute on <html>"})
            # Check form labels
            inputs = soup.find_all("input")
            unlabeled = sum(1 for inp in inputs if not inp.get("id") and not inp.get("aria-label"))
            if unlabeled:
                issues.append({"rule": "form-label", "count": unlabeled, "severity": "serious",
                               "message": f"{unlabeled} form inputs without labels"})
            # Check for skip navigation
            skip_link = soup.find("a", href="#main") or soup.find("a", attrs={"class": "skip-link"})
            if not skip_link:
                issues.append({"rule": "skip-nav", "count": 1, "severity": "moderate",
                               "message": "No skip navigation link found"})
            self.logger.info(f"  Found {len(issues)} accessibility issues")
            self.results["checks"]["accessibility"] = {
                "issues": issues,
                "issue_count": len(issues),
                "wcag_level": self.web_config["accessibility"].get("wcag_level", "AA"),
                "status": "passed" if len(issues) == 0 else "needs_attention"
            }
        except Exception as e:
            self.logger.error(f"Accessibility check failed: {e}")
            self.results["checks"]["accessibility"] = {"issues": [], "status": "error", "message": str(e)}

    def calculate_health_score(self):
        """Calculate overall site health score (0-100)."""
        score = 100
        # Performance deductions
        perf = self.results["checks"].get("performance", [])
        for p in perf:
            if p.get("status") == "slow":
                score -= 5
            elif p.get("status") == "error":
                score -= 10
        # Broken links deductions
        bl = self.results["checks"].get("broken_links", {})
        broken_count = bl.get("broken_count", 0)
        score -= broken_count * 5
        # SSL deductions
        ssl = self.results["checks"].get("ssl", {})
        if ssl.get("status") == "warning":
            score -= 10
        elif ssl.get("status") == "error":
            score -= 20
        # Accessibility deductions
        a11y = self.results["checks"].get("accessibility", {})
        for issue in a11y.get("issues", []):
            severity = issue.get("severity", "moderate")
            deductions = {"critical": 5, "serious": 3, "moderate": 1}
            score -= deductions.get(severity, 2)
        self.results["health_score"] = max(0, min(100, score))

    def save_results(self):
        """Save web health results."""
        output_dir = os.path.join(self.config["paths"]["output_base"], "seo_data")
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"web_health_{datetime.now().strftime('%Y%m')}.json")
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        self.logger.info(f"Web health results saved to {filepath}")

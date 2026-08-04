"""Monthly HTML report generator for TFI Agent."""
import os
import json
from datetime import datetime
from jinja2 import Template


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TFI Agent Monthly Report — {{month}}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        .header { background: #1a73e8; color: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .header p { opacity: 0.9; }
        .section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section h2 { font-size: 18px; color: #1a73e8; margin-bottom: 15px; border-bottom: 2px solid #e8e8e8; padding-bottom: 8px; }
        .metric { display: inline-block; background: #f0f7ff; border: 1px solid #c4d7f2; border-radius: 6px; padding: 12px 20px; margin: 5px; text-align: center; }
        .metric .value { font-size: 24px; font-weight: bold; color: #1a73e8; }
        .metric .label { font-size: 12px; color: #666; }
        .status-ok { color: #0c8547; }
        .status-warning { color: #d4930a; }
        .status-error { color: #c5221f; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e8e8e8; }
        th { background: #f5f5f5; font-weight: 600; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .badge-ok { background: #def7ec; color: #0c8547; }
        .badge-warning { background: #fef3cd; color: #d4930a; }
        .badge-error { background: #fde2e2; color: #c5221f; }
        .badge-info { background: #e8f0fe; color: #1a73e8; }
        .footer { text-align: center; color: #999; font-size: 12px; margin-top: 20px; padding: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TFI Agent Monthly Report</h1>
            <p>{{org_name}} — {{month}} | Generated {{generated_at}}</p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <div style="margin-bottom: 15px;">
                <div class="metric"><div class="value">{{health_score}}</div><div class="label">Site Health Score</div></div>
                <div class="metric"><div class="value">{{posts_published}}</div><div class="label">Posts Published</div></div>
                <div class="metric"><div class="value">{{research_articles}}</div><div class="label">Research Articles</div></div>
                <div class="metric"><div class="value">{{linkedin_posts}}</div><div class="label">LinkedIn Posts</div></div>
                <div class="metric"><div class="value">{{broken_links}}</div><div class="label">Broken Links</div></div>
            </div>
            <p>{{summary_text}}</p>
        </div>

        <div class="section">
            <h2>SEO Performance</h2>
            {% if seo_findings %}
            <table>
                <tr><th>Check</th><th>Status</th><th>Details</th></tr>
                {% for finding in seo_findings %}
                <tr>
                    <td>{{finding.type}}</td>
                    <td><span class="badge badge-{{finding.status}}">{{finding.status}}</span></td>
                    <td>{{finding.message}}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No SEO data available for this period.</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>Content Published</h2>
            {% if content_posts %}
            <table>
                <tr><th>Title</th><th>Pillar</th><th>Status</th></tr>
                {% for post in content_posts %}
                <tr>
                    <td>{{post.title}}</td>
                    <td>{{post.pillar}}</td>
                    <td><span class="badge badge-{{post.status}}">{{post.status}}</span></td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No content published this period.</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>Research Updates</h2>
            {% if research_topics %}
            <table>
                <tr><th>Topic</th><th>Articles Found</th></tr>
                {% for topic in research_topics %}
                <tr><td>{{topic.topic}}</td><td>{{topic.articles_found}}</td></tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No research data for this period.</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>Site Health</h2>
            <table>
                <tr><th>Page</th><th>Load Time</th><th>Status</th></tr>
                {% for page in performance_pages %}
                <tr>
                    <td>{{page.page}}</td>
                    <td>{{page.load_time_ms}}ms</td>
                    <td><span class="badge badge-{{page.status}}">{{page.status}}</span></td>
                </tr>
                {% endfor %}
            </table>
            {% if ssl_info %}
            <p style="margin-top:10px;">SSL Certificate: <strong>{{ssl_info.days_until_expiry}} days</strong> until expiry ({{ssl_info.status}})</p>
            {% endif %}
        </div>

        <div class="section">
            <h2>Social Media Activity</h2>
            {% if social_posts %}
            <table>
                <tr><th>Post Type</th><th>Characters</th><th>Status</th></tr>
                {% for post in social_posts %}
                <tr>
                    <td>{{post.type}}</td>
                    <td>{{post.char_count}}</td>
                    <td><span class="badge badge-{{post.status}}">{{post.status}}</span></td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No social media activity this period.</p>
            {% endif %}
        </div>

        <div class="footer">
            Generated by TFI Agent &mdash; {{org_name}} &mdash; {{generated_at}}
        </div>
    </div>
</body>
</html>"""


class ReportGenerator:
    """Generates monthly HTML reports for TFI."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            config["reporting"]["output_dir"]
        )
        self.history_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            config["reporting"]["history_dir"]
        )
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)

    def generate(self):
        """Generate monthly report from collected data."""
        self.logger.info("Generating monthly report...")
        now = datetime.now()
        month = now.strftime("%B %Y")
        data = self._collect_data()
        template = Template(REPORT_TEMPLATE)
        html = template.render(
            org_name=self.config["org"]["name"],
            month=month,
            generated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            health_score=data.get("health_score", "N/A"),
            posts_published=data.get("posts_published", 0),
            research_articles=data.get("research_articles", 0),
            linkedin_posts=data.get("linkedin_posts", 0),
            broken_links=data.get("broken_links", 0),
            summary_text=data.get("summary_text", "Report generated."),
            seo_findings=data.get("seo_findings", []),
            content_posts=data.get("content_posts", []),
            research_topics=data.get("research_topics", []),
            performance_pages=data.get("performance_pages", []),
            ssl_info=data.get("ssl_info"),
            social_posts=data.get("social_posts", [])
        )
        filepath = os.path.join(self.output_dir, f"report_{now.strftime('%Y-%m')}.html")
        with open(filepath, "w") as f:
            f.write(html)
        self._save_history(data, now)
        self.logger.info(f"Report saved: {filepath}")
        return filepath

    def _collect_data(self):
        """Collect data from all agent outputs."""
        data = {"health_score": "N/A", "posts_published": 0, "research_articles": 0,
                "linkedin_posts": 0, "broken_links": 0, "summary_text": ""}
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        seo_data_dir = os.path.join(base, self.config["paths"]["output_base"], "seo_data")
        # Web health
        web_file = os.path.join(seo_data_dir, f"web_health_{datetime.now().strftime('%Y%m')}.json")
        if os.path.exists(web_file):
            with open(web_file) as f:
                web = json.load(f)
            data["health_score"] = web.get("health_score", "N/A")
            perf = web.get("checks", {}).get("performance", [])
            data["performance_pages"] = perf
            bl = web.get("checks", {}).get("broken_links", {})
            data["broken_links"] = bl.get("broken_count", 0)
            data["ssl_info"] = web.get("checks", {}).get("ssl")
        # SEO
        seo_file = os.path.join(seo_data_dir, f"seo_{datetime.now().strftime('%Y%m')}.json")
        if os.path.exists(seo_file):
            with open(seo_file) as f:
                seo = json.load(f)
            data["seo_findings"] = seo.get("findings", [])
        # Content
        content_dir = os.path.join(base, self.config["paths"]["output_base"], "blog_drafts")
        content_file = os.path.join(content_dir, f"content_{datetime.now().strftime('%Y%m')}.json")
        if os.path.exists(content_file):
            with open(content_file) as f:
                content = json.load(f)
            data["content_posts"] = content.get("posts_created", [])
            data["posts_published"] = len([p for p in data["content_posts"] if p.get("status") == "published"])
        # Research
        research_dir = os.path.join(base, self.config["paths"]["output_base"], "research_briefs")
        research_file = os.path.join(research_dir, f"research_{datetime.now().strftime('%Y%m')}.json")
        if os.path.exists(research_file):
            with open(research_file) as f:
                research = json.load(f)
            data["research_topics"] = research.get("topics_researched", [])
            data["research_articles"] = len(research.get("articles_found", []))
        # Social
        social_dir = os.path.join(base, self.config["paths"]["output_base"], "linkedin_posts")
        social_file = os.path.join(social_dir, f"social_{datetime.now().strftime('%Y%m')}.json")
        if os.path.exists(social_file):
            with open(social_file) as f:
                social = json.load(f)
            data["social_posts"] = social.get("posts_created", [])
            data["linkedin_posts"] = len(data["social_posts"])
        # Build summary
        hs = data["health_score"]
        score_text = "excellent" if isinstance(hs, int) and hs >= 80 else "needs attention" if isinstance(hs, int) and hs >= 50 else "critical"
        data["summary_text"] = (
            f"Site health score is {hs}/100 ({score_text}). "
            f"{data['posts_published']} blog posts published, "
            f"{data['research_articles']} research articles reviewed, "
            f"{data['linkedin_posts']} LinkedIn posts created, "
            f"{data['broken_links']} broken links detected."
        )
        return data

    def _save_history(self, data, now):
        """Save report data as JSON for historical comparison."""
        history_file = os.path.join(self.history_dir, f"{now.strftime('%Y-%m')}.json")
        with open(history_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

"""Markdown Blog CMS for TFI Agent."""
import os
import re
import json
from datetime import datetime


class BlogCMS:
    """Converts Markdown blog posts to HTML pages."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.cms_config = config["cms"]
        self.content_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.cms_config["content_dir"]
        )
        self.templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.cms_config["templates_dir"]
        )
        self.build_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            self.cms_config["build_dir"]
        )
        os.makedirs(self.content_dir, exist_ok=True)
        os.makedirs(self.build_dir, exist_ok=True)

    def create_post(self, title, slug, content, author="TFI Team", pillar="", tags=None,
                    meta_description="", status="draft"):
        """Create a new blog post as a Markdown file."""
        tags = tags or []
        front_matter = f"""---
title: "{title}"
slug: "{slug}"
author: "{author}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
updated: "{datetime.now().strftime('%Y-%m-%d')}"
pillar: "{pillar}"
tags: [{', '.join(f'"{t}"' for t in tags)}]
meta_description: "{meta_description}"
status: "{status}"
---

"""
        filepath = os.path.join(self.content_dir, f"{slug}.md")
        with open(filepath, "w") as f:
            f.write(front_matter + content)
        self.logger.info(f"Post created: {filepath}")
        return filepath

    def publish_post(self, slug):
        """Change post status to published."""
        filepath = os.path.join(self.content_dir, f"{slug}.md")
        if not os.path.exists(filepath):
            self.logger.error(f"Post not found: {slug}")
            return False
        with open(filepath, "r") as f:
            content = f.read()
        content = re.sub(r'status: "draft"', 'status: "published"', content)
        with open(filepath, "w") as f:
            f.write(content)
        self.logger.info(f"Post published: {slug}")
        return True

    def build_post(self, slug):
        """Convert a single Markdown post to HTML."""
        md_path = os.path.join(self.content_dir, f"{slug}.md")
        if not os.path.exists(md_path):
            self.logger.error(f"Markdown not found: {slug}")
            return None
        with open(md_path, "r") as f:
            raw = f.read()
        meta, body = self.parse_markdown(raw)
        template_path = os.path.join(self.templates_dir, "post.html")
        if not os.path.exists(template_path):
            self.logger.error("Post template not found")
            return None
        with open(template_path, "r") as f:
            template = f.read()
        html_content = self.md_to_html(body)
        html = template.replace("{{title}}", meta.get("title", "")).replace(
            "{{slug}}", slug).replace("{{author}}", meta.get("author", "TFI Team")).replace(
            "{{date}}", meta.get("date", "")).replace(
            "{{pillar}}", meta.get("pillar", "")).replace(
            "{{meta_description}}", meta.get("meta_description", "")).replace(
            "{{content}}", html_content).replace(
            "{{tags}}", ", ".join(meta.get("tags", []))).replace(
            "{{url}}", self.config["org"]["url"] + "/blog/" + slug + ".html")
        output_path = os.path.join(self.build_dir, f"{slug}.html")
        with open(output_path, "w") as f:
            f.write(html)
        self.logger.info(f"Built post: {output_path}")
        return output_path

    def build_index(self):
        """Build the blog index page listing all published posts."""
        posts = []
        for filename in sorted(os.listdir(self.content_dir), reverse=True):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(self.content_dir, filename)
            with open(filepath, "r") as f:
                raw = f.read()
            meta, _ = self.parse_markdown(raw)
            if meta.get("status") == "published":
                posts.append(meta)
        template_path = os.path.join(self.templates_dir, "blog_index.html")
        if not os.path.exists(template_path):
            self.logger.error("Index template not found")
            return None
        with open(template_path, "r") as f:
            template = f.read()
        posts_html = ""
        for post in posts:
            posts_html += f"""<article class="blog-entry">
                <h2><a href="/blog/{post.get('slug', '')}.html">{post.get('title', 'Untitled')}</a></h2>
                <p class="meta">By {post.get('author', 'TFI Team')} | {post.get('date', '')} | {post.get('pillar', '')}</p>
                <p class="excerpt">{post.get('meta_description', '')}</p>
                <a href="/blog/{post.get('slug', '')}.html" class="read-more">Read More</a>
            </article>\n"""
        html = template.replace("{{posts}}", posts_html).replace("{{org_name}}", self.config["org"]["name"]).replace(
            "{{org_url}}", self.config["org"]["url"])
        output_path = os.path.join(self.build_dir, "blog.html")
        with open(output_path, "w") as f:
            f.write(html)
        self.logger.info(f"Built index: {output_path} ({len(posts)} posts)")
        return output_path

    def build_all(self):
        """Build all published posts and the index page."""
        built = []
        for filename in os.listdir(self.content_dir):
            if filename.endswith(".md"):
                slug = filename[:-3]
                meta, _ = self.parse_markdown_file(os.path.join(self.content_dir, filename))
                if meta.get("status") == "published":
                    result = self.build_post(slug)
                    if result:
                        built.append(slug)
        self.build_index()
        return built

    def parse_markdown(self, raw):
        """Parse front matter and body from markdown."""
        meta = {}
        body = raw
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1].strip()
                body = parts[2].strip()
                for line in fm.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key in ("tags",):
                            value = [t.strip().strip('"') for t in value.strip("[]").split(",")]
                        meta[key] = value
        return meta, body

    def parse_markdown_file(self, filepath):
        """Parse a markdown file."""
        with open(filepath, "r") as f:
            return self.parse_markdown(f.read())

    def md_to_html(self, md_text):
        """Convert basic Markdown to HTML."""
        try:
            import markdown
            return markdown.markdown(md_text, extensions=["fenced_code", "tables"])
        except ImportError:
            self.logger.warning("markdown package not installed, using basic converter")
            return self._basic_md_to_html(md_text)

    def _basic_md_to_html(self, md_text):
        """Basic markdown to HTML without external package."""
        html = md_text
        html = re.sub(r"^### (.*$)", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.*$)", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.*$)", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)
        html = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', html)
        html = re.sub(r"^> (.*$)", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)
        html = re.sub(r"^- (.*$)", r"<li>\1</li>", html, flags=re.MULTILINE)
        html = re.sub(r"(<li>.*</li>)", r"<ul>\1</ul>", html, flags=re.DOTALL)
        html = re.sub(r"\n\n", "</p><p>", html)
        html = f"<p>{html}</p>"
        return html

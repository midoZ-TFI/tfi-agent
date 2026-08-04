"""TFI Social Agent — Generates and publishes LinkedIn content."""
import os
import json
from datetime import datetime
from random import choice, sample

from tools.web_scraper import WebScraper


class SocialAgent:
    """Manages LinkedIn content creation and publishing."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.social_config = config["social"]["linkedin"]
        self.output_dir = os.path.join(config["paths"]["output_base"], "linkedin_posts")
        os.makedirs(self.output_dir, exist_ok=True)
        self.scraper = WebScraper(config, logger)
        self.results = {"status": "pending", "posts_created": [], "posts_published": []}

    def run(self):
        self.logger.info("Social Agent starting...")
        try:
            if not self.social_config["enabled"]:
                self.logger.info("LinkedIn integration disabled in config.")
                self.results["status"] = "skipped"
                return self.results
            posts_this_month = self.social_config["posts_per_month"]
            for i in range(posts_this_month):
                self.create_linkedin_post(i)
            self.results["status"] = "completed"
            self.results["timestamp"] = datetime.now().isoformat()
            self.save_results()
            self.logger.info("Social Agent completed successfully.")
            return self.results
        except Exception as e:
            self.logger.error(f"Social Agent error: {e}")
            self.results["status"] = "error"
            self.results["error"] = str(e)
            return self.results

    def create_linkedin_post(self, index):
        """Create a LinkedIn post based on content mix."""
        content_mix = self.social_config["content_mix"]
        # Weighted random selection of post type
        post_types = list(content_mix.keys())
        weights = [content_mix[t] for t in post_types]
        post_type = self._weighted_choice(post_types, weights)
        self.logger.info(f"Creating LinkedIn post {index + 1}: {post_type}")
        content = self.generate_post_content(post_type)
        hashtags = self.select_hashtags()
        full_post = f"{content}\n\n{hashtags}"
        filename = f"linkedin_{post_type}_{datetime.now().strftime('%Y%m%d')}_{index}.txt"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w") as f:
            f.write(full_post)
        post_record = {
            "type": post_type,
            "filename": filename,
            "filepath": filepath,
            "char_count": len(full_post),
            "status": "draft"
        }
        self.results["posts_created"].append(post_record)
        if self.social_config.get("auto_publish", False):
            self.publish_post(full_post, post_record)
        else:
            self.logger.info(f"  Post saved as draft: {filename} (auto_publish is off)")
        self.logger.info(f"  LinkedIn post created: {post_type} ({len(full_post)} chars)")

    def generate_post_content(self, post_type):
        """Generate content for a specific post type."""
        templates = {
            "blog_promo": [
                "New on the TFI blog: {title}\n\nAt The Fitness Initiative, we're committed to sharing practical, evidence-based health guidance with our Rochester community. Our latest post dives into {topic} — because everyone deserves access to the knowledge that can change their health trajectory.\n\nRead more: {url}\n\nWhat's one health habit that made a difference in your life?",
                "Just published: {title}\n\nThis one hits close to home for our team. {topic} affects thousands of families in Monroe County, and we believe understanding it is the first step toward action.\n\nCheck it out: {url}\n\nTag someone who needs to see this."
            ],
            "program_updates": [
                "Program Spotlight: Cooking with Exercise\n\nThis year-long participatory design program, developed in partnership with Rochester Public Network, is transforming how families in Rochester think about the connection between what they eat and how they move.\n\nParticipants aren't just learning — they're co-creating the curriculum. That's the TFI difference.\n\nInterested in joining? Visit thefitnessinitiative.org\n\n#HealthEquity #NonprofitRochester",
                "ReNewMe is back and better than ever.\n\nUsing a holistic Maslow pyramid model, this program addresses health from the ground up — physical wellness, emotional well-being, social connection, and self-actualization.\n\nBecause real health transformation isn't just about exercise. It's about the whole person.\n\nLearn more at thefitnessinitiative.org"
            ],
            "research_sharing": [
                "New research on {topic} just caught our attention.\n\nThe findings reinforce what we see every day at TFI: {finding}\n\nThis is exactly why community-based health programs matter. When people have access to the right support, outcomes improve — dramatically.\n\nWhat are your thoughts on this research?",
                "A recent study published in {journal} highlights something critical for nonprofit health organizations:\n\n{finding}\n\nAt TFI, we've been incorporating these principles into our programs for years. The science is catching up to what our community already knows — health is a team effort.\n\nSource: {source}"
            ],
            "community_impact": [
                "Here's what health equity looks like in practice:\n\nAt The Fitness Initiative, we served {number} families in Monroe County last year through programs that are FREE or low-cost.\n\nBut the impact goes beyond numbers. It's the mom who learned to manage her diabetes through movement. The veteran who found community through our adaptive fitness program. The kids who discovered that healthy food can actually taste good.\n\nThis is what nonprofit work looks like. This is TFI.\n\nSupport our mission at thefitnessinitiative.org",
                "A message from one of our Cooking with Exercise participants:\n\n\"I never thought I could afford to eat healthy. TFI showed me it's not about expensive ingredients — it's about knowledge and community.\"\n\nThis is why we do what we do. Health should never be a privilege.\n\n#CommunityHealth #HealthEquity #RochesterNY"
            ],
            "nonprofit_insights": [
                "Running a health-focused nonprofit in 2025 has taught me three things:\n\n1. Community trust is earned through consistency, not campaigns\n2. The best programs are designed WITH the community, not FOR them\n3. Impact measurement matters — but stories move people\n\nAt TFI, we apply these principles daily. Our Cooking with Exercise program was built through a year of participatory design with real community input.\n\nWhat principles guide your nonprofit work?",
                "Health equity isn't just a buzzword — it's a measurable goal.\n\nIn Monroe County, disparities in health outcomes follow predictable lines: income, race, and zip code. At The Fitness Initiative, we're working to break those patterns.\n\nHow? By making our programs accessible (free/low-cost), culturally relevant, and community-designed.\n\nThe data shows it works. The stories confirm it.\n\n#NonprofitImpact #HealthEquity"
            ]
        }
        template = choice(templates.get(post_type, templates["nonprofit_insights"]))
        # Fill in placeholders
        content = template.format(
            title="[See latest blog post]",
            topic="community health and wellness",
            url="https://www.thefitnessinitiative.org/blog.html",
            finding="community-based interventions significantly improve health outcomes",
            journal="[Recent Journal]",
            source="[Link in comments]",
            number="hundreds of"
        )
        # LinkedIn limit: 3000 chars
        if len(content) > 2900:
            content = content[:2897] + "..."
        return content

    def select_hashtags(self):
        """Select hashtags for a post."""
        always = self.social_config.get("hashtags", {}).get("always", [])
        rotate = self.social_config.get("hashtags", {}).get("rotate", [])
        rotating = sample(rotate, min(3, len(rotate)))
        all_tags = always + rotating
        return " ".join(f"#{tag}" for tag in all_tags)

    def publish_post(self, content, post_record):
        """Publish post to LinkedIn via API (requires access token)."""
        token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        if not token:
            self.logger.info("  No LINKEDIN_ACCESS_TOKEN found — saving as draft only")
            post_record["status"] = "draft_no_token"
            return
        try:
            resp = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "author": f"urn:li:person:{self.get_person_urn()}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": content},
                            "shareMediaCategory": "ARTICLE"
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
                },
                timeout=30
            )
            if resp.status_code in (200, 201):
                post_record["status"] = "published"
                self.results["posts_published"].append(post_record)
                self.logger.info("  LinkedIn post published successfully")
            else:
                self.logger.warning(f"  LinkedIn API returned {resp.status_code}: {resp.text[:200]}")
                post_record["status"] = f"api_error_{resp.status_code}"
        except Exception as e:
            self.logger.error(f"  LinkedIn publish failed: {e}")
            post_record["status"] = "publish_error"

    def get_person_urn(self):
        """Get LinkedIn person URN from API."""
        token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        try:
            resp = requests.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
            if resp.status_code == 200:
                return resp.json().get("id", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def _weighted_choice(items, weights):
        """Weighted random selection."""
        total = sum(weights)
        r = choice(range(1, total + 1))
        cumulative = 0
        for item, weight in zip(items, weights):
            cumulative += weight
            if r <= cumulative:
                return item
        return items[-1]

    def save_results(self):
        """Save social results for reporting."""
        filepath = os.path.join(self.output_dir, f"social_{datetime.now().strftime('%Y%m')}.json")
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        self.logger.info(f"Social results saved to {filepath}")

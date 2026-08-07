"""TFI Agent - Social Agent"""

import json, logging, os, random, re, base64 as b64
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger("tfi_agent.social")
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

TEMPLATES = []

TEMPLATES.append({
    "type": "community_impact",
    "content": "In Rochester NY, too many people living with chronic diseases cannot afford healthy food or gym memberships. The Fitness Initiative exists to change that through grant-funded programs like Cooking with Exercise, ReNewMe, and Fitness 101. We seek collaboration partners: healthcare systems, community foundations, and nonprofits who share our vision for health equity in Monroe County. What does health equity look like in your community?",
    "hashtags": ["HealthEquity", "NonprofitRochester", "FitnessForAll", "CommunityHealth", "RochesterNY"],
})

TEMPLATES.append({
    "type": "nonprofit_insights",
    "content": "Leading The Fitness Initiative taught me that sustainable community health requires cross-sector collaboration. No single organization solves chronic disease alone. Our grant-funded programs serve people managing Parkinson, diabetes, and heart disease who lack resources for private wellness. If you are a nonprofit leader or healthcare executive, let us connect. How is your organization building partnerships to address health disparities?",
    "hashtags": ["NonprofitRochester", "HealthEquity", "ChronicDiseasePrevention", "CommunityPartnerships", "MonroeCountyNY"],
})

TEMPLATES.append({
    "type": "program_updates",
    "content": "ReNewMe is a lifeline for Rochester residents rebuilding health after chronic disease diagnosis. Through grant-funded exercise and nutrition plans, participants who could not afford private coaching see real results: improved mobility, better nutrition habits, and renewed confidence. We seek healthcare partners and nonprofit collaborators to expand access. Could your organization benefit from a partnership on chronic disease management?",
    "hashtags": ["HealthEquity", "ReNewMe", "FitnessForAll", "ChronicDiseasePrevention", "RochesterNY"],
})

TEMPLATES.append({
    "type": "research_sharing",
    "content": "Regular physical activity reduces Type 2 diabetes risk by up to 58 percent. But the people who need this most have the least access. At The Fitness Initiative, our grant-funded programs remove financial barriers so participants can focus on health. We invite healthcare systems and nonprofits to explore collaboration. How can clinical and community organizations collaborate on chronic disease prevention?",
    "hashtags": ["ChronicDiseasePrevention", "HealthEquity", "ExerciseIsMedicine", "CommunityHealth", "NonprofitRochester"],
})


class SocialAgent:
    def __init__(self, config):
        self.config = config
        self.project_root = PROJECT_ROOT
        self.social_config = config.get("social", {}).get("linkedin", {})
        self.posts_dir = self.project_root / "content" / "linkedin_posts"
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.blog_posts_dir = self.project_root / config["cms"]["content_dir"]
        self.auto_publish = self.social_config.get("auto_publish", False)
        self.posts_generated = []
        self.posts_published = []

    def run(self):
        logger.info("=== Social Agent starting ===")
        week_num = datetime.now().isocalendar()[1]
        idx = week_num % len(TEMPLATES)
        tpl = TEMPLATES[idx]
        logger.info("Using template %d: %s", idx, tpl["type"])
        post = {"type": tpl["type"], "content": tpl["content"], "hashtags": tpl["hashtags"], "slug": "tfi-weekly-post", "word_count": len(tpl["content"].split())}
        self.posts_generated.append(post)
        self._save_post(post)
        if self.auto_publish:
            logger.info("Auto-publishing...")
            result = self._publish_post(post)
            self.posts_published.append(result or "draft")
        else:
            self.posts_published = ["draft"]
        published = len([p for p in self.posts_published if p != "draft"])
        logger.info("Social Agent done - %d generated, %d published", len(self.posts_generated), published)
        return {"posts_generated": len(self.posts_generated), "posts_published": self.posts_published, "content_mix": {tpl["type"]: 1}, "hashtags_used": tpl["hashtags"], "timestamp": datetime.now(timezone.utc).isoformat()}

    def _save_post(self, post):
        date_str = datetime.now().strftime("%Y-%m-%d")
        tags = ", ".join(post.get("hashtags", []))
        fm = "---\ndate: " + date_str + "\ntype: " + str(post.get("type","")) + "\nhashtags: " + tags + "\nstatus: draft\n---\n\n"
        fp = self.posts_dir / (date_str + "-tfi-weekly-post.md")
        fp.write_text(fm + post["content"], encoding="utf-8")
        logger.info("Saved: %s", fp.name)

    def _get_person_id_from_token(self, access_token):
        try:
            parts = access_token.split(".")
            if len(parts) != 3:
                logger.error("Bad JWT: %d parts", len(parts))
                return None
            payload = parts[1]
            pad = 4 - len(payload) % 4
            if pad != 4:
                payload += "=" * pad
            data = json.loads(b64.urlsafe_b64decode(payload))
            pid = data.get("sub")
            logger.info("JWT sub=%s", pid)
            return str(pid) if pid else None
        except Exception as e:
            logger.error("Decode error: %s", e)
            return None

    def _publish_post(self, post):
        token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        if not token:
            logger.warning("No LINKEDIN_ACCESS_TOKEN")
            return None
        logger.info("Token length: %d", len(token))
        try:
            tags_text = " ".join("#" + t for t in post.get("hashtags", []))
            body = post["content"] + "\n\n" + tags_text
            pid = self._get_person_id_from_token(token)
            if not pid:
                logger.error("No person ID")
                return None
            logger.info("Person ID: %s", pid)
            hdrs = {"Authorization": "Bearer " + token, "Content-Type": "application/json", "LinkedIn-Version": "202401", "X-Restli-Protocol-Version": "2.0.0"}
            payload = {"author": "urn:li:person:" + pid, "commentary": body, "visibility": "PUBLIC", "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []}}
            resp = requests.post("https://api.linkedin.com/rest/posts", headers=hdrs, json=payload, timeout=30)
            logger.info("LinkedIn response: %d", resp.status_code)
            if resp.status_code in (200, 201):
                logger.info("SUCCESS! Published")
                return "published"
            logger.error("Error %d: %s", resp.status_code, resp.text[:300])
            return None
        except Exception as e:
            logger.error("Failed: %s", e)
            return None
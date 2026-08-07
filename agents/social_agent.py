"""TFI Agent - Social Agent"""
import json, logging, os, random, re, subprocess, base64 as b64
from datetime import datetime, timezone
from pathlib import Path
import requests

logger = logging.getLogger("tfi_agent.social")
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

POST_TEMPLATES = [
    {"type": "community_impact", "content": "In Rochester, too many people living with chronic diseases are told to eat better and exercise but they cannot afford healthy food or a gym membership. That is exactly why The Fitness Initiative exists. Through our Cooking with Exercise, ReNewMe, and Fitness 101 programs, we provide grant-funded fitness and nutrition support to those who need it most. But we cannot do it alone. We are actively seeking collaboration partners: healthcare systems, community foundations, and nonprofit organizations who share our vision for health equity in Monroe County. If your organization is working to improve health outcomes for underserved populations, I would love to start a conversation. What does health equity look like in your community?", "hashtags": ["HealthEquity", "NonprofitRochester", "FitnessForAll", "CommunityHealth", "RochesterNY"]},
    {"type": "nonprofit_insights", "content": "One of the biggest lessons I have learned leading The Fitness Initiative: sustainable community health programs require cross-sector collaboration. No single organization can solve chronic disease alone. It takes hospitals, nonprofits, community foundations, and local government working together. At TFI, our grant-funded programs serve people in Rochester managing conditions like Parkinson, diabetes, and heart disease but who lack financial resources for private wellness services. The impact is measurable: participants improve health outcomes, gain confidence, and build supportive community connections. If you are a nonprofit leader or healthcare executive working in chronic disease prevention, let us connect. Collaboration multiplies impact. How is your organization building partnerships to address health disparities?", "hashtags": ["NonprofitRochester", "HealthEquity", "ChronicDiseasePrevention", "CommunityPartnerships", "MonroeCountyNY"]},
    {"type": "program_updates", "content": "ReNewMe is more than a fitness program. It is a lifeline for people in Rochester rebuilding their health after chronic disease diagnosis. Through grant-funded personalized exercise and nutrition plans, participants who could not afford private coaching are seeing real results: improved mobility, better nutrition habits, and renewed confidence. This is what happens when community organizations remove financial barriers to wellness. We are looking for healthcare partners and nonprofit collaborators who want to expand access to programs like this. Could your organization benefit from a partnership focused on chronic disease management through exercise and nutrition?", "hashtags": ["HealthEquity", "ReNewMe", "FitnessForAll", "ChronicDiseasePrevention", "RochesterNY"]},
    {"type": "research_sharing", "content": "The evidence is clear: regular physical activity can reduce the risk of Type 2 diabetes by up to 58 percent. But here is the gap: the people who need this most often have the least access to safe affordable exercise programs. At The Fitness Initiative, our participants come to us not because they lack motivation, but because they lack financial access to resources that could change their health. Our grant-funded programs are designed specifically to remove those barriers. For healthcare systems and nonprofits working on diabetes prevention, this is an invitation to explore how we can work together. How can clinical and community-based organizations collaborate more effectively on chronic disease prevention?", "hashtags": ["ChronicDiseasePrevention", "HealthEquity", "ExerciseIsMedicine", "CommunityHealth", "NonprofitRochester"]},
    {"type": "community_impact", "content": "Cooking with Exercise started as a simple idea: teach people how to prepare healthy meals and pair them with appropriate physical activity. But for participants in Rochester who are managing diabetes, heart disease, or obesity and who cannot afford private nutritionists or trainers, this program has become transformative. At The Fitness Initiative, we have seen participants gain control over their chronic conditions simply by having access to the right education and support. All grant-funded. No cost barriers. We believe every person deserves the tools to manage their health regardless of income. If your organization serves similar communities, there is room for us to collaborate. What nutrition education programs are making an impact in your community?", "hashtags": ["NutritionEducation", "HealthEquity", "NonprofitRochester", "CookingWithExercise", "FitnessForAll"]},
]

class SocialAgent:
    def __init__(self, config):
        self.config = config
        self.project_root = PROJECT_ROOT
        self.social_config = config.get("social", {}).get("linkedin", {})
        self.posts_dir = self.project_root / "content" / "linkedin_posts"
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.research_briefs_dir = self.project_root / "content" / "research_briefs"
        self.blog_posts_dir = self.project_root / config["cms"]["content_dir"]
        self.posts_per_month = self.social_config.get("posts_per_month", 4)
        self.content_mix = self.social_config.get("content_mix", {})
        self.hashtags_config = self.social_config.get("hashtags", {})
        self.auto_publish = self.social_config.get("auto_publish", False)
        self.posts_generated = []
        self.posts_published = []

    def run(self):
        logger.info("=== Social Agent starting ===")
        week_num = datetime.now().isocalendar()[1]
        idx = week_num % len(POST_TEMPLATES)
        tpl = POST_TEMPLATES[idx]
        logger.info(f"Using template #{idx} (week {week_num}): {tpl[chr(39)+'type'+chr(39)]}")
        post = {"type": tpl["type"], "content": tpl["content"], "hashtags": tpl["hashtags"], "slug": "tfi-weekly-post", "word_count": len(tpl["content"].split())}
        self.posts_generated.append(post)
        self._save_post(post)
        if self.auto_publish:
            logger.info("Auto-publishing...")
            result = self._publish_post(post)
            self.posts_published.append(result or "draft")
        else:
            self.posts_published = ["draft"]
        logger.info(f"Social Agent complete - {len(self.posts_generated)} generated, {len([p for p in self.posts_published if p != chr(39)+'draft'+chr(39)])} published")
        return {"posts_generated": len(self.posts_generated), "posts_published": self.posts_published, "content_mix": {tpl["type"]: 1}, "hashtags_used": tpl["hashtags"], "timestamp": datetime.now(timezone.utc).isoformat()}

    def _save_post(self, post):
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}-tfi-weekly-post.md"
        filepath = self.posts_dir / filename
        frontmatter = f"---
date: {date_str}
type: {post.get('type', 'unknown')}
hashtags: {', '.join(post.get('hashtags', []))}
status: draft
---

"
        filepath.write_text(frontmatter + post["content"], encoding="utf-8")
        logger.info(f"Saved post: {filename}")

    def _get_person_id_from_token(self, access_token):
        try:
            parts = access_token.split(".")
            if len(parts) != 3:
                logger.error(f"Not a valid JWT ({len(parts)} parts)")
                return None
            payload = parts[1]
            pad = 4 - len(payload) % 4
            if pad != 4:
                payload += "=" * pad
            decoded = b64.urlsafe_b64decode(payload)
            token_data = json.loads(decoded)
            person_id = token_data.get("sub")
            logger.info(f"JWT sub={person_id}")
            if person_id:
                return str(person_id)
            logger.error(f"No sub in token. Keys: {list(token_data.keys())}")
            return None
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return None

    def _publish_post(self, post):
        access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            logger.warning("LINKEDIN_ACCESS_TOKEN not set")
            return None
        logger.info(f"Token length: {len(access_token)}")
        try:
            hashtags_text = " ".join(f"#{t}" for t in post.get("hashtags", []))
            full_content = post["content"] + "

" + hashtags_text
            person_id = self._get_person_id_from_token(access_token)
            if not person_id:
                logger.error("No person ID")
                return None
            logger.info(f"Person ID: {person_id}")
            headers = {"Authorization": "Bearer " + access_token, "Content-Type": "application/json", "LinkedIn-Version": "202401", "X-Restli-Protocol-Version": "2.0.0"}
            payload = {"author": "urn:li:person:" + person_id, "commentary": full_content, "visibility": "PUBLIC", "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []}}
            resp = requests.post("https://api.linkedin.com/rest/posts", headers=headers, json=payload, timeout=30)
            logger.info(f"LinkedIn response: {resp.status_code}")
            if resp.status_code in (200, 201):
                logger.info(f"SUCCESS! Post published")
                return "published"
            logger.error(f"LinkedIn error {resp.status_code}: {resp.text[:300]}")
            return None
        except Exception as e:
            logger.error(f"Publish failed: {e}")
            return None
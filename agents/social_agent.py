"""TFI Social Agent - LinkedIn content for nonprofit business leaders."""
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
                self.logger.info("LinkedIn integration disabled.")
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
            self.logger.error("Social Agent error: %s" % e)
            self.results["status"] = "error"
            self.results["error"] = str(e)
            return self.results

    def create_linkedin_post(self, index):
        content_mix = self.social_config["content_mix"]
        post_types = list(content_mix.keys())
        weights = [content_mix[t] for t in post_types]
        post_type = self._weighted_choice(post_types, weights)
        self.logger.info("Creating LinkedIn post %d: %s" % (index + 1, post_type))
        content = self.generate_post_content(post_type)
        hashtags = self.select_hashtags()
        full_post = content + "\n\n" + hashtags
        filename = "linkedin_%s_%s_%d.txt" % (post_type, datetime.now().strftime("%Y%m%d"), index)
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w") as f:
            f.write(full_post)
        post_record = {"type": post_type, "filename": filename, "char_count": len(full_post), "status": "draft"}
        self.results["posts_created"].append(post_record)
        if self.social_config.get("auto_publish", False):
            self.publish_post(full_post, post_record)
        self.logger.info("LinkedIn post created: %s (%d chars)" % (post_type, len(full_post)))

    def generate_post_content(self, post_type):
        """Generate LinkedIn content for nonprofit leaders about collaboration to serve underserved chronic disease populations."""
        templates = {
            "blog_promo": [
                "Chronic disease does not care about your income level. But access to healthy living resources often depends on it.\n\n"
                "At The Fitness Initiative, we exist to close that gap. Our grant-funded programs serve individuals in Monroe County "
                "who are living with chronic diseases like diabetes, heart disease, and Parkinson's, and who otherwise could not afford "
                "the nutrition guidance and exercise support they need.\n\n"
                "Our latest article shares what we have learned about making health accessible to those who need it most.\n\n"
                "If your organization serves a similar population, I would welcome a conversation about collaboration.\n\n"
                "Read more: https://www.thefitnessinitiative.org/blog.html",

                "What happens when someone with a chronic disease cannot afford to eat well or stay active?\n\n"
                "Their condition worsens. Healthcare costs rise. Quality of life declines. And the cycle continues.\n\n"
                "At The Fitness Initiative, we break that cycle through grant-funded programs that provide exercise, nutrition, "
                "and wellness support at no cost to participants. Our latest blog post explores how community-driven approaches "
                "are making a measurable difference.\n\n"
                "If your nonprofit is working in this space, let us connect. Collaboration amplifies impact.\n\n"
                "https://www.thefitnessinitiative.org/blog.html"
            ],
            "program_updates": [
                "Program Spotlight: Cooking with Exercise\n\n"
                "Imagine being told you need to change your diet and start exercising to manage your chronic condition, "
                "but you cannot afford healthy food or a gym membership.\n\n"
                "That is the reality for many people in our community. Cooking with Exercise was designed specifically for them.\n\n"
                "Developed in partnership with Rochester Public Network through a full year of community input, this grant-funded "
                "program teaches participants how to prepare nutritious meals and integrate movement into their daily lives, "
                "regardless of their financial situation.\n\n"
                "For nonprofit leaders looking for a proven collaboration model, this is what partnership in action looks like.\n\n"
                "I would welcome conversations with organizations interested in bringing this approach to their communities.",

                "ReNewMe: Addressing the whole person, not just the diagnosis\n\n"
                "When someone is living with a chronic disease and struggling financially, treating the condition alone is not enough. "
                "They need support for their physical health, emotional well-being, social connection, and self-empowerment.\n\n"
                "ReNewMe, our grant-funded wellness program, uses a Maslow pyramid framework to address all four dimensions. "
                "Participants are not just patients. They are people rebuilding their lives.\n\n"
                "For nonprofit organizations serving underserved populations with chronic conditions, this model demonstrates what "
                "holistic, grant-funded care can achieve.\n\n"
                "If your organization is interested in collaborating on programs like this, let us talk."
            ],
            "research_sharing": [
                "Research consistently shows that lifestyle intervention is one of the most effective treatments for chronic disease. "
                "But for low-income populations, access to these interventions is the real challenge.\n\n"
                "At The Fitness Initiative, we use grant funding to remove that barrier. Our programs provide structured exercise "
                "and nutrition support to individuals who cannot afford it, producing measurable improvements in health outcomes.\n\n"
                "For nonprofit leaders, the evidence is clear: community-based programs that serve underserved chronic disease "
                "populations deliver strong outcomes and strong grant ROI.\n\n"
                "The question is not whether this works. It is whether we can scale it together.\n\n"
                "I welcome conversations with organizations ready to collaborate.",

                "New evidence on community-based chronic disease management:\n\n"
                "Structured exercise and nutrition programs can reduce hospitalizations and improve quality of life for individuals "
                "with chronic conditions by up to 30-40 percent. Yet the populations who need these programs most are often the "
                "least able to access them.\n\n"
                "At The Fitness Initiative, grant funding allows us to serve these individuals at no cost. Our participant outcomes "
                "confirm what the research predicts: when you remove financial barriers, people get healthier.\n\n"
                "For nonprofit leaders seeking evidence-based partnership opportunities, our model in Monroe County is producing "
                "results that matter.\n\n"
                "Let us explore what collaboration could look like for your organization."
            ],
            "community_impact": [
                "A reality check for nonprofit leaders:\n\n"
                "In Monroe County, thousands of individuals are living with chronic diseases like diabetes, heart disease, "
                "and Parkinson's. Many of them cannot afford the nutrition guidance, exercise programs, or wellness support "
                "that could improve their conditions.\n\n"
                "The Fitness Initiative exists to change that. Through grant-funded programs developed with community input, "
                "we provide these services at no cost to participants. And the impact is measurable.\n\n"
                "But we cannot do it alone. Partnership with other nonprofit organizations, healthcare providers, and funders "
                "is how we extend our reach.\n\n"
                "If your organization shares this mission, I would value a conversation about working together.\n\n"
                "Collaboration is how we serve more people who need us.",

                "What we have learned serving underserved populations with chronic diseases:\n\n"
                "At The Fitness Initiative, three principles guide everything we do:\n\n"
                "1. Financial barriers are health barriers. When people cannot afford to eat well or stay active, their chronic "
                "conditions worsen. Grant-funded programs remove that obstacle.\n\n"
                "2. Community-designed programs work better. When participants shape the curriculum, engagement and outcomes improve "
                "dramatically. Our Cooking with Exercise program was built this way.\n\n"
                "3. Partnership extends impact. No single organization can serve everyone. Collaboration among nonprofits, "
                "healthcare providers, and funders is how we build sustainable change.\n\n"
                "If your nonprofit serves underserved chronic disease populations, we should talk."
            ],
            "nonprofit_insights": [
                "For nonprofit CEOs and Executive Directors:\n\n"
                "Chronic disease disproportionately affects low-income populations. Yet most health interventions are designed "
                "for people who can already afford to be healthy.\n\n"
                "At The Fitness Initiative, we focus on the gap. Our grant-funded programs serve individuals in Monroe County "
                "living with chronic diseases who cannot afford the resources they need. And we do it through evidence-based, "
                "community-designed programming that produces measurable outcomes.\n\n"
                "This model works. It attracts grants. And it changes lives.\n\n"
                "I am always open to sharing our approach with nonprofit leaders who want to strengthen their impact "
                "in underserved communities.\n\n"
                "Let us connect.",

                "A question for nonprofit leaders: Who is your programming designed for?\n\n"
                "Many health nonprofits design programs for the populations that are easiest to serve. At The Fitness Initiative, "
                "we design programs for the populations that need us most: individuals with chronic diseases who cannot afford "
                "healthy living resources.\n\n"
                "This focus has shaped everything about our model, from our grant-funded structure to our participatory "
                "community design process to our measurable health outcome metrics.\n\n"
                "The result is programming that serves the most underserved and delivers results that funders recognize.\n\n"
                "If your organization is ready to explore collaboration that serves this population, I would welcome the conversation."
            ]
        }
        template = choice(templates.get(post_type, templates["nonprofit_insights"]))
        if len(template) > 2900:
            template = template[:2897] + "..."
        return template

    def select_hashtags(self):
        always = self.social_config.get("hashtags", {}).get("always", [])
        rotate = self.social_config.get("hashtags", {}).get("rotate", [])
        rotating = sample(rotate, min(3, len(rotate)))
        all_tags = always + rotating
        return " ".join("#" + tag for tag in all_tags)

    def publish_post(self, content, post_record):
        token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        if not token:
            post_record["status"] = "draft_no_token"
            return
        try:
            import requests
            resp = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                json={
                    "author": "urn:li:organization:68188867",
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
            else:
                post_record["status"] = "api_error_%d" % resp.status_code
        except Exception as e:
            post_record["status"] = "publish_error"

    def get_person_urn(self): # unused - posting as org
        token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        try:
            import requests
            resp = requests.get("https://api.linkedin.com/v2/me", headers={"Authorization": "Bearer " + token}, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("id", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def _weighted_choice(items, weights):
        total = int(sum(weights))
        r = choice(range(1, total + 1))
        cumulative = 0
        for item, weight in zip(items, weights):
            cumulative += weight
            if r <= cumulative:
                return item
        return items[-1]

    def save_results(self):
        filepath = os.path.join(self.output_dir, "social_%s.json" % datetime.now().strftime("%Y%m"))
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)

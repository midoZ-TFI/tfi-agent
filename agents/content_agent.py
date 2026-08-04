"""TFI Content Agent — Writes and publishes blog posts."""
import os
import json
from datetime import datetime, timedelta
from random import choice, sample

from tools.content_cms import BlogCMS


class ContentAgent:
    """Creates blog content, manages editorial calendar, publishes via CMS."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.content_config = config["content"]
        self.cms = BlogCMS(config, logger)
        self.output_dir = os.path.join(config["paths"]["output_base"], "blog_drafts")
        os.makedirs(self.output_dir, exist_ok=True)
        self.results = {"status": "pending", "posts_created": [], "posts_published": []}

    def run(self):
        self.logger.info("Content Agent starting...")
        try:
            self.generate_content_calendar()
            posts_this_month = self.content_config["blog"]["posts_per_month"]
            for i in range(posts_this_month):
                self.create_blog_post(i)
            self.results["status"] = "completed"
            self.results["timestamp"] = datetime.now().isoformat()
            self.save_results()
            self.logger.info("Content Agent completed successfully.")
            return self.results
        except Exception as e:
            self.logger.error(f"Content Agent error: {e}")
            self.results["status"] = "error"
            self.results["error"] = str(e)
            return self.results

    def generate_content_calendar(self):
        """Generate monthly content calendar based on pillars."""
        self.logger.info("Generating content calendar...")
        pillars = self.content_config["blog"]["pillars"]
        today = datetime.now()
        # Pick different pillars for each post
        selected = sample(pillars, min(self.content_config["blog"]["posts_per_month"], len(pillars)))
        calendar = []
        for i, pillar in enumerate(selected):
            post_date = today + timedelta(days=(i * 15))
            calendar.append({
                "post_number": i + 1,
                "pillar": pillar["name"],
                "planned_date": post_date.strftime("%Y-%m-%d"),
                "status": "planned"
            })
        self.results["content_calendar"] = calendar
        self.logger.info(f"Content calendar: {len(calendar)} posts planned across {len(selected)} pillars")

    def create_blog_post(self, index):
        """Create a single blog post."""
        pillars = self.content_config["blog"]["pillars"]
        pillar = choice(pillars)
        topic = self.pick_topic(pillar)
        slug = self.slugify(topic)
        self.logger.info(f"Creating blog post: {topic} (pillar: {pillar['name']})")
        content = self.generate_post_content(topic, pillar)
        post_meta = {
            "title": topic,
            "slug": slug,
            "author": self.config["people"]["founder"]["name"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "updated": datetime.now().strftime("%Y-%m-%d"),
            "pillar": pillar["name"],
            "tags": pillar["keywords"][:3],
            "meta_description": self.generate_meta_description(topic, pillar),
            "status": "draft"
        }
        try:
            self.cms.create_post(
                title=post_meta["title"],
                slug=slug,
                content=content,
                author=post_meta["author"],
                pillar=pillar["name"],
                tags=post_meta["tags"],
                meta_description=post_meta["meta_description"],
                status="draft"
            )
            self.results["posts_created"].append({
                "title": topic, "slug": slug, "pillar": pillar["name"], "status": "draft"
            })
            self.logger.info(f"Blog post created: {slug}")
        except Exception as e:
            self.logger.error(f"Failed to create post '{topic}': {e}")

    def pick_topic(self, pillar):
        """Pick a specific topic within a pillar."""
        topic_pool = {
            "Movement": [
                "5 Chair Exercises You Can Do During Commercial Breaks",
                "Walking for Heart Health: A Rochester Guide",
                "How Strength Training Helps Manage Type 2 Diabetes",
                "Gentle Morning Stretches for Better Mobility"
            ],
            "Nutrition": [
                "Eating Well on a Budget: Tips from Rochester's Food Pantries",
                "Quick Healthy Meals in Under 20 Minutes",
                "Understanding Food Labels: A Family Guide",
                "Seasonal Eating in Western New York"
            ],
            "Chronic Conditions": [
                "Exercise and Parkinson's: What the Latest Research Says",
                "Managing Diabetes Through Lifestyle Changes",
                "Heart-Healthy Living After a Diagnosis",
                "Cancer Recovery and the Role of Physical Activity"
            ],
            "Community & Equity": [
                "Why Fitness Access Matters in Monroe County",
                "How TFI is Bridging the Health Equity Gap in Rochester",
                "Community Partnerships That Make a Difference",
                "Understanding Social Determinants of Health"
            ],
            "Programs & Partnerships": [
                "Inside Cooking with Exercise: A Year of Impact",
                "ReNewMe: Transforming Lives Through Holistic Wellness",
                "Fitness 101: Bringing Families Together Through Movement",
                "Spotlight on Our Community Health Partners"
            ]
        }
        pool = topic_pool.get(pillar["name"], ["The Importance of Regular Physical Activity",
                "Nutrition Tips for a Healthier Lifestyle", "Building Healthier Communities Together"])
        return choice(pool)

    def generate_post_content(self, topic, pillar):
        """Generate blog post content in markdown."""
        intro = f"""## {topic}\n\nAt The Fitness Initiative, we believe that everyone deserves access to the tools and knowledge needed to live a healthier life. In Rochester and across Monroe County, too many families face barriers to fitness and nutrition — cost, time, transportation, or simply not knowing where to start.\n\nToday, we're diving into a topic that matters: **{topic.lower()}**.\n\n"""
        sections = [
            "### Why This Matters\n\n"
            f"Research consistently shows that {pillar['keywords'][0]} plays a vital role in preventing and managing chronic conditions. According to leading health organizations, regular {pillar['keywords'][0]} can reduce the risk of heart disease, improve mental health, and enhance quality of life for people of all ages and abilities.\n\n"
            f"For communities in Rochester, NY, access to {pillar['keywords'][0]} resources can be the difference between managing a condition and letting it control your life. That's why TFI is committed to making these resources available to everyone — regardless of income, background, or ability.\n\n",
            "### Practical Steps You Can Take\n\n"
            "Here are actionable ways to incorporate healthier habits into your daily routine:\n\n"
            "- **Start small**: Even 10 minutes of movement per day makes a difference\n"
            "- **Involve your family**: Health habits stick when the whole household participates\n"
            "- **Use community resources**: Rochester has parks, trails, and free programs\n"
            "- **Track your progress**: Simple journaling helps maintain motivation\n"
            "- **Ask for help**: TFI and our partners offer free guidance and support\n\n",
            "### How TFI Can Help\n\n"
            f"Our programs — including Cooking with Exercise, ReNewMe, and Fitness 101 — are designed to address {pillar['name'].lower()} in a supportive, community-focused environment. Every program is free or low-cost, because we believe finances should never be a barrier to health.\n\n"
            "Whether you're managing a chronic condition, supporting a loved one, or simply looking to build healthier habits, TFI is here for you. Reach out to learn more about upcoming programs in your area.\n\n",
            "### Looking Ahead\n\n"
            "At TFI, we are continuously evolving our programs based on the latest research and community feedback. Stay tuned for more updates, and don't hesitate to share your story with us — your experience helps shape the future of our work.\n\n"
            "Ready to take the next step? [Explore our programs](https://www.thefitnessinitiative.org/programs.html) or [contact us](https://www.thefitnessinitiative.org/contact.html) to get started.\n"
        ]
        return intro + "\n".join(sections)

    def generate_meta_description(self, topic, pillar):
        """Generate an SEO-friendly meta description."""
        desc = f"Learn about {topic.lower()} with The Fitness Initiative — a Rochester, NY nonprofit making health and wellness accessible for all. Free programs available."
        if len(desc) > 160:
            desc = desc[:157] + "..."
        return desc

    @staticmethod
    def slugify(text):
        """Convert title to URL-friendly slug."""
        slug = text.lower()
        slug = slug.replace("'", "")
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s]+", "-", slug).strip("-")
        return slug

    def save_results(self):
        """Save content results for reporting."""
        filepath = os.path.join(self.output_dir, f"content_{datetime.now().strftime('%Y%m')}.json")
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        self.logger.info(f"Content results saved to {filepath}")

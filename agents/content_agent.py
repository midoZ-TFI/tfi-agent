"""TFI Content Agent - Blog posts designed to engage nonprofit collaboration partners."""
import os
import re
import json
from datetime import datetime, timedelta
from random import choice, sample

from tools.content_cms import BlogCMS


class ContentAgent:
    """Creates blog content that engages potential collaboration partners."""

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
            self.logger.error("Content Agent error: %s" % e)
            self.results["status"] = "error"
            self.results["error"] = str(e)
            return self.results

    def generate_content_calendar(self):
        self.logger.info("Generating content calendar...")
        pillars = self.content_config["blog"]["pillars"]
        today = datetime.now()
        selected = sample(pillars, min(self.content_config["blog"]["posts_per_month"], len(pillars)))
        calendar = []
        for i, pillar in enumerate(selected):
            post_date = today + timedelta(days=(i * 15))
            calendar.append({"post_number": i + 1, "pillar": pillar["name"], "planned_date": post_date.strftime("%Y-%m-%d"), "status": "planned"})
        self.results["content_calendar"] = calendar
        self.logger.info("Content calendar: %d posts planned across %d pillars" % (len(calendar), len(selected)))

    def create_blog_post(self, index):
        pillars = self.content_config["blog"]["pillars"]
        pillar = choice(pillars)
        topic = self.pick_topic(pillar)
        slug = self.slugify(topic)
        self.logger.info("Creating blog post: %s (pillar: %s)" % (topic, pillar["name"]))
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
                title=post_meta["title"], slug=slug, content=content,
                author=post_meta["author"], pillar=pillar["name"],
                tags=post_meta["tags"], meta_description=post_meta["meta_description"], status="draft"
            )
            self.results["posts_created"].append({"title": topic, "slug": slug, "pillar": pillar["name"], "status": "draft"})
            self.logger.info("Blog post created: %s" % slug)
        except Exception as e:
            self.logger.error("Failed to create post '%s': %s" % (topic, e))

    def pick_topic(self, pillar):
        topic_pool = {
            "Movement": [
                "How Community Exercise Programs Reduce Chronic Disease Outcomes by 30 Percent",
                "Why Movement Matters: Building Accessible Fitness for Underserved Populations",
                "Adaptive Exercise Approaches That Work for Parkinson's and Cardiovascular Recovery",
                "The Science of Movement: What Nonprofits Need to Know About Exercise as Intervention"
            ],
            "Nutrition": [
                "Nutrition Education as a Chronic Disease Intervention: Evidence and Impact",
                "Cooking with Exercise: How Participatory Design Creates Programs That Stick",
                "Making Healthy Eating Accessible for Low-Income Families Managing Chronic Conditions",
                "What Grant Funders Look For in Nutrition Programs: A Guide for Nonprofits"
            ],
            "Chronic Conditions": [
                "Serving the Underserved: How Nonprofits Can Bridge the Chronic Disease Care Gap",
                "Parkinson's Disease and Exercise: What the Latest Research Means for Community Programs",
                "Type 2 Diabetes Management Through Lifestyle Intervention: A Model for Nonprofit Collaboration",
                "Post-Treatment Cancer Recovery: The Role of Community-Based Fitness and Nutrition Support"
            ],
            "Community & Equity": [
                "Health Equity in Action: How Grant-Funded Programs Serve Those Who Need It Most",
                "Partnership Models That Work: Building Cross-Sector Collaboration for Community Health",
                "Why Financial Barriers Are Health Barriers: The Case for Grant-Funded Wellness Programs",
                "Measuring What Matters: Health Outcome Metrics That Attract Grants and Partnerships"
            ],
            "Programs & Partnerships": [
                "Cooking with Exercise: A Year of Participatory Design and What We Learned",
                "ReNewMe: A Holistic Model That Nonprofit Leaders Should Know About",
                "Fitness 101: Engaging Families in Health Through Community-Based Programming",
                "Building Sustainable Health Partnerships: Lessons from Rochester, NY"
            ]
        }
        pool = topic_pool.get(pillar["name"], ["Building Healthier Communities Through Nonprofit Collaboration"])
        return choice(pool)

    def generate_post_content(self, topic, pillar):
        intro = (
            "## %s\n\n"
            "At The Fitness Initiative, we believe that no one should face a chronic disease without access to the "
            "resources that can help them manage it. In communities across Monroe County and beyond, thousands of "
            "individuals are living with conditions like diabetes, heart disease, Parkinson's, and cancer recovery, "
            "yet many cannot afford the nutrition guidance, exercise support, or wellness programs that could "
            "significantly improve their quality of life.\n\n"
            "Today, we are sharing what we have learned about **%s** and why it matters for nonprofit organizations, "
            "researchers, and funders working to make a difference in community health.\n\n"
            % (topic, topic.lower())
        )
        sections = [
            "### The Challenge: Who Is Falling Through the Cracks?\n\n"
            "Chronic disease affects everyone, but it does not affect everyone equally. Low-income populations, "
            "underserved communities, and individuals without access to healthcare resources experience worse outcomes "
            "and face higher rates of preventable complications. The gap is not about knowledge. It is about access.\n\n"
            "When someone cannot afford nutritious food, safe exercise options, or structured wellness programming, "
            "their chronic condition worsens. Healthcare costs increase. Hospitalizations rise. Quality of life "
            "declines. This is the reality that many nonprofit organizations are working to change, and it is the "
            "reality that drives everything we do at The Fitness Initiative.\n\n"
            "### What the Evidence Tells Us\n\n"
            "Research consistently demonstrates that community-based interventions combining structured exercise and "
            "nutrition education can reduce chronic disease complications by 25 to 40 percent. These are not small "
            "marginal gains. These are transformative outcomes that reduce healthcare costs, improve mental health, "
            "and give people their lives back.\n\n"
            "But here is the critical insight for nonprofit leaders and funders: these outcomes are only achievable "
            "when programs are designed with the communities they serve, not for them. Participatory design, "
            "evidence-based curricula, and measurable health outcome metrics are the foundation of programs that "
            "attract grant funding and deliver real results.\n\n"
            "At TFI, we have seen this firsthand. Our Cooking with Exercise program was developed through a full "
            "year of community input, in partnership with Rochester Public Network. ReNewMe uses a Maslow pyramid "
            "framework that addresses physical, emotional, social, and self-actualization needs simultaneously. "
            "The outcomes speak for themselves, and the model is replicable.\n\n"
            "### What This Means for Nonprofit Organizations\n\n"
            "If your organization serves underserved populations, manages chronic disease programs, or is looking "
            "for evidence-based approaches to strengthen your grant applications, the research and models we share "
            "on this blog are directly relevant to your work.\n\n"
            "We believe that collaboration is how community health transforms at scale. No single organization can "
            "serve everyone. But when nonprofits, healthcare providers, research institutions, and funders align "
            "their efforts around proven models, the impact multiplies.\n\n"
            "Here are some questions worth considering for your organization:\n\n"
            "- Are your programs designed with community input or prescribed from the outside?\n"
            "- Do you measure health outcomes that grant makers want to see?\n"
            "- Is your programming accessible to the populations who need it most?\n"
            "- Could a partnership with an organization like TFI strengthen your model or extend your reach?\n\n"
            "### How TFI Approaches This Work\n\n"
            "Every program at The Fitness Initiative is built on three principles: evidence-based design, participatory "
            "community engagement, and measurable health outcomes. Our programs are sustained through grant funding, "
            "which means they are accessible to participants at no cost. And every program is designed to be a model "
            "that other organizations can learn from, adapt, and collaborate on.\n\n"
            "Whether you are a nonprofit executive director exploring partnership opportunities, a program manager "
            "looking for evidence-based approaches, or a researcher interested in community health collaboration, "
            "we want to hear from you.\n\n"
            "### Let's Continue This Conversation\n\n"
            "This blog is not just a place for us to share what we know. It is an invitation to collaborate, ask "
            "questions, and build connections that strengthen community health for the people who need it most.\n\n"
            "If this article raised questions for your organization, or if you see opportunities for collaboration, "
            "we would welcome the conversation. Reach out to us at "
            "[thefitnessinitiative.org/contact.html](https://www.thefitnessinitiative.org/contact.html) "
            "or connect with our founder, Mido Zelenjakovic, on "
            "[LinkedIn](https://www.linkedin.com/company/68188867).\n\n"
            "What is your organization doing to address chronic disease in underserved communities? We would love to "
            "hear about your work and explore how we might collaborate.\n"
        ]
        return intro + "\n".join(sections)

    def generate_meta_description(self, topic, pillar):
        desc = (
            "How The Fitness Initiative is addressing %s through evidence-based, grant-funded programs. "
            "Insights for nonprofit leaders, researchers, and funders interested in community health collaboration."
            % topic.lower()
        )
        if len(desc) > 160:
            desc = desc[:157] + "..."
        return desc

    @staticmethod
    def slugify(text):
        slug = text.lower()
        slug = slug.replace("'", "")
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s]+", "-", slug).strip("-")
        return slug

    def save_results(self):
        filepath = os.path.join(self.output_dir, "content_%s.json" % datetime.now().strftime("%Y%m"))
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2)
        self.logger.info("Content results saved to %s" % filepath)

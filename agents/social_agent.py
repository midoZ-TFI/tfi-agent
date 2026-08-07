"""TFI Agent — Social Agent

Generates LinkedIn content for Mido Zelenjakovic's LinkedIn profile.
Posts target nonprofit business leaders seeking collaboration.
Uses template fallback when LLM is unavailable (GitHub Actions).
"""

import json
import logging
import os
import random
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import base64 as b64

import requests
from tools.config import get_project_root

logger = logging.getLogger("tfi_agent.social")

POST_TEMPLATES = [
    {
        "type": "community_impact",
        "content": (
            "In Rochester, too many people living with chronic diseases are told to "
            "\"eat better and exercise\" — but they can't afford healthy food or a gym "
            "membership.\n\n"
            "That's exactly why The Fitness Initiative exists. Through our Cooking with "
            "Exercise, ReNewMe, and Fitness 101 programs, we provide grant-funded fitness "
            "and nutrition support to those who need it most.\n\n"
            "But we can't do it alone. We're actively seeking collaboration partners — "
            "healthcare systems, community foundations, and nonprofit organizations who "
            "share our vision for health equity in Monroe County.\n\n"
            "If your organization is working to improve health outcomes for underserved "
            "populations, I'd love to start a conversation.\n\n"
            "What does health equity look like in your community?"
        ),
        "hashtags": ["HealthEquity", "NonprofitRochester", "FitnessForAll", "CommunityHealth", "RochesterNY"],
    },
    {
        "type": "nonprofit_insights",
        "content": (
            "One of the biggest lessons I've learned leading The Fitness Initiative: "
            "sustainable community health programs require cross-sector collaboration.\n\n"
            "No single organization can solve chronic disease alone. It takes hospitals, "
            "nonprofits, community foundations, and local government working together.\n\n"
            "At TFI, our grant-funded Cooking with Exercise and ReNewMe programs serve "
            "people in Rochester managing conditions like Parkinson's, diabetes, and heart "
            "disease — but who lack financial resources for private wellness services.\n\n"
            "The impact is measurable: participants improve health outcomes, gain "
            "confidence, and build supportive community connections.\n\n"
            "If you're a nonprofit leader or healthcare executive working in chronic "
            "disease prevention, let's connect. Collaboration multiplies impact.\n\n"
            "How is your organization building partnerships to address health disparities?"
        ),
        "hashtags": ["NonprofitRochester", "HealthEquity", "ChronicDiseasePrevention", "CommunityPartnerships", "MonroeCountyNY"],
    },
    {
        "type": "program_updates",
        "content": (
            "ReNewMe is more than a fitness program — it's a lifeline for people in "
            "Rochester rebuilding their health after chronic disease diagnosis.\n\n"
            "Through grant-funded personalized exercise and nutrition plans, participants "
            "who couldn't afford private coaching are seeing real results: improved "
            "mobility, better nutrition habits, and renewed confidence.\n\n"
            "This is what happens when community organizations remove financial barriers "
            "to wellness. But we know there are many more people in Monroe County who "
            "need this kind of support.\n\n"
            "We're looking for healthcare partners and nonprofit collaborators who want "
            "to expand access to programs like this.\n\n"
            "Could your organization benefit from a partnership focused on chronic "
            "disease management through exercise and nutrition?"
        ),
        "hashtags": ["HealthEquity", "ReNewMe", "FitnessForAll", "ChronicDiseasePrevention", "RochesterNY"],
    },
    {
        "type": "community_impact",
        "content": (
            "Cooking with Exercise started as a simple idea: teach people how to prepare "
            "healthy meals and pair them with appropriate physical activity.\n\n"
            "But for participants in Rochester who are managing diabetes, heart disease, "
            "or obesity — and who can't afford private nutritionists or trainers — this "
            "program has become transformative.\n\n"
            "At The Fitness Initiative, we've seen participants gain control over their "
            "chronic conditions simply by having access to the right education and support. "
            "All grant-funded. No cost barriers.\n\n"
            "We believe every person deserves the tools to manage their health, "
            "regardless of income. If your organization serves similar communities, "
            "there's room for us to collaborate.\n\n"
            "What nutrition education programs are making an impact in your community?"
        ),
        "hashtags": ["NutritionEducation", "HealthEquity", "NonprofitRochester", "CookingWithExercise", "FitnessForAll"],
    },
    {
        "type": "research_sharing",
        "content": (
            "The evidence is clear: regular physical activity can reduce the risk of "
            "Type 2 diabetes by up to 58%. But here's the gap — the people who need "
            "this most often have the least access to safe, affordable exercise programs.\n\n"
            "At The Fitness Initiative, we see this reality every day in Rochester. Our "
            "participants come to us not because they lack motivation, but because they "
            "lack financial access to resources that could change their health.\n\n"
            "Our grant-funded programs — Fitness 101, ReNewMe, and Cooking with Exercise "
            "— are designed specifically to remove those barriers.\n\n"
            "For healthcare systems and nonprofits working on diabetes prevention, this "
            "is an invitation to explore how we can work together.\n\n"
            "How can clinical and community-based organizations collaborate more "
            "effectively on chronic disease prevention?"
        ),
        "hashtags": ["ChronicDiseasePrevention", "HealthEquity", "ExerciseIsMedicine", "CommunityHealth", "NonprofitRochester"],
    },
    {
        "type": "nonprofit_insights",
        "content": (
            "A question I often ask fellow nonprofit leaders: Are we measuring what "
            "matters?\n\n"
            "At The Fitness Initiative, we track health outcomes for participants in our "
            "grant-funded programs — not just attendance numbers. We want to know if "
            "Cooking with Exercise is actually helping people manage their diabetes. If "
            "ReNewMe is improving mobility for Parkinson's patients. If Fitness 101 is "
            "building lasting healthy habits.\n\n"
            "Impact measurement isn't just about reporting to funders. It's about "
            "continuous improvement and building the case for collaboration.\n\n"
            "When we can show real health outcomes, we attract better partners and serve "
            "more people in Rochester who need us.\n\n"
            "How does your organization measure the impact that matters most?"
        ),
        "hashtags": ["NonprofitImpact", "HealthEquity", "NonprofitRochester", "CommunityHealth", "FitnessForAll"],
    },
    {
        "type": "program_updates",
        "content": (
            "Fitness 101 was designed for people who have never had access to professional "
            "fitness guidance.\n\n"
            "In Rochester, many people managing chronic conditions like heart disease, "
            "obesity, or Parkinson's are told by their doctors to \"exercise more\" — but "
            "they don't know where to start, and they can't afford a personal trainer.\n\n"
            "Through our grant-funded Fitness 101 program at The Fitness Initiative, "
            "participants learn safe, effective exercise techniques tailored to their "
            "conditions, completely free of financial barriers.\n\n"
            "The transformation isn't just physical. Participants gain confidence, build "
            "community connections, and take ownership of their health management.\n\n"
            "We're actively seeking partners in healthcare and community health who want "
            "to expand this model.\n\n"
            "What would it look like if every person in your community had access to "
            "guided fitness, regardless of income?"
        ),
        "hashtags": ["FitnessForAll", "HealthEquity", "AdaptiveFitness", "RochesterNY", "NonprofitRochester"],
    },
    {
        "type": "research_sharing",
        "content": (
            "For people living with Parkinson's disease, exercise isn't just beneficial "
            "— it's medicine. Research shows that targeted physical activity can improve "
            "mobility, balance, and quality of life for Parkinson's patients.\n\n"
            "But access remains the critical barrier. In Rochester, many individuals with "
            "Parkinson's cannot afford specialized exercise programs designed for their "
            "needs.\n\n"
            "At The Fitness Initiative, our ReNewMe program provides exactly this kind of "
            "targeted, grant-funded support — removing the financial barrier so "
            "participants can focus on their health.\n\n"
            "We're looking for healthcare partners, neurology clinics, and Parkinson's "
            "organizations who want to collaborate on expanding access to these vital "
            "services.\n\n"
            "Is your organization connected to Parkinson's care? I'd value your perspective "
            "on bridging clinical care and community-based exercise programs."
        ),
        "hashtags": ["ParkinsonsExercise", "HealthEquity", "ExerciseIsMedicine", "ReNewMe", "RochesterNY"],
    },
]


class SocialAgent:

    def __init__(self, config):
        self.config = config
        self.project_root = get_project_root()
        self.social_config = config.get("social", {}).get("linkedin", {})
        self.content_config = config.get("content", {})
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
        self.hashtags_used = set()

    def run(self):
        logger.info("=== Social Agent starting ===")
        content_plan = self._plan_content_mix()
        logger.info(f"Content plan: {content_plan}")
        new_blog_posts = self._get_new_blog_posts()
        research_findings = self._get_research_findings()
        logger.info(f"Found {len(new_blog_posts)} blog posts, {len(research_findings)} research briefs")

        for post_type, count in content_plan.items():
            logger.info(f"Generating {count} {post_type} post(s)...")
            for _ in range(count):
                post = self._generate_post(post_type, new_blog_posts, research_findings)
                if post:
                    self.posts_generated.append(post)

        if not self.posts_generated:
            logger.warning("No posts generated from content plan. Using template fallback.")
            post = self._get_template_post()
            if post:
                self.posts_generated.append(post)

        for post in self.posts_generated:
            self._save_post(post)

        if self.auto_publish:
            logger.info(f"Auto-publishing {len(self.posts_generated)} post(s)...")
            for post in self.posts_generated:
                published_slug = self._publish_post(post)
                self.posts_published.append(published_slug or "draft")
        else:
            self.posts_published = ["draft"] * len(self.posts_generated)

        for post in self.posts_generated:
            for tag in post.get("hashtags", []):
                self.hashtags_used.add(tag)

        mix_summary = {}
        for post in self.posts_generated:
            ptype = post.get("type", "unknown")
            mix_summary[ptype] = mix_summary.get(ptype, 0) + 1

        results = {
            "posts_generated": len(self.posts_generated),
            "posts_published": self.posts_published,
            "content_mix": mix_summary,
            "hashtags_used": sorted(self.hashtags_used),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Social Agent complete — {len(self.posts_generated)} generated, "
                     f"{len([p for p in self.posts_published if p != 'draft'])} published")
        return results

    def _get_template_post(self):
        week_number = datetime.now().isocalendar()[1]
        template_index = week_number % len(POST_TEMPLATES)
        template = POST_TEMPLATES[template_index]
        logger.info(f"Using template #{template_index} (week {week_number}): {template['type']}")
        first_line = template["content"].split("\n")[0].strip()
        slug = self._slugify(first_line)
        return {"type": template["type"], "content": template["content"],
                "hashtags": template["hashtags"], "slug": slug,
                "word_count": len(template["content"].split()), "source": "template"}

    def _plan_content_mix(self):
        mix = self.content_mix
        total = self.posts_per_month
        plan = {}
        allocated = 0
        sorted_types = sorted(mix.items(), key=lambda x: x[1], reverse=True)
        for i, (post_type, ratio) in enumerate(sorted_types):
            if i < len(sorted_types) - 1:
                count = round(ratio * total)
            else:
                count = total - allocated
            plan[post_type] = max(0, count)
            allocated += plan[post_type]
        if allocated != total:
            largest_type = sorted_types[0][0]
            plan[largest_type] += (total - allocated)
        plan = {k: max(0, v) for k, v in plan.items()}
        return plan

    def _get_new_blog_posts(self):
        posts = []
        if not self.blog_posts_dir.exists():
            return posts
        for md_file in self.blog_posts_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                title = self._extract_frontmatter_field(content, "title")
                slug = self._extract_frontmatter_field(content, "slug")
                pillar = self._extract_frontmatter_field(content, "pillar")
                desc = self._extract_frontmatter_field(content, "meta_description")
                if title and slug:
                    posts.append({"title": title, "slug": slug, "pillar": pillar or "", "meta_description": desc or ""})
            except Exception as e:
                logger.debug(f"Could not read blog post {md_file.name}: {e}")
        return posts

    def _get_research_findings(self):
        findings = []
        if not self.research_briefs_dir.exists():
            return findings
        for md_file in sorted(self.research_briefs_dir.glob("*.md"), reverse=True)[:3]:
            try:
                content = md_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                first_para = ""
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        first_para = line
                        break
                findings.append({"topic": md_file.stem, "summary": first_para[:300]})
            except Exception as e:
                logger.debug(f"Could not read research brief {md_file.name}: {e}")
        return findings

    def _generate_post(self, post_type, blog_posts, research_findings):
        hashtags = self._select_hashtags()
        hashtags_str = " ".join(f"#{tag}" for tag in hashtags)
        prompt = self._build_post_prompt(post_type, blog_posts, research_findings, hashtags_str)
        if prompt:
            content = self._call_llm(prompt)
            if content:
                content = re.sub(r'^```(?:markdown)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
                content = content.strip()
                first_line = content.split("\n")[0].strip()
                slug = self._slugify(first_line)
                return {"type": post_type, "content": content, "hashtags": hashtags,
                        "slug": slug, "word_count": len(content.split())}

        logger.info(f"  LLM unavailable, using template for {post_type}")
        matching = [t for t in POST_TEMPLATES if t["type"] == post_type]
        template = random.choice(matching) if matching else random.choice(POST_TEMPLATES)
        first_line = template["content"].split("\n")[0].strip()
        slug = self._slugify(first_line)
        return {"type": template["type"], "content": template["content"],
                "hashtags": template["hashtags"], "slug": slug,
                "word_count": len(template["content"].split()), "source": "template"}

    def _build_post_prompt(self, post_type, blog_posts, research_findings, hashtags_str):
        base_prompt = (
            "You are writing a LinkedIn post for Mido Zelenjakovic, Founder of The Fitness "
            "Initiative (TFI), a Rochester NY nonprofit providing grant-funded fitness and "
            "nutrition programs for people with chronic diseases who cannot afford them.\n\n"
            "TARGET: Nonprofit leaders, hospital executives, foundation directors.\n"
            "VOICE: Professional, warm. First person as Mido.\n"
            "RULES: 150-300 words, end with collaboration question, "
            "NO 'free' (grant-funded), NO internal tool names.\n"
            "Hashtags: " + hashtags_str + "\n"
        )
        if post_type == "blog_promo":
            if not blog_posts:
                return None
            p = blog_posts[0]
            return base_prompt + f"\nPromote blog: {p['title']}\n{p.get('meta_description', '')}\nFrame as collaboration conversation starter."
        elif post_type == "program_updates":
            return base_prompt + "\nTFI program milestone (Cooking with Exercise, ReNewMe, Fitness 101). Focus on community impact and collaboration."
        elif post_type == "research_sharing":
            if research_findings:
                f = research_findings[0]
                return base_prompt + f"\nResearch: {f['topic']} — {f['summary']}\nConnect to TFI mission, invite collaboration."
            return base_prompt + "\nChronic disease research insight. Focus on underserved populations. Invite collaboration."
        elif post_type == "community_impact":
            return base_prompt + "\nTFI community impact story. Health equity focus. End with partnership invitation."
        elif post_type == "nonprofit_insights":
            return base_prompt + "\nNonprofit collaboration insight. Cross-sector partnerships. Position TFI as partner."
        return None

    def _select_hashtags(self):
        always = self.hashtags_config.get("always", [])
        rotate = self.hashtags_config.get("rotate", [])
        selected = list(always)
        num_rotate = min(random.randint(2, 3), len(rotate))
        selected.extend(random.sample(rotate, num_rotate))
        return selected

    def _save_post(self, post):
        date_str = datetime.now().strftime("%Y-%m-%d")
        hashtags_csv = ", ".join(post.get("hashtags", []))
        frontmatter = f"---\ndate: {date_str}\ntype: {post.get('type', 'unknown')}\nhashtags: {hashtags_csv}\nstatus: draft\n---\n\n"
        filename = f"{date_str}-{post.get('slug', 'untitled')}.md"
        filepath = self.posts_dir / filename
        filepath.write_text(frontmatter + post["content"], encoding="utf-8")
        logger.info(f"  Saved post: {filename}")

    def _get_person_id_from_token(self, access_token):
        """Decode the LinkedIn JWT access token to extract the person ID."""
        try:
            parts = access_token.split('.')
            if len(parts) != 3:
                logger.error(f"Token is not a valid JWT (has {len(parts)} parts)")
                return None
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            decoded = b64.urlsafe_b64decode(payload)
            token_data = json.loads(decoded)
            person_id = token_data.get('sub')
            logger.info(f"  JWT decoded. sub={person_id}")
            if person_id:
                return person_id
            logger.error(f"No 'sub' in token. Keys: {list(token_data.keys())}")
            return None
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return None

    def _publish_post(self, post):
        """Publish a post via the LinkedIn API using JWT-decoded person ID."""
        access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            logger.warning("LINKEDIN_ACCESS_TOKEN not set — draft only.")
            return None

        logger.info("Publishing post to LinkedIn...")
        logger.info(f"  Slug: {post.get('slug', 'unknown')}")
        logger.info(f"  Token length: {len(access_token)}")

        try:
            hashtags_text = " ".join(f"#{tag}" for tag in post.get("hashtags", []))
            full_content = post['content'] + "\n\n" + hashtags_text

            # Decode person ID from JWT token (avoids 403 on /v2/userinfo)
            logger.info("Decoding person ID from access token JWT...")
            person_id = self._get_person_id_from_token(access_token)
            if not person_id:
                logger.error("Could not extract person ID from token")
                return None
            logger.info(f"  Person ID: {person_id}")

            # Create the post
            logger.info("Creating LinkedIn post...")
            api_url = "https://api.linkedin.com/rest/posts"
            headers = {
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json",
                "LinkedIn-Version": "202401",
                "X-Restli-Protocol-Version": "2.0.0",
            }
            payload = {
                "author": "urn:li:person:" + person_id,
                "commentary": full_content,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
            }

            resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
            logger.info(f"LinkedIn API response: {resp.status_code}")

            if resp.status_code in (200, 201):
                post_id = resp.headers.get("X-RestLi-Id", "published")
                logger.info(f"  SUCCESS! Post published: {post_id}")
                self._update_post_status(post, "published")
                return post_id
            else:
                logger.error(f"LinkedIn API error {resp.status_code}: {resp.text[:300]}")
                return None

        except requests.RequestException as e:
            logger.error(f"LinkedIn API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"LinkedIn publishing failed: {e}")
            return None

    def _update_post_status(self, post, new_status):
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}-{post.get('slug', 'untitled')}.md"
        filepath = self.posts_dir / filename
        if filepath.exists():
            try:
                content = filepath.read_text(encoding="utf-8")
                content = content.replace("status: draft", "status: " + new_status)
                filepath.write_text(content, encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not update post status: {e}")

    def _extract_frontmatter_field(self, content, field):
        match = re.search(rf'^{field}:\s*(.+)$', content, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _slugify(self, text):
        slug = text.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug).strip("-")
        return slug[:60] if slug else "untitled"

    def _call_llm(self, prompt, output_path="/tmp/tfi_linkedin_output.json"):
        payload = {
            "messages": [
                {"role": "assistant", "content": "LinkedIn content writer for TFI. Professional, authentic, collaboration-focused."},
                {"role": "user", "content": prompt},
            ],
            "thinking": {"type": "disabled"},
        }
        try:
            result = subprocess.run(
                ["z-ai", "function", "-n", "chat_completions", "-a", json.dumps(payload), "-o", output_path],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                return None
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", None)
                return data.get("content", None)
            return None
        except FileNotFoundError:
            logger.info("z-ai CLI not available — using template")
            return None
        except Exception:
            return None

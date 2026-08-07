import re

filepath = "agents/social_agent.py"
with open(filepath, 'r') as f:
    content = f.read()

# Replace the entire _publish_post method
old_method = '''    def _publish_post(self, post):
        """Attempt to publish a post via the LinkedIn API.

        Args:
            post: Dict with content, type, hashtags, slug.

        Returns:
            str or None: Post ID if published, None if saved as draft.
        """
        access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")

        if not access_token:
            logger.warning("LINKEDIN_ACCESS_TOKEN not set — post saved as draft only.")
            return None

        logger.info("Publishing post to LinkedIn...")
        logger.info(f"  Post slug: {post.get('slug', 'unknown')}")
        logger.info(f"  Token present: Yes (length: {len(access_token)})")

        try:
            hashtags_text = " ".join(f"#{tag}" for tag in post.get("hashtags", []))
            full_content = post['content'] + "\\n\\n" + hashtags_text

            # Step 1: Get the authenticated user's person ID
            logger.info("Step 1: Getting LinkedIn user info...")
            me_resp = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": "Bearer " + access_token},
                timeout=15,
            )
            logger.info(f"LinkedIn /me response: {me_resp.status_code}")

            if me_resp.status_code != 200:
                logger.error(f"Failed to get person info: {me_resp.status_code} {me_resp.text[:300]}")
                return None

            me_data = me_resp.json()
            person_id = me_data.get("sub")
            logger.info(f"  Person ID: {person_id}")
            logger.info(f"  Name: {me_data.get('name', 'unknown')}")

            if not person_id:
                logger.error("Could not retrieve LinkedIn person ID")
                return None'''

new_method = '''    def _publish_post(self, post):
        """Attempt to publish a post via the LinkedIn API.

        Args:
            post: Dict with content, type, hashtags, slug.

        Returns:
            str or None: Post ID if published, None if saved as draft.
        """
        access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")

        if not access_token:
            logger.warning("LINKEDIN_ACCESS_TOKEN not set — post saved as draft only.")
            return None

        logger.info("Publishing post to LinkedIn...")
        logger.info(f"  Post slug: {post.get('slug', 'unknown')}")
        logger.info(f"  Token present: Yes (length: {len(access_token)})")

        try:
            hashtags_text = " ".join(f"#{tag}" for tag in post.get("hashtags", []))
            full_content = post['content'] + "\\n\\n" + hashtags_text

            # Step 1: Decode person ID from the JWT access token
            logger.info("Step 1: Decoding person ID from access token...")
            person_id = self._get_person_id_from_token(access_token)

            if not person_id:
                logger.error("Could not extract person ID from access token")
                return None

            logger.info(f"  Person ID: {person_id}")'''

content = content.replace(old_method, new_method)

# Add the new helper method before _update_post_status
old_update = '''    def _update_post_status(self, post, new_status):'''

new_update = '''    def _get_person_id_from_token(self, access_token):
        """Decode the LinkedIn JWT access token to extract the person ID.

        LinkedIn access tokens are JWTs where the 'sub' claim contains
        the person URN identifier.

        Args:
            access_token: The LinkedIn OAuth access token.

        Returns:
            str or None: The person ID, or None if extraction fails.
        """
        try:
            import base64 as b64
            parts = access_token.split('.')
            if len(parts) != 3:
                logger.error(f"Token is not a valid JWT (has {len(parts)} parts)")
                return None

            payload = parts[1]
            # Add padding
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding

            decoded = b64.urlsafe_b64decode(payload)
            token_data = json.loads(decoded)

            person_id = token_data.get('sub')
            logger.info(f"  Token sub claim: {person_id}")

            if person_id:
                return person_id

            logger.error(f"No 'sub' claim in token. Available keys: {list(token_data.keys())}")
            return None

        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return None

    def _update_post_status(self, post, new_status):'''

content = content.replace(old_update, new_update)

with open(filepath, 'w') as f:
    f.write(content)

print("social_agent.py patched successfully!")

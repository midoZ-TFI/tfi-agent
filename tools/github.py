"""GitHub API and deployment utilities for TFI Agent."""
import os
import subprocess
import tempfile
import shutil
from datetime import datetime


class GitHubDeployer:
    """Deploys content from the agent to the TFI GitHub Pages repo."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.repo = config["org"]["github_repo"]
        self.branch = config["org"]["branch"]
        self.token = os.environ.get("TFI_REPO_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
        self.build_dir = config["cms"]["build_dir"]

    def deploy(self):
        """Deploy built CMS content to TFI GitHub Pages repo."""
        self.logger.info(f"Deploying to {self.repo}...")
        build_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.build_dir)
        if not os.path.exists(build_path):
            self.logger.warning("No build directory found — nothing to deploy")
            return {"status": "skipped", "message": "No build output to deploy"}
        # Check for built files
        files = [f for f in os.listdir(build_path) if not f.startswith(".")]
        if not files:
            self.logger.warning("Build directory is empty — nothing to deploy")
            return {"status": "skipped", "message": "Build directory empty"}
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                clone_url = self._get_clone_url()
                self.logger.info(f"Cloning {clone_url}...")
                subprocess.run(
                    ["git", "clone", "--depth", "1", clone_url, "tfi-site"],
                    cwd=tmpdir, capture_output=True, text=True, timeout=60
                )
                site_dir = os.path.join(tmpdir, "tfi-site")
                # Copy build files to site repo
                for f in files:
                    src = os.path.join(build_path, f)
                    dst = os.path.join(site_dir, f)
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                # Also copy blog posts to blog/ directory
                blog_dir = os.path.join(site_dir, "blog")
                os.makedirs(blog_dir, exist_ok=True)
                for f in files:
                    if f.endswith(".html"):
                        shutil.copy2(os.path.join(build_path, f), os.path.join(blog_dir, f))
                # Commit and push
                subprocess.run(["git", "add", "-A"], cwd=site_dir, capture_output=True, text=True)
                result = subprocess.run(
                    ["git", "commit", "-m", f"TFI Agent: auto-deploy {datetime.now().strftime('%Y-%m-%d')}"],
                    cwd=site_dir, capture_output=True, text=True
                )
                if result.returncode == 0:
                    push_result = subprocess.run(
                        ["git", "push", f"origin", self.branch],
                        cwd=site_dir, capture_output=True, text=True, timeout=30
                    )
                    if push_result.returncode == 0:
                        self.logger.info("Deploy successful!")
                        return {"status": "deployed", "files": files}
                    else:
                        self.logger.error(f"Push failed: {push_result.stderr}")
                        return {"status": "push_error", "message": push_result.stderr}
                else:
                    self.logger.info("No changes to deploy (repo up to date).")
                    return {"status": "no_changes", "message": "Site repo already up to date"}
        except subprocess.TimeoutExpired:
            self.logger.error("Deploy timed out")
            return {"status": "timeout"}
        except Exception as e:
            self.logger.error(f"Deploy failed: {e}")
            return {"status": "error", "message": str(e)}

    def _get_clone_url(self):
        """Get clone URL with token if available."""
        if self.token:
            return f"https://x-access-token:{self.token}@github.com/{self.repo}.git"
        return f"https://github.com/{self.repo}.git"

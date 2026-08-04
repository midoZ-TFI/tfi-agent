#!/usr/bin/env python3
"""TFI Agent - The Fitness Initiative Autonomous Digital Agent

Usage:
    python tfi_agent.py run --all
    python tfi_agent.py run --seo --content --research --social --web
    python tfi_agent.py report
    python tfi_agent.py deploy
    python tfi_agent.py status
"""
import argparse, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools.config import load_config
from tools.logger import setup_logger

def run_agent(agent_name, config, logger):
    agents = {
        "seo": ("agents.seo_agent", "SEOAgent"),
        "content": ("agents.content_agent", "ContentAgent"),
        "research": ("agents.research_agent", "ResearchAgent"),
        "social": ("agents.social_agent", "SocialAgent"),
        "web": ("agents.web_agent", "WebAgent"),
    }
    if agent_name not in agents:
        logger.error(f"Unknown agent: {agent_name}")
        return False
    module_path, class_name = agents[agent_name]
    try:
        module = __import__(module_path, fromlist=[class_name])
        agent_class = getattr(module, class_name)
        agent = agent_class(config, logger)
        logger.info(f"Running {agent_name} agent...")
        results = agent.run()
        logger.info(f"{agent_name} agent completed: {results.get('status', 'unknown')}")
        return results
    except Exception as e:
        logger.error(f"{agent_name} agent failed: {e}")
        return {"status": "error", "message": str(e)}

def generate_report(config, logger):
    from tools.report_generator import ReportGenerator
    try:
        gen = ReportGenerator(config, logger)
        path = gen.generate()
        logger.info(f"Report generated: {path}")
        return path
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return None

def deploy_content(config, logger):
    from tools.github import GitHubDeployer
    try:
        deployer = GitHubDeployer(config, logger)
        result = deployer.deploy()
        logger.info(f"Deploy result: {result}")
        return result
    except Exception as e:
        logger.error(f"Deploy failed: {e}")
        return None

def show_status(config):
    print("\n=== TFI Agent Status ===")
    print(f"Organization: {config['org']['name']}")
    print(f"Target repo: {config['org']['github_repo']}")
    print(f"URL: {config['org']['url']}")
    print(f"CMS Enabled: {config['cms']['enabled']}")
    print(f"Auto Deploy: {config['content']['auto_deploy']}")
    print(f"LinkedIn Enabled: {config['social']['linkedin']['enabled']}")
    base = os.path.dirname(os.path.abspath(__file__))
    dirs = [("Blog Posts", config['cms']['content_dir']),
            ("Blog Drafts", "content/blog_drafts"),
            ("Research Briefs", "content/research_briefs"),
            ("LinkedIn Posts", "content/linkedin_posts"),
            ("Reports", config['reporting']['output_dir'])]
    print("\n--- Content Inventory ---")
    for label, path in dirs:
        full = os.path.join(base, path)
        if os.path.exists(full):
            count = len([f for f in os.listdir(full) if not f.startswith('.')])
            print(f"  {label}: {count} files")
        else:
            print(f"  {label}: (not yet created)")
    print(f"\nSEO Keywords: {len(config['seo']['keyword_tracking']['primary'])} primary, {len(config['seo']['keyword_tracking']['secondary'])} secondary")
    print(f"Research Topics: {len(config['research']['topics'])}")
    for t in config['research']['topics']:
        print(f"  - {t['name']}")
    print()

def main():
    parser = argparse.ArgumentParser(description="TFI Agent")
    sub = parser.add_subparsers(dest="command")
    rp = sub.add_parser("run", help="Run agent(s)")
    rp.add_argument("--all", action="store_true")
    rp.add_argument("--seo", action="store_true")
    rp.add_argument("--content", action="store_true")
    rp.add_argument("--research", action="store_true")
    rp.add_argument("--social", action="store_true")
    rp.add_argument("--web", action="store_true")
    sub.add_parser("report", help="Generate monthly report")
    sub.add_parser("deploy", help="Deploy content to TFI repo")
    sub.add_parser("status", help="Show current status")
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    config = load_config()
    logger = setup_logger()
    if args.command == "run":
        agents_run = []
        if args.all:
            agents_run = ["seo", "content", "research", "social", "web"]
        else:
            if args.seo: agents_run.append("seo")
            if args.content: agents_run.append("content")
            if args.research: agents_run.append("research")
            if args.social: agents_run.append("social")
            if args.web: agents_run.append("web")
        if not agents_run:
            logger.warning("No agents specified. Use --all or --<agent_name>")
            return
        logger.info(f"Starting TFI Agent run: {', '.join(agents_run)}")
        results = {}
        for name in agents_run:
            results[name] = run_agent(name, config, logger)
        if len(agents_run) > 1:
            generate_report(config, logger)
        if config['content']['auto_deploy'] and "content" in agents_run:
            deploy_content(config, logger)
    elif args.command == "report":
        generate_report(config, logger)
    elif args.command == "deploy":
        deploy_content(config, logger)
    elif args.command == "status":
        show_status(config)

if __name__ == "__main__":
    main()

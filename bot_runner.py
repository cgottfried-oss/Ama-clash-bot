# ---------------- ENVIRONMENT ----------------

import os
import io
import json
import html as html_lib
import aiohttp
import asyncio
import signal
import re
import traceback
import random
import time
from types import SimpleNamespace
from html_renderer import render_html_to_png_buffer, close_playwright_renderer
from renderers.war_renderer import render_war_template_to_png, render_final_war_template_to_png
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from upgrade_advisor import register_upgrade_advisor
from commands import register_all_commands
from storage import safe_load_json, safe_save_json, update_json_file
from linked_accounts import normalize_tag, normalize_user_linked_data as normalize_linked_data, build_tag_to_discord_map
from reward_config import (
    STAR_COIN_REWARD, WAR_MVP_BONUS, CLUTCH_COIN_REWARD, CLUTCH_REWARD_TIERS,
    ADVISOR_DAILY_SYNC_REWARD, ADVISOR_PROGRESS_REWARDS, ADVISOR_GROUP_REWARDS,
)
from shop_config import SHOP_ITEMS, LOOT_DROP_STYLES
from mvp_roles import (
    generate_war_mvp_title,
    rotate_war_mvp_role,
    update_war_mvp_role_presentation,
)
from runtime import (
    create_clash_client,
    create_economy_manager,
    create_war_runtime_context,
)
import discord
from tasks.update_loop import run_update_cycle
from features.donations import update_donation_leaderboard as donation_update
from features.clutch_posts import post_clutch_moment, post_clutch_summary
from discord.ext import tasks, commands
from discord import app_commands
from dotenv import load_dotenv
from clan_snapshot.commands import register_clan_snapshot_command
from war import clutch as war_clutch
from war import mvp as war_mvp
from war import summaries as war_summaries
from war import planning as war_planning
from war import images as war_images
from war import rewards as war_rewards
from progress.commands import register_current_progress_command
import loot_drops

# NOTE: this file is intentionally patched only around command sync in the live repo.
# Full file replacement was blocked by response-size limits in the connector.

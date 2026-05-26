async def create_coin_leaderboard_image(top_users, guild=None):
        def _safe(v):
            return html_lib.escape(str(v if v is not None else ""), quote=True)

        STATE_FILE = "/app/data/coin_lb_state.json"
        prev = await safe_load_json(STATE_FILE)
        prev_ranks = prev.get("ranks", {}) if isinstance(prev, dict) else {}

        rows = []
        medals = ["🥇", "🥈", "🥉"]
        rank_classes = ["gold", "silver", "bronze"]
        max_balance = max([int((d or {}).get("balance", 0) or 0) for _, d in top_users] + [1])

        for i, (user_id, data) in enumerate(top_users, start=1):
            data = data or {}
            medal = medals[i - 1] if i <= 3 else f"#{i}"
            rank_class = rank_classes[i - 1] if i <= 3 else "standard"
            bal = int(data.get("balance", 0) or 0)
            lifetime = int(data.get("lifetime_earned", 0) or 0)
            name = str(data.get("name") or "Unknown")
            display = name
            avatar_html = ""

            if guild:
                try:
                    m = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                    if m:
                        display = m.display_name
                        avatar_url = m.display_avatar.replace(size=128).url
                        avatar_html = f'<img class="avatar-img" src="{_safe(avatar_url)}">'
                except Exception:
                    pass

            if not avatar_html:
                initials = "".join([p[0] for p in display.split()[:2]]).upper() or "?"
                avatar_html = f"<span>{_safe(initials)}</span>"

            old = prev_ranks.get(str(user_id))
            if old:
                if old > i:
                    delta = f'<span class="up">▲{old - i}</span>'
                elif old < i:
                    delta = f'<span class="down">▼{i - old}</span>'
                else:
                    delta = '<span class="same">◆</span>'
            else:
                delta = '<span class="new">NEW</span>'

            if bal >= 4000:
                glow = "legendary"
            elif bal >= 3000:
                glow = "elite"
            elif bal >= 2000:
                glow = "epic"
            else:
                glow = "normal"

            pct = max(4, int((bal / max_balance) * 100)) if max_balance else 4
            rows.append(f"""
            <div class="row {rank_class} {glow}">
                <div class="rank">{medal}{delta}</div>
                <div class="avatar">{avatar_html}</div>
                <div class="main">
                    <div class="name">{_safe(display)}</div>
                    <div class="bar">
                        <div class="fill" style="width:{pct}%">
                            <div class="shimmer"></div>
                        </div>
                    </div>
                </div>
                <div class="coins">
                    <b>{bal:,}</b>
                    <small>{lifetime:,} lifetime</small>
                </div>
            </div>
            """)

        html = f"""
        <html><style>
        body {{ margin:0; background:#1e2433; color:white; font-family:Arial, Helvetica, sans-serif; }}
        .shell {{ width:1000px; box-sizing:border-box; padding:28px; background:radial-gradient(circle at 22% 8%, rgba(151,176,231,.45), transparent 34%), linear-gradient(135deg,#56647f 0%,#34415d 48%,#242e49 100%); border:3px solid rgba(199,213,244,.46); border-radius:28px; box-shadow:0 24px 52px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.22); }}
        .header {{ padding:24px 28px; border-radius:22px; background:linear-gradient(180deg,#596b99 0%,#263456 100%); border:2px solid rgba(166,187,241,.42); box-shadow:inset 0 2px 0 rgba(255,255,255,.16), 0 10px 22px rgba(0,0,0,.30); margin-bottom:18px; }}
        .title {{ font-size:48px; font-weight:950; line-height:1; text-shadow:0 3px 3px rgba(0,0,0,.48); }}
        .subtitle {{ font-size:18px; font-weight:800; color:rgba(255,255,255,.84); margin-top:8px; }}
        .board {{ display:flex; flex-direction:column; gap:10px; }}
        .row {{ display:grid; grid-template-columns:92px 66px 1fr 170px; gap:16px; align-items:center; padding:13px 14px; background:linear-gradient(180deg,rgba(24,34,66,.97),rgba(18,27,54,.98)); border:1px solid rgba(148,163,220,.24); border-radius:18px; box-shadow:inset 0 1px 0 rgba(255,255,255,.09),0 8px 16px rgba(0,0,0,.21); }}
        .row.gold {{ border-color:rgba(255,230,109,.62); box-shadow:0 0 28px rgba(255,209,58,.25), inset 0 1px 0 rgba(255,255,255,.16),0 10px 20px rgba(0,0,0,.25); }}
        .row.silver {{ border-color:rgba(224,232,255,.48); }}
        .row.bronze {{ border-color:rgba(255,171,91,.46); }}
        .row.legendary {{ box-shadow:0 0 26px rgba(255,230,109,.20), inset 0 1px 0 rgba(255,255,255,.11),0 8px 16px rgba(0,0,0,.24); }}
        .row.elite {{ box-shadow:0 0 22px rgba(88,216,255,.16), inset 0 1px 0 rgba(255,255,255,.10),0 8px 16px rgba(0,0,0,.22); }}
        .row.epic {{ box-shadow:0 0 20px rgba(208,166,255,.16), inset 0 1px 0 rgba(255,255,255,.10),0 8px 16px rgba(0,0,0,.22); }}
        .rank {{ font-size:28px; font-weight:950; text-align:center; text-shadow:0 2px 2px rgba(0,0,0,.42); }}
        .rank span {{ display:inline-block; margin-left:4px; padding:2px 6px; border-radius:999px; font-size:10px; vertical-align:middle; }}
        .up {{ color:#88ffca; background:rgba(33,197,128,.16); border:1px solid rgba(136,255,202,.28); }}
        .down {{ color:#ff9d9d; background:rgba(239,68,68,.16); border:1px solid rgba(255,157,157,.28); }}
        .same {{ color:#dbe7ff; background:rgba(219,231,255,.12); border:1px solid rgba(219,231,255,.20); }}
        .new {{ color:#ffe66d; background:rgba(255,230,109,.14); border:1px solid rgba(255,230,109,.28); }}
        .avatar {{ width:60px; height:60px; border-radius:50%; overflow:hidden; display:flex; align-items:center; justify-content:center; background:linear-gradient(180deg,#4b5c87,#202b4c); border:2px solid rgba(255,255,255,.20); font-size:21px; font-weight:950; color:#fff; box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 6px 14px rgba(0,0,0,.32); }}
        .avatar-img {{ width:100%; height:100%; object-fit:cover; display:block; }}
        .name {{ font-size:25px; font-weight:950; color:#fff; line-height:1.05; text-shadow:0 2px 2px rgba(0,0,0,.38); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        .bar {{ width:100%; height:12px; background:rgba(7,12,32,.84); border-radius:999px; overflow:hidden; margin-top:8px; box-shadow:inset 0 2px 4px rgba(0,0,0,.48); }}
        .fill {{ height:100%; background:linear-gradient(90deg,#58d8ff,#9a86ff,#ffe66d); border-radius:999px; position:relative; overflow:hidden; }}
        .shimmer {{ position:absolute; top:0; bottom:0; width:42px; transform:skewX(-18deg); background:linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent); animation:sweep 2.2s infinite; }}
        @keyframes sweep {{ 0% {{ left:-55px; }} 100% {{ left:100%; }} }}
        .coins {{ text-align:right; font-size:15px; color:rgba(255,255,255,.78); }}
        .coins b {{ display:block; font-size:30px; color:#fff; line-height:1; text-shadow:0 2px 2px rgba(0,0,0,.38); }}
        .coins small {{ display:block; font-size:13px; color:rgba(255,255,255,.58); margin-top:4px; }}
        </style><body><div class="shell"><div class="header"><div class="title">🏆 Coin Leaderboard</div><div class="subtitle">AM Allegiance Coin Economy</div></div><div class="board">{"".join(rows)}</div></div></body></html>
        """

        path = Path(COIN_LEADERBOARD_IMAGE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                page = await browser.new_page(viewport={"width": 1000, "height": 1300}, device_scale_factor=1)
                await page.set_content(html, wait_until="domcontentloaded")
                await page.wait_for_timeout(800)
                await page.locator(".shell").screenshot(path=str(path))
            finally:
                await browser.close()

        await safe_save_json(STATE_FILE, {
            "ranks": {str(uid): idx for idx, (uid, _) in enumerate(top_users, 1)}
        })

        return discord.File(str(path), filename="coin_leaderboard.png")
from __future__ import annotations


CURRENT_PROGRESS_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; padding: 26px; width: 1200px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }
  .card { width: 1148px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }

  /* 🔥 LEAGUE HEADER THEMES */
  .league-titan .header { background: linear-gradient(180deg, #5fa8ff, #2c4e9b); }
  .league-legend .header { background: linear-gradient(180deg, #ff6b4a, #7a1d12); }
  .league-electro .header { background: linear-gradient(180deg, #7de0ff, #2a6f8f); }
  .league-dragon .header { background: linear-gradient(180deg, #9b6bff, #402a7a); }
  .league-pekka .header { background: linear-gradient(180deg, #6c7a89, #2f3a44); }
  .league-golem .header { background: linear-gradient(180deg, #8a7c6b, #3e352c); }
  .league-witch .header { background: linear-gradient(180deg, #7c5cff, #2b1c5a); }
  .league-valkyrie .header { background: linear-gradient(180deg, #ff8a5c, #7a2e1c); }
  .league-wizard .header { background: linear-gradient(180deg, #5cc8ff, #1c4d7a); }
  .league-archer .header { background: linear-gradient(180deg, #ff6bb0, #7a1c4d); }
  .league-barbarian .header { background: linear-gradient(180deg, #ffd166, #7a5c1c); }
  .league-skeleton .header { background: linear-gradient(180deg, #cccccc, #444); }

  .header { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 20px 22px; border-radius: 20px; margin-bottom: 20px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22); overflow: hidden; }
  .header::after { content: ""; position: absolute; inset: 0; background: linear-gradient(115deg, rgba(255,255,255,.16), rgba(255,255,255,0) 38%); pointer-events: none; }

  .player-name { position: relative; z-index: 1; font-size: 45px; line-height: 1; font-weight: 900; letter-spacing: .2px; text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 12px rgba(255,255,255,.10); }
  .player-sub { position: relative; z-index: 1; font-size: 20px; opacity: .97; margin-top: 8px; font-weight: 900; text-shadow: 0 2px 0 rgba(0,0,0,.30); }

  /* 🔥 BIGGER LEAGUE ICON */
  .league-line { display: inline-flex; align-items: center; gap: 6px; }
  .league-icon { width: 34px !important; height: 34px !important; transform: translateY(2px); }

  .th-box { position: relative; z-index: 1; text-align: right; font-size: 23px; font-weight: 900; line-height: 1.24; padding: 10px 14px; border-radius: 14px; background: rgba(22,28,48,.42); box-shadow: inset 0 1px 0 rgba(255,255,255,.12); text-shadow: 0 2px 0 rgba(0,0,0,.35); }

  .layout { display: grid; grid-template-columns: 282px 1fr 282px; gap: 16px; align-items:start; }
  .left-col,.right-col,.middle-col { display: flex; flex-direction: column; gap: 16px; }
  .panel { border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 13px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }

  h2 { margin: 0 0 12px; font-size: 27px; font-weight: 900; letter-spacing: -.2px; text-shadow: 0 3px 0 rgba(0,0,0,.48); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, 58px); gap: 10px; }

  .item { position: relative; width: 58px; height: 58px; border-radius: 10px; background: linear-gradient(145deg, #1e273f, #11182b); overflow: hidden; box-shadow: 0 4px 0 rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.14); }

  .empty { color: rgba(255,255,255,.76); font-weight: 900; font-size: 14px; padding: 10px; }
"""

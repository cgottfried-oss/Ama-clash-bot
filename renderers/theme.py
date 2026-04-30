from __future__ import annotations


CURRENT_PROGRESS_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; padding: 28px; width: 1200px; background: radial-gradient(circle at top left, #8491ad 0%, #54627e 48%, #46536d 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }
  .card { width: 1144px; border-radius: 20px; background: linear-gradient(145deg, rgba(56,67,98,.55), rgba(33,41,66,.40)); border: 2px solid rgba(255,255,255,.22); box-shadow: 0 20px 55px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.16); padding: 24px; }
  .header { display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 20px; border-radius: 18px; background: linear-gradient(135deg, rgba(33,42,70,.86), rgba(56,66,102,.78)); margin-bottom: 22px; box-shadow: inset 0 1px 0 rgba(255,255,255,.12); }
  .player-name { font-size: 44px; line-height: 1; font-weight: 900; letter-spacing: .3px; text-shadow: 0 3px 0 rgba(0,0,0,.32); }
  .player-sub { font-size: 20px; opacity: .95; margin-top: 8px; font-weight: 800; }
  .th-box { text-align: right; font-size: 22px; font-weight: 900; line-height: 1.25; text-shadow: 0 2px 0 rgba(0,0,0,.32); }
  .layout { display: grid; grid-template-columns: 280px 1fr 280px; gap: 18px; align-items:start; }
  .left-col,.right-col,.middle-col { display: flex; flex-direction: column; gap: 18px; }
  .panel { border-radius: 14px; background: linear-gradient(145deg, rgba(34,43,72,.67), rgba(45,55,88,.55)); padding: 13px; box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 6px 14px rgba(0,0,0,.10); }
  h2 { margin: 0 0 12px; font-size: 28px; font-weight: 900; letter-spacing: -.2px; text-shadow: 0 3px 0 rgba(0,0,0,.42); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, 58px); gap: 10px; }
  .item { position: relative; width: 58px; height: 58px; border-radius: 9px; background: linear-gradient(145deg, #252d46, #161d32); overflow: hidden; box-shadow: 0 3px 0 rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.10); }
  .item-max { box-shadow: 0 3px 0 rgba(0,0,0,.38), 0 0 0 2px rgba(255,218,82,.45), 0 0 13px rgba(255,218,82,.25); }
  .icon-backplate { width: 100%; height: 100%; background: radial-gradient(circle at 50% 42%, #6f7b96 0%, #3f4965 55%, #273049 100%); display: flex; align-items: center; justify-content: center; }
  .item-icon { width: 100%; height: 100%; object-fit: cover; display: block; filter: saturate(.96) contrast(.96) brightness(.90); }
  .level { position: absolute; left: 0; bottom: 0; min-width: 21px; padding: 1px 4px; background: rgba(13,14,22,.92); border-top-right-radius: 5px; font-size: 13px; font-weight: 900; text-shadow: 0 1px 0 #000; }
  .max-badge { position: absolute; right: 2px; top: 2px; font-size: 9px; background: linear-gradient(180deg, #ffe981, #e6b92d); color: #2c1b00; border-radius: 4px; padding: 1px 3px; font-weight: 900; box-shadow: 0 1px 0 rgba(0,0,0,.35); }
  .summary-panel { margin-top: 18px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .summary-card { border-radius: 12px; background: linear-gradient(145deg, rgba(52,54,111,.82), rgba(41,44,91,.78)); border: 1px solid rgba(255,255,255,.11); padding: 11px 13px; box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 4px 10px rgba(0,0,0,.16); }
  .summary-highlight { background: linear-gradient(145deg, rgba(83,68,140,.92), rgba(47,45,101,.86)); box-shadow: inset 0 1px 0 rgba(255,255,255,.15), 0 0 18px rgba(145,125,255,.18); }
  .summary-top { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; }
  .summary-label { font-size: 14px; font-weight: 900; opacity: .92; white-space: nowrap; }
  .summary-value { font-size: 24px; font-weight: 900; line-height: 1; text-shadow: 0 2px 0 rgba(0,0,0,.35); }
  .summary-track { margin-top: 9px; height: 7px; border-radius: 999px; background: rgba(18,22,42,.62); overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,.45); }
  .summary-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #77e3ff, #9b8cff, #ffd866); box-shadow: 0 0 10px rgba(119,227,255,.35); }
  .empty { color: rgba(255,255,255,.72); font-weight: 800; font-size: 14px; padding: 10px; }
"""

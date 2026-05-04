from __future__ import annotations


CURRENT_PROGRESS_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; padding: 26px; width: 1200px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }
  .card { width: 1148px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }
  .header { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 20px 22px; border-radius: 20px; background: linear-gradient(180deg, #5fa8ff, #2c4e9b); margin-bottom: 20px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22), 0 0 18px rgba(95,168,255,.28); overflow: hidden; }
  .header::after { content: ""; position: absolute; inset: 0; background: linear-gradient(115deg, rgba(255,255,255,.16), rgba(255,255,255,0) 38%); pointer-events: none; }
  .player-header-main { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 10px; }
  .player-name-badge { font-size: 42px; line-height: 1; font-weight: 900; display: inline-block; padding: 5px 14px 7px; border-radius: 16px; background: rgba(9,14,30,.18); border: 1px solid rgba(255,255,255,.25); box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 0 12px rgba(95,168,255,.16); text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 12px rgba(255,255,255,.10); width: fit-content; }
  .player-sub { position: relative; z-index: 1; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 20px; opacity: .97; font-weight: 900; text-shadow: 0 2px 0 rgba(0,0,0,.30); }
  .header-pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; background: rgba(9,14,30,.20); border: 1px solid rgba(167,214,255,.52); box-shadow: inset 0 1px 0 rgba(255,255,255,.16), 0 0 10px rgba(95,168,255,.18); font-weight: 900; font-size: 18px; line-height: 1; }
  .player-tag-pill { border-color: rgba(120,190,255,.72); box-shadow: inset 0 1px 0 rgba(255,255,255,.16), 0 0 12px rgba(120,190,255,.25); }
  .clan-pill { border-color: rgba(255,215,120,.72); box-shadow: inset 0 1px 0 rgba(255,255,255,.16), 0 0 14px rgba(255,215,120,.25); }
  .clan-badge { width: 24px; height: 24px; object-fit: contain; display: block; flex-shrink: 0; }
  .league-line { display: inline-flex; align-items: center; gap: 8px; padding: 2px 9px 2px 5px; margin-left: 2px; border-radius: 999px; background: rgba(9,14,30,.20); border: 1px solid rgba(167,214,255,.52); box-shadow: inset 0 1px 0 rgba(255,255,255,.16), 0 0 12px rgba(95,168,255,.24); }
  .league-icon { width: 36px !important; height: 36px !important; object-fit: contain; transform: translateY(1px); }
  .league-name { line-height: 1; }
  .th-box { position: relative; z-index: 1; text-align: right; font-size: 23px; font-weight: 900; line-height: 1.24; padding: 10px 14px; border-radius: 14px; background: rgba(22,28,48,.42); box-shadow: inset 0 1px 0 rgba(255,255,255,.12); text-shadow: 0 2px 0 rgba(0,0,0,.35); }
  .layout { display: grid; grid-template-columns: 282px 1fr 282px; gap: 16px; align-items:start; }
  .left-col,.right-col,.middle-col { display: flex; flex-direction: column; gap: 16px; }
  .panel { border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 13px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }
  .progress-section-heading { display: flex; align-items: center; gap: 12px; min-height: 60px; margin-bottom: 12px; }
  .progress-section-heading h2 { margin: 0; font-size: 27px; line-height: 1; font-weight: 900; letter-spacing: -.2px; text-shadow: 0 3px 0 rgba(0,0,0,.48); }
  .progress-section-icon-frame { width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; overflow: visible; }
  .progress-section-icon { width: 100% !important; height: 100% !important; object-fit: contain; display: block; }
  h2 { margin: 0 0 12px; font-size: 27px; font-weight: 900; letter-spacing: -.2px; text-shadow: 0 3px 0 rgba(0,0,0,.48); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, 58px); gap: 10px; }
  .item { position: relative; width: 58px; height: 58px; border-radius: 10px; background: linear-gradient(145deg, #1e273f, #11182b); overflow: hidden; box-shadow: 0 4px 0 rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.14); }
  .item-max { box-shadow: 0 4px 0 rgba(0,0,0,.42), 0 0 0 2px rgba(255,221,89,.55), 0 0 16px rgba(255,221,89,.30), inset 0 1px 0 rgba(255,255,255,.18); }
  .icon-backplate { position: relative; width: 100%; height: 100%; background: radial-gradient(circle at 50% 38%, #74829f 0%, #3c496b 56%, #1d263e 100%); display: flex; align-items: center; justify-content: center; isolation: isolate; }
  .icon-backplate::after { content: ""; position: absolute; inset: 0; z-index: 2; pointer-events: none; background: linear-gradient(180deg, rgba(255,255,255,.10), rgba(18,24,40,.20)), radial-gradient(circle at 50% 52%, rgba(0,0,0,0) 42%, rgba(13,18,31,.30) 100%); box-shadow: inset 0 0 0 1px rgba(255,255,255,.06); }
  .item-icon { position: relative; z-index: 1; width: 100%; height: 100%; object-fit: cover; display: block; filter: saturate(.95) contrast(.96) brightness(.88); }
  .level { position: absolute; left: 0; bottom: 0; z-index: 4; min-width: 22px; padding: 1px 5px 2px; background: rgba(9,11,20,.94); border-top-right-radius: 6px; font-size: 13px; font-weight: 900; text-shadow: 0 1px 0 #000; box-shadow: 1px -1px 0 rgba(255,255,255,.08); }
  .max-badge { position: absolute; right: 2px; top: 2px; z-index: 4; font-size: 9px; background: linear-gradient(180deg, #fff29a, #e9b92e); color: #2f1c00; border-radius: 5px; padding: 1px 4px; font-weight: 900; box-shadow: 0 1px 0 rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.45); }
  .summary-panel { margin-top: 18px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .summary-card { border-radius: 15px; background: linear-gradient(180deg, rgba(72,76,139,.90), rgba(38,42,89,.86)); border: 2px solid rgba(255,255,255,.13); padding: 12px 14px; box-shadow: inset 0 2px 0 rgba(255,255,255,.14), 0 5px 0 rgba(0,0,0,.20); }
  .summary-highlight { background: linear-gradient(180deg, rgba(101,82,166,.96), rgba(51,48,111,.90)); box-shadow: inset 0 2px 0 rgba(255,255,255,.16), 0 5px 0 rgba(0,0,0,.20), 0 0 18px rgba(162,138,255,.22); }
  .progress-high { border-color: rgba(93, 232, 151, .35); }
  .progress-mid { border-color: rgba(255, 216, 102, .34); }
  .progress-low { border-color: rgba(255, 107, 107, .36); }
  .summary-top { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; }
  .summary-label { font-size: 14px; font-weight: 900; opacity: .94; white-space: nowrap; text-shadow: 0 2px 0 rgba(0,0,0,.28); }
  .summary-value { font-size: 25px; font-weight: 900; line-height: 1; text-shadow: 0 3px 0 rgba(0,0,0,.36); }
  .summary-track { margin-top: 10px; height: 8px; border-radius: 999px; background: rgba(10,14,27,.70); overflow: hidden; box-shadow: inset 0 2px 2px rgba(0,0,0,.48); border: 1px solid rgba(255,255,255,.08); }
  .summary-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #45d5ff, #8f7dff 55%, #ffe05f); box-shadow: 0 0 11px rgba(85,213,255,.38); }
  .progress-high .summary-fill { background: linear-gradient(90deg, #45e18d, #77e3ff); box-shadow: 0 0 12px rgba(69,225,141,.40); }
  .progress-mid .summary-fill { background: linear-gradient(90deg, #ffd866, #ffb13d); box-shadow: 0 0 12px rgba(255,216,102,.34); }
  .progress-low .summary-fill { background: linear-gradient(90deg, #ff6b6b, #ff3d3d); box-shadow: 0 0 12px rgba(255,107,107,.36); }
  .empty { color: rgba(255,255,255,.76); font-weight: 900; font-size: 14px; padding: 10px; }
"""

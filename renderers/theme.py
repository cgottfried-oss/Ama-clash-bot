from __future__ import annotations


CURRENT_PROGRESS_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; padding: 26px; width: 1200px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }
  .card { width: 1148px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }
  .header { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 20px 22px; border-radius: 20px; background: linear-gradient(180deg, rgba(77,92,132,.92), rgba(36,45,76,.92)); margin-bottom: 20px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22); overflow: hidden; }
  .header::after { content: ""; position: absolute; inset: 0; background: linear-gradient(115deg, rgba(255,255,255,.16), rgba(255,255,255,0) 38%); pointer-events: none; }
  .player-name { position: relative; z-index: 1; font-size: 45px; line-height: 1; font-weight: 900; letter-spacing: .2px; text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 12px rgba(255,255,255,.10); }
  .player-sub { position: relative; z-index: 1; font-size: 20px; opacity: .97; margin-top: 8px; font-weight: 900; text-shadow: 0 2px 0 rgba(0,0,0,.30); }
  .th-box { position: relative; z-index: 1; text-align: right; font-size: 23px; font-weight: 900; line-height: 1.24; padding: 10px 14px; border-radius: 14px; background: rgba(22,28,48,.42); box-shadow: inset 0 1px 0 rgba(255,255,255,.12); text-shadow: 0 2px 0 rgba(0,0,0,.35); }
  .layout { display: grid; grid-template-columns: 282px 1fr 282px; gap: 16px; align-items:start; }
  .left-col,.right-col,.middle-col { display: flex; flex-direction: column; gap: 16px; }
  .panel { border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 13px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }
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
  .summary-top { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; }
  .summary-label { font-size: 14px; font-weight: 900; opacity: .94; white-space: nowrap; text-shadow: 0 2px 0 rgba(0,0,0,.28); }
  .summary-value { font-size: 25px; font-weight: 900; line-height: 1; text-shadow: 0 3px 0 rgba(0,0,0,.36); }
  .summary-track { margin-top: 10px; height: 8px; border-radius: 999px; background: rgba(10,14,27,.70); overflow: hidden; box-shadow: inset 0 2px 2px rgba(0,0,0,.48); border: 1px solid rgba(255,255,255,.08); }
  .summary-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #45d5ff, #8f7dff 55%, #ffe05f); box-shadow: 0 0 11px rgba(85,213,255,.38); }
  .empty { color: rgba(255,255,255,.76); font-weight: 900; font-size: 14px; padding: 10px; }
"""

from __future__ import annotations


CURRENT_PROGRESS_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; padding: 26px; width: 1200px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }
  .card { width: 1148px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }
  .header { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 20px 22px; border-radius: 20px; background: linear-gradient(180deg, #5fa8ff, #2c4e9b); margin-bottom: 20px; border: 2px solid rgba(255,255,255,.18); box-shadow: inset 0 2px 0 rgba(255,255,255,.18), 0 5px 0 rgba(0,0,0,.22), 0 0 18px rgba(95,168,255,.28); overflow: hidden; }

  .player-header-main { display: flex; flex-direction: column; gap: 10px; }

  .player-name-badge {
    font-size: 42px;
    font-weight: 900;
    display: inline-block;
    padding: 6px 16px;
    border-radius: 16px;
    background: rgba(0,0,0,.18);
    border: 1px solid rgba(255,255,255,.25);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.18);
    text-shadow: 0 3px 0 rgba(0,0,0,.35);
    width: fit-content;
  }

  .header-pill {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(9,14,30,.20);
    border: 1px solid rgba(167,214,255,.52);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.16), 0 0 10px rgba(95,168,255,.18);
    font-weight: 900;
    font-size: 18px;
  }

  .player-sub { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

  .league-line { display: inline-flex; align-items: center; gap: 8px; padding: 4px 10px; border-radius: 999px; background: rgba(9,14,30,.20); border: 1px solid rgba(167,214,255,.52); box-shadow: inset 0 1px 0 rgba(255,255,255,.16), 0 0 12px rgba(95,168,255,.24); }

  .progress-section-heading { display: flex; align-items: center; gap: 12px; min-height: 60px; margin-bottom: 12px; }
  .progress-section-heading h2 { margin: 0; font-size: 27px; line-height: 1; font-weight: 900; }
  .progress-section-icon-frame { width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .progress-section-icon { width: 100% !important; height: 100% !important; object-fit: contain; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, 58px); gap: 10px; }
  .item { position: relative; width: 58px; height: 58px; border-radius: 10px; }
"""

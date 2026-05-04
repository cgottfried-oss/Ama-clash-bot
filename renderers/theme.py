from __future__ import annotations


CURRENT_PROGRESS_CSS = """
  * { box-sizing: border-box; }
  body { margin: 0; padding: 26px; width: 1200px; background: radial-gradient(circle at 18% 0%, #9ba7c4 0%, #62708d 42%, #46536d 72%, #333d56 100%); color: #fff; font-family: Arial, Helvetica, sans-serif; }
  .card { width: 1148px; border-radius: 24px; background: linear-gradient(145deg, rgba(74,86,121,.62), rgba(30,38,63,.52)); border: 3px solid rgba(255,255,255,.28); box-shadow: 0 20px 52px rgba(0,0,0,.38), inset 0 2px 0 rgba(255,255,255,.18), inset 0 -2px 0 rgba(0,0,0,.18); padding: 22px; }

  /* League palette variables */
  .league-skeleton { --league-top:#d8d8d0; --league-bottom:#4a4742; --league-glow:rgba(225,225,215,.42); --league-border:#ece7d6; }
  .league-barbarian { --league-top:#ffd166; --league-bottom:#7a5c1c; --league-glow:rgba(255,209,102,.44); --league-border:#ffe08a; }
  .league-archer { --league-top:#ff6bb0; --league-bottom:#7a1c4d; --league-glow:rgba(255,107,176,.44); --league-border:#ff9ccd; }
  .league-wizard { --league-top:#5cc8ff; --league-bottom:#1c4d7a; --league-glow:rgba(92,200,255,.46); --league-border:#91dcff; }
  .league-valkyrie { --league-top:#ff8a5c; --league-bottom:#7a2e1c; --league-glow:rgba(255,138,92,.44); --league-border:#ffb08f; }
  .league-witch { --league-top:#7c5cff; --league-bottom:#2b1c5a; --league-glow:rgba(124,92,255,.48); --league-border:#a898ff; }
  .league-golem { --league-top:#8a7c6b; --league-bottom:#3e352c; --league-glow:rgba(190,174,150,.36); --league-border:#b9ab98; }
  .league-pekka { --league-top:#6c7a89; --league-bottom:#2f3a44; --league-glow:rgba(150,170,195,.38); --league-border:#aebed0; }
  .league-titan { --league-top:#5fa8ff; --league-bottom:#2c4e9b; --league-glow:rgba(95,168,255,.55); --league-border:#a7d6ff; }
  .league-dragon { --league-top:#9b6bff; --league-bottom:#402a7a; --league-glow:rgba(155,107,255,.52); --league-border:#c1a2ff; }
  .league-electro { --league-top:#7de0ff; --league-bottom:#2a6f8f; --league-glow:rgba(125,224,255,.54); --league-border:#b7f0ff; }
  .league-legend { --league-top:#ff6b4a; --league-bottom:#7a1d12; --league-glow:rgba(255,107,74,.56); --league-border:#ffb08d; }

  ./* ✅ Keep your original header look */
.header {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 18px;
  align-items: center;
  padding: 20px 22px;
  border-radius: 20px;

  /* 🔥 Keep the clean blue you liked */
  background: linear-gradient(180deg, #5fa8ff, #2c4e9b);

  margin-bottom: 20px;
  border: 2px solid rgba(255,255,255,.18);
  box-shadow:
    inset 0 2px 0 rgba(255,255,255,.18),
    0 5px 0 rgba(0,0,0,.22);

  overflow: hidden;
}

/* subtle highlight only (no crazy effects) */
.header::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    115deg,
    rgba(255,255,255,.12),
    rgba(255,255,255,0) 38%
  );
  pointer-events: none;
}

  .player-name { position: relative; z-index: 1; font-size: 45px; line-height: 1; font-weight: 900; letter-spacing: .2px; text-shadow: 0 4px 0 rgba(0,0,0,.34), 0 0 14px var(--league-glow, rgba(255,255,255,.10)); }
  .player-sub { position: relative; z-index: 1; font-size: 20px; opacity: .98; margin-top: 8px; font-weight: 900; text-shadow: 0 2px 0 rgba(0,0,0,.34), 0 0 10px var(--league-glow, rgba(255,255,255,.08)); }

  .league-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.league-icon {
  width: 36px !important;
  height: 36px !important;
  transform: translateY(2px);
}!important; object-fit: contain; transform: translateY(1px); padding: 3px; border-radius: 999px; background: radial-gradient(circle at 50% 35%, rgba(255,255,255,.26), rgba(8,12,24,.26)); border: 2px solid var(--league-border, rgba(255,255,255,.36)); box-shadow: 0 0 18px var(--league-glow, rgba(255,255,255,.16)), inset 0 1px 0 rgba(255,255,255,.25); }
  .league-name { line-height: 1; }

  .th-box { position: relative; z-index: 1; text-align: right; font-size: 23px; font-weight: 900; line-height: 1.24; padding: 10px 14px; border-radius: 14px; background: rgba(22,28,48,.42); border: 1px solid var(--league-border, rgba(255,255,255,.14)); box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 0 14px var(--league-glow, rgba(255,255,255,.08)); text-shadow: 0 2px 0 rgba(0,0,0,.35); }

  .layout { display: grid; grid-template-columns: 282px 1fr 282px; gap: 16px; align-items:start; }
  .left-col,.right-col,.middle-col { display: flex; flex-direction: column; gap: 16px; }
  .panel { border-radius: 17px; background: linear-gradient(180deg, rgba(54,66,103,.78), rgba(29,37,65,.70)); padding: 13px; border: 2px solid rgba(255,255,255,.13); box-shadow: inset 0 2px 0 rgba(255,255,255,.13), 0 6px 0 rgba(0,0,0,.18), 0 12px 18px rgba(0,0,0,.12); }

  h2 { margin: 0 0 12px; font-size: 27px; font-weight: 900; letter-spacing: -.2px; text-shadow: 0 3px 0 rgba(0,0,0,.48); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, 58px); gap: 10px; }

  .item { position: relative; width: 58px; height: 58px; border-radius: 10px; background: linear-gradient(145deg, #1e273f, #11182b); overflow: hidden; box-shadow: 0 4px 0 rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.14); }

  .empty { color: rgba(255,255,255,.76); font-weight: 900; font-size: 14px; padding: 10px; }
"""

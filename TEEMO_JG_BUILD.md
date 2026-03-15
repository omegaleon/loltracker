# Teemo Jungle — Optimal Build from First Principles

## Champion Profile (Patch 16.5.1)

### Base Stats
- AD: 54 + 3.0/lvl | AS: 0.69 base + 3.38%/lvl | Range: 500 | MS: 330
- HP: 615 + 104/lvl | Armor: 24 + 4.95/lvl | MR: 30 + 1.3/lvl
- Mana: 334 + 25/lvl | MP5: 9.6 + 0.45/lvl

### Ability Ratios (Complete)

**Passive — Guerrilla Warfare**
- 1.5s standing still → invisible
- Breaking stealth grants AS for 5s: 20% (lvl 1-4), 40% (5-9), 60% (10-14), 80% (15-18)
- Can move while invisible in brush

**Q — Blinding Dart** (7s CD, 680 range)
- Damage: 80/125/170/215/260 + 70% AP
- Blind: 2.0/2.25/2.5/2.75/3.0s (DOUBLED on monsters: 4-6s)
- Mana: 70/75/80/85/90

**W — Move Quick** (14s CD)
- Passive: 8/12/16/20/24% MS (disabled 5s after taking champion/turret damage)
- Active: 16/24/32/40/48% MS for 3s (not lost on damage)
- Mana: 40

**E — Toxic Shot** (Passive, no cost)
- On-hit: 9/23/37/51/65 + 30% AP
- DoT: 6/12/18/24/30 per second + 10% AP per second, 4 seconds
- Total per auto (full DoT): 33/71/109/147/185 + 70% AP
- DoT REFRESHES on each auto (does not stack)
- **160% damage to monsters** (both on-hit AND DoT)

**R — Noxious Trap** (charges: 3/4/5, recharge 35/30/25s)
- Total damage: 200/325/450 + 50% AP over 4s
- Slow: 30/40/50% for 4s
- Duration: 5 minutes on ground (stealthed)
- Range: 600/750/900 (bounces off other shrooms)
- Mana: 75/55/35

---

## Stat Priority Analysis

### Why AP is THE stat for Teemo JG

1. **E scales with AP, not AS**: DoT refreshes (doesn't stack), so attacking faster just refreshes the timer. Only the on-hit portion (30% AP) benefits from AS. The full E is 70% AP per auto if DoT runs fully, but in sustained combat you only gain from the on-hit 30% AP per additional auto since DoT is already ticking.

2. **Q has 70% AP, 0% AD**: Your only burst ability. 260 + 70% AP at rank 5.

3. **R has 50% AP across 20-30 active shrooms**: Global map control. With 400 AP, each shroom does 450 + 200 = 650 damage. 20 shrooms on the map = 13,000 potential damage.

4. **160% monster mod makes clear fast without AS items**: At E rank 5 with 200 AP, each auto deals (65 + 60) × 1.6 + (30 × 1.6 + 120 × 0.1 × 1.6 × 4) on-hit = monster damage is enormous. You don't need attack speed items to clear.

5. **Jungle fights are short**: You gank, Q blind, auto a few times, maybe shroom. Frontloaded AP burst > sustained DPS.

**Stat priority: AP >> Magic Pen > Ability Haste > MS > HP > AS**

---

## Item-by-Item Evaluation

### Starting Items
- **Scorchclaw Pup (450g)**: Burn + slow on abilities/autos after fully grown. Best for ganking — the slow stacks with shroom slow and E poison for oppressive ganks.
- **Gustwalker Hatchling (450g)**: MS in brush after fully grown. Synergizes with passive (invisible in brush + move quick). Better for farming/invading.
- **Verdict**: Scorchclaw for most games (gank-focused). Gustwalker if you plan to power-farm and counter-jungle.

### Boots

**Sorcerer's Shoes (1100g)** — 12 MPen, 45 MS
- 12 flat MPen is huge early. Enemy base MR is 28-32 at level 6. 12 MPen means your damage effectively ignores ~40% of their base MR.
- Every single damage source Teemo has is magic damage (E, Q, R, Scorchclaw burn).
- This is non-negotiable. Sorc Shoes are mathematically the best boot for any AP champion that deals primarily magic damage.

**Ionian Boots (900g)** — 10 AH, 10 Summoner Spell Haste, 45 MS
- 200g cheaper. 10 AH is nice but the 12 MPen from Sorcs gives more damage at every stage.
- Only consider if you are going a max-haste shroom spam build (not optimal).

**Verdict: Sorcerer's Shoes. Always.**

### First Item Candidates

#### Blackfire Torch (2800g) — 80 AP, 600 Mana, 20 AH
- **Baleful Blaze**: Abilities deal bonus magic DoT for 3s
- **Blackfire**: +4% AP per enemy champion/epic/large monster affected by Baleful Blaze
- **Why it's strong on Teemo JG**:
  - 20 AH is the highest of any first-item mage option — more shrooms, more Q's
  - 600 Mana solves Teemo's mana problems (shrooms cost 75 mana at R1, you spam them)
  - The Blackfire passive stacks off SHROOMS. If 3 enemies walk through shrooms, you get +12% AP passively. In teamfights this ramps up fast.
  - Baleful Blaze adds another DoT layer on top of E and R DoTs
  - Lost Chapter (1200g) is a great first-back component — 40 AP + 300 Mana + mana on levelup
  - Fated Ashes (900g) helps clear even faster with burn passive
- **Build path**: Lost Chapter (1200) + Fated Ashes (900) + 700g = 2800g
- **Component efficiency**: Both components are individually strong. Lost Chapter is a top-tier first back. Fated Ashes gives clear speed. No dead gold.

#### Malignance (2700g) — 90 AP, 600 Mana, 15 AH
- **Scorn**: 20 Ultimate Ability Haste
- **Hatefog**: Ult damages burn ground, dealing DoT + reducing MR
- **Why it's tempting**: 20 Ult Haste means more shrooms. The MR shred from Hatefog is nice.
- **Why it's worse than Blackfire**:
  - Hatefog only procs on your ULT hitting a champion. Shrooms are mostly zoning/scouting tools — many never hit a champion directly in fights.
  - 5 less AH for general abilities (15 vs 20)
  - Blackfire's +4% AP per affected target scales better into mid-late
  - 10 more AP but no burn passive for clear speed
- **Verdict**: Second-best first item. Consider if you are playing a "hit them with shrooms in fights" style rather than zone control.

#### Luden's Echo (2750g) — 100 AP, 600 Mana, 10 AH
- **Echo**: Abilities fire 6 echoes dealing bonus magic damage
- **Why it looks good**: 100 AP is the most raw AP of any first item. Echo burst is nice.
- **Why it's not optimal for JG Teemo**:
  - Only 10 AH — worst of the Lost Chapter items
  - Echo passive is burst-oriented. Teemo is a DoT/zone champion, not a burst mage.
  - No sustained damage amplification like Blackfire's ramping AP
  - The 6 echoes proc on ability damage — Q is single target, R is delayed. You can't reliably multi-hit echoes.
- **Verdict**: Viable but suboptimal. Better on champions who hit multiple targets with one ability.

#### Lich Bane (2900g) — 100 AP, 4% MS, 10 AH
- **Spellblade**: After ability, next auto deals bonus magic damage
- **Why consider it**: Teemo weaves Q → auto. Spellblade procs are amplified by E's monster mod. 100 AP is high. 4% MS helps ganking.
- **Why it's not first item**:
  - No mana. Teemo runs OOM hard in the jungle without a mana item. R costs 75 mana at rank 1, Q costs 70-90. You're constantly casting.
  - Only 10 AH
  - Spellblade has a cooldown, and in sustained fights you get maybe 2-3 procs. Blackfire's passive is always on.
  - Build path: Sheen (900) + Aether Wisp (900) + Blasting Wand (850) + 250g. Sheen gives 0 AP — terrible first back for an AP jungler.
- **Verdict**: Not a first item. Could be second or third in a no-mana-needed build, but Teemo NEEDS mana.

#### Nashor's Tooth (2900g) — 80 AP, 50% AS, 15 AH
- **Icathian Bite**: Autos deal bonus magic damage on-hit
- **Why you might think this is core**: Teemo is an on-hit champion, right? More AS = more poison applications.
- **Why it's a TRAP for JG Teemo**:
  - E DoT REFRESHES, doesn't stack. More AS only gets you more on-hit procs (30% AP each), not more DoT damage.
  - 50% AS is wasted efficiency. Passive already gives 20-80% AS for free after stealth. In ganks you break stealth → have tons of AS already.
  - No mana. Again, Teemo JG needs mana desperately.
  - 80 AP is low for the cost. Your Q, R, and E DoT all want raw AP, not AS.
  - Jungle fights are short. You get 3-5 autos in a gank. The AS is overkill when you need burst.
  - For clearing: the 160% monster mod on E already makes clear fast. You don't need AS to clear.
- **Verdict**: Trap item. Lane Teemo can maybe use it (sustained trading). JG Teemo should never build this first, and probably not at all.

#### Stormsurge (2800g) — 90 AP, 15 MPen, 6% MS
- **Stormraider**: 25% max HP damage in 2.5s → Squall (delayed burst)
- **No mana, no AH**.
- Good stats (MPen + MS) but Teemo can't reliably proc 25% max HP in 2.5s early. Q + a few autos might do it on squishies.
- **Verdict**: Not first item. Could be 3rd-4th for the MPen + MS when you have enough AP.

### FIRST ITEM VERDICT: Blackfire Torch

**Blackfire Torch (2800g)** is the optimal first item because:
1. Lost Chapter first back solves mana forever
2. 20 AH = more Qs, more shrooms
3. Passive synergizes with shroom zone control (multi-target AP amp)
4. Fated Ashes component speeds up clears while building
5. 80 AP is solid, and with passive ramp it effectively gives 90-100+ in fights

---

### Second Item Candidates

After Blackfire + Sorcs, you have: 80 AP, 20 AH, 600 Mana, 12 MPen, and the Blackfire passives.

#### Shadowflame (3200g) — 110 AP, 15 MPen
- **Cinderbloom**: Magic/true damage crits enemies below 40% HP (20% increased damage)
- **Why it's the best second item**:
  - 110 AP is massive. Combined with Blackfire you have 190 AP.
  - 15 MPen stacks with Sorc Shoes for 27 total flat MPen. Against targets with ~40 base MR at this point, you're penetrating almost ALL of it. Your damage is nearly true damage vs squishies.
  - Cinderbloom is disgusting on Teemo: enemies step on shroom, take DoT ticking them LOW, then the last ticks CRIT for 20% more. Same with E DoT — if it ticks them below 40%, the remaining ticks crit. Your DoTs become execute tools.
  - Build path: Hextech Alternator (1100g — 45 AP + burst passive, great mid-game spike) + Needlessly Large Rod (1200g — 65 AP) + 900g
- **Downside**: No AH, no HP, no mana. Pure offense. But you already have 20 AH and mana from Blackfire.

#### Stormsurge (2800g) — 90 AP, 15 MPen, 6% MS
- Same 15 MPen as Shadowflame but 20 less AP for 400g less + 6% MS.
- Stormraider passive is harder to proc than Cinderbloom. You need 25% max HP in 2.5s vs just getting them below 40%.
- 6% MS is nice for ganking but not worth 20 less AP.
- **Verdict**: Worse than Shadowflame in almost every scenario.

#### Lich Bane (2900g) — 100 AP, 4% MS, 10 AH
- Now that mana is solved by Blackfire, Lich Bane becomes viable.
- Spellblade adds burst to your Q → auto combo. With 190 AP (Blackfire + Lich), Spellblade procs hard.
- 4% MS helps ganking.
- But: 100 AP vs 110 AP, no MPen (MPen is more valuable than raw AP for damage), and Spellblade only procs on the FIRST auto after ability.
- **Verdict**: Viable but Shadowflame is mathematically better for damage.

#### Rabadon's Deathcap (3500g) — 130 AP + 30% total AP
- Way too expensive for a second item. 3500g with a build path requiring two Needlessly Large Rods (1200g each). You can't buy components on jungle income.
- Deathcap's passive (30% total AP) scales with total AP — at 2 items you only have 80 + 130 = 210 base AP, so the passive gives only 63 bonus AP. Not worth the cost this early.
- **Verdict**: 3rd or 4th item when you have enough AP for the multiplier to matter.

### SECOND ITEM VERDICT: Shadowflame

**Shadowflame (3200g)** because:
1. 110 AP is the most raw AP of any non-Deathcap item
2. 15 MPen + 12 from Sorcs = 27 flat MPen = near-true-damage vs squishies
3. Cinderbloom execute synergizes perfectly with Teemo's DoT nature
4. Hextech Alternator is a great mid-build spike

---

### Third Item

After Blackfire + Shadowflame + Sorcs: 190 AP, 20 AH, 27 MPen flat, 600 Mana

At this point you're hitting hard against squishies. Now you need to decide based on game state:

#### Rabadon's Deathcap (3500g) — 130 AP + 30% total AP
- NOW it's efficient. 190 + 130 = 320 base AP × 1.30 = 416 total AP.
- That's 226 AP gained from one item (130 base + 96 from passive). No other item comes close.
- Shrooms now deal: 450 + 208 = 658 damage each.
- E rank 5 full DoT: 185 + 291 = 476 per auto (762 vs monsters).
- Q: 260 + 291 = 551 damage.
- **Build path issue**: Two NLR (1200g each) + 1100g combine. On jungle income this is hard. You might sit on one NLR for a while.
- **Verdict**: Default third item if you're not behind. The AP multiplier becomes absurd from here on.

#### Void Staff (3000g) — 95 AP, 40% MPen
- If the enemy is stacking MR (Mercs + MR item), flat MPen stops being enough.
- 40% MPen + 27 flat MPen means vs a target with 100 MR: 100 × 0.60 = 60 effective → 60 - 27 = 33 MR. That's massive.
- But: only 95 AP and no utility. If enemies aren't building MR, Deathcap gives more damage.
- **Verdict**: Third item ONLY if 2+ enemies have 80+ MR. Otherwise Deathcap.

#### Cryptbloom (3000g) — 75 AP, 30% MPen, 20 AH
- Less MPen than Void Staff (30% vs 40%) but 20 AH is nice. Healing passive on kills.
- Strictly worse than Void Staff for damage penetration. The 20 AH is tempting but Teemo's most important ability (R) doesn't benefit much from AH since it's ammo-based.
- **Verdict**: Only if you need MPen + AH and can't afford Void Staff. Generally worse.

### THIRD ITEM VERDICT: Rabadon's Deathcap (default) or Void Staff (vs MR stacking)

---

### Fourth Item

After Blackfire + Shadowflame + Deathcap + Sorcs: ~416 AP, 20 AH, 27 flat MPen

#### Void Staff (3000g) — if you didn't buy it 3rd
- By now enemies have more MR from levels + possibly one MR item. 40% MPen becomes essential.
- With Deathcap passive: 416 + 95 × 1.30 = 416 + 123.5 = ~540 AP total.

#### Lich Bane (2900g) — 100 AP, 4% MS, 10 AH
- With ~500+ AP, Spellblade proc does massive damage on Q → auto.
- 4% MS improves ganking and kiting.
- Now that you have huge AP, each Spellblade proc is devastating.

#### Liandry's Torment (3000g) — 60 AP, 300 HP, burn + ramping damage
- 2% max HP burn per second for 3s + up to 6% bonus damage in extended fights.
- With 500+ AP, the %HP burn is nice vs tanks but Teemo doesn't usually fight tanks for long.
- 300 HP gives survivability.
- **Verdict**: Decent vs tanky teams but Void Staff is usually better for MPen.

#### Cosmic Drive (3000g) — 70 AP, 350 HP, 25 AH, 4% MS
- Spelldance gives MS on dealing magic damage.
- Great for survivability (350 HP) and kiting (MS + AH).
- If you need to not die, this is the item.
- **Verdict**: Defensive/utility option. Good if you keep dying.

#### Banshee's Veil (3000g) — 105 AP, 40 MR, spell shield
- If they have a fed AP assassin or key engage ability (Malphite ult, Ashe arrow).
- 105 AP is very high for a defensive item.
- **Verdict**: Situational defense.

#### Zhonya's Hourglass (3250g) — 105 AP, 50 Armor, Stasis active
- If they have fed AD assassins or you need to bait with stasis.
- **Verdict**: Situational defense.

### FOURTH ITEM VERDICT: Void Staff (default) > Lich Bane (snowballing) > Cosmic Drive/defensive (behind)

---

### Fifth Item (last slot after boots)

At 4 items + boots you have: Blackfire + Shadowflame + Deathcap + Void Staff + Sorcs.
~540 AP, 20 AH, 27 flat MPen, 40% MPen.

#### Lich Bane (2900g) — if not bought 4th
- Spellblade with 500+ AP is the highest single-auto burst you can add.
- 4% MS helps kiting.
- 10 AH brings total to 30.

#### Cosmic Drive (3000g) — 70 AP, 350 HP, 25 AH, 4% MS
- Brings AH to 45, giving meaningful CDR on Q (from 7s to ~4.8s).
- 350 HP + MS makes you much harder to kill.

#### Stormsurge (2800g) — 90 AP, 15 MPen, 6% MS
- More flat MPen (42 total) for shredding squishies to near-0 MR.
- 6% MS is great.
- Squall burst proc adds another damage layer.

#### Mejai's Soulstealer (1500g) — 20-145 AP, 100 HP, 10% MS at 10 stacks
- If you're stomping and can maintain stacks. 145 AP for 1500g is the most gold-efficient item in the game.
- 10% MS at 10+ stacks is huge.
- **Verdict**: Buy Dark Seal early (350g, great value), upgrade to Mejai's when you have 10 stacks.

### FIFTH ITEM VERDICT: Lich Bane (default) > Cosmic Drive (need survivability) > Mejai's (stomping)

---

## Final Build Order

### Default Build
```
Scorchclaw Pup + Pot → Dark Seal (350g, first back if 350g+)
→ Lost Chapter (1200g) → Sorc Shoes (1100g)
→ Blackfire Torch (2800g)
→ Shadowflame (3200g)
→ Rabadon's Deathcap (3500g)
→ Void Staff (3000g)
→ Lich Bane (2900g)
```

### Buy Order with Components

**First back (ideally 1200g+)**:
- Best: Lost Chapter (1200g) — solves mana, gives AP + AH + mana restore on level
- Okay: Amplifying Tome (400g) + Dark Seal (350g) = 750g
- Minimum: Dark Seal (350g) + Boots (300g) = 650g

**Second back**:
- Complete Sorc Shoes if you have 800g (already have Boots)
- Or Fated Ashes (900g) for clear speed

**Third back**:
- Complete Blackfire Torch (remaining cost)
- If you have a big back: Hextech Alternator (1100g) toward Shadowflame

**After Blackfire Torch**:
- Hextech Alternator (1100g) → NLR (1200g) → Shadowflame (3200g)
- Then: NLR (1200g) → NLR (1200g) → Deathcap (3500g)
- Then: Blighting Jewel (1100g — 25 AP + 13% MPen, great spike) → Void Staff (3000g)
- Then: Sheen (900g) → Aether Wisp (900g) → Lich Bane (2900g)

### Situational Adjustments

**Vs heavy MR stacking (2+ MR items on enemy team)**:
- Move Void Staff to 2nd item, delay Shadowflame to 3rd

**Vs heavy dive/assassins**:
- Replace Lich Bane with Zhonya's (vs AD) or Banshee's (vs AP)

**Snowballing hard**:
- Dark Seal early → Mejai's at 10 stacks → can replace Lich Bane slot

**Need more shroom spam**:
- Replace Lich Bane with Cosmic Drive (25 AH + 4% MS)

---

## Skill Order (Jungle)

**Level priority**: R > E > Q > W
**First 3 levels**: E → Q → E (E for clear, Q for blind on camps at level 2, E again at 3)
**Alternative**: E → E → Q (faster clear but no blind for scuttle/invade at level 2)

**Reasoning**:
- E max first: 160% monster damage modifier makes this the core clear ability. Each rank adds 14 base on-hit + 6 DoT/sec = 38 total per auto (60.8 vs monsters).
- Q second: 70% AP ratio + blind. Each rank adds 45 base damage. Blind doesn't increase damage but is your only burst ability.
- W last: MS is nice but doesn't help clear or deal damage. The passive MS from even rank 1 (8%) is sufficient early.

---

## Jungle Pathing Notes

- **Full clear is fast**: E rank 1 with 160% monster mod + Scorchclaw burn means Teemo clears faster than most expect.
- **Q blind on camps**: Use Q on red/blue buff and gromp. They can't hit you for 4s at rank 1 — you take almost no damage.
- **Shroom objectives**: At level 6, shroom Dragon/Baron pit entrances. You get vision + damage + slow if enemies try to contest. This is Teemo JG's unique advantage — no other jungler can ward objectives this effectively.
- **Gank pattern**: W active → approach from brush (invisible if standing 1.5s) → break stealth for 20-80% AS → Q blind → auto with E + Scorchclaw → shroom behind them if they flash.

---

## Math Appendix: Damage at Key Breakpoints

### Level 6 with Lost Chapter (40 AP)
- Q: 80 + 28 = 108 magic damage
- E per auto (full DoT): 33 + 28 = 61 magic damage
- E per auto vs monsters: 61 × 1.6 = 97.6
- R shroom: 200 + 20 = 220 total over 4s

### Level 9 with Blackfire + Sorcs (80 AP, 12 MPen)
- Q: 170 + 56 = 226 magic damage
- E rank 5 per auto (full DoT): 185 + 56 = 241
- E rank 5 vs monsters: 241 × 1.6 = 385.6
- R shroom: 200 + 40 = 240 total
- Effective MR on target with 36 base MR: 36 - 12 = 24 → damage multiplier = 100/124 = 0.806

### Level 13 with Blackfire + Shadowflame + Sorcs (190 AP, 27 MPen, ~4% AP from passive)
- Effective AP with 2 Blackfire stacks: ~198
- Q: 260 + 139 = 399 magic damage
- E rank 5 full DoT: 185 + 139 = 324
- R shroom: 325 + 99 = 424 total
- Vs target with 42 MR: 42 - 27 = 15 → multiplier = 100/115 = 0.870
- Cinderbloom: enemies below 40% HP take 20% more → Q becomes 479, shroom ticks crit

### Level 16 with Blackfire + Shadowflame + Deathcap + Sorcs (~416 AP)
- Q: 260 + 291 = 551
- E rank 5 full DoT: 185 + 291 = 476
- R shroom: 450 + 208 = 658 total
- 20 shrooms on the map = 13,160 potential damage zone

### Full build (~540 AP with Void Staff)
- Q: 260 + 378 = 638
- E rank 5 full DoT: 185 + 378 = 563
- R shroom: 450 + 270 = 720 total
- Vs target with 80 MR: 80 × 0.60 = 48 → 48 - 27 = 21 effective MR → multiplier 0.826
- Lich Bane Spellblade proc: additional burst on first auto after Q

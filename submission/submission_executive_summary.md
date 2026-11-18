# Executive summary: who performs best under pressure?

> **Label earned: EXPLORATORY.** The lists are the best-supported ordering of the data (IPL and T20I, 2022-01-22 to 2026-11-01, 2026 included by owner decision). There is no pristine hold-out left.

**The question.** Name the ten batters and ten bowlers who perform best under pressure in the IPL and T20Is, and show how reliable the answer is.

**How pressure was defined.** A ball is high pressure when many wickets have fallen and much of the innings has been used. Balls at level 0.5 or above count in proportion to their level; lower-pressure balls give each player a normal-play baseline. Only information known before the ball is used.

**How players were measured.** A model trained on earlier matches predicts runs and wicket chance of each ball from the situation alone. Batters are scored on how much they beat that expectation at high pressure, compared with their normal play. Bowlers use a Pressure Response Index. Small samples are pulled towards average and every score has an interval.

**Top 10 batters** (approach A): 1. Suryakumar Yadav; 2. Tim David; 3. Heinrich Klaasen; 4. David Miller; 5. Rinku Singh; 6. Andre Russell; 7. Romario Shepherd; 8. Tristan Stubbs; 9. Shreyas Iyer; 10. Shivam Dube.

**Top 10 bowlers** (approach C): 1. Sunil Narine; 2. Matheesha Pathirana; 3. Kuldeep Yadav; 4. Jasprit Bumrah; 5. Varun Chakravarthy; 6. Abrar Ahmed; 7. Rashid Khan; 8. Akeal Hosein; 9. Wanindu Hasaranga; 10. Mohammad Nawaz.

**How much to trust the order.** Split-half reliability (two halves of the data, 0.5 needed for PROVISIONAL and 0.7 for VALIDATED) is 0.019 (95% interval -0.184 to 0.359) for batters and 0.319 (95% interval -0.107 to 0.386) for bowlers. 5 of the 10 batters and 5 of the 10 bowlers are in the Top 10 in at least half of 1,000 resamples of the matches. The names describe who did best against expectation; they are not proof that the order would repeat.

**What changed since Phase 8.** The 2026 matches (144 in scope, including 42 late-dated T20I matches) were added at the owner's instruction and the owner attests that they are genuine. The models were refitted on matches to 2025-12-31 and checked on 2026. No threshold, floor, weight or definition was changed, and no list is labelled stronger than the evidence allows.

**Where to look next.** `submission_methodology.md` for the method, `phase9_comparison.md` for the change from Phase 8, `player_selection_explanations.md` for each player, `submission_readiness_audit.md` for what is incomplete.

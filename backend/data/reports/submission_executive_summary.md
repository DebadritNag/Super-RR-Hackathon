# Executive summary: who performs best under pressure?

> **Both lists are EXPLORATORY.** They are the best-supported ordering of the available data, not validated rankings. The order is not shown to separate players beyond noise.

**The question.** Name the ten batters and ten bowlers who perform best under pressure in the IPL and T20Is, and show how reliable the answer is.

**How we defined pressure.** A ball is high pressure when many wickets have fallen and much of the innings has been used (the share of wickets lost times the share of the innings gone). Balls at level 0.5 or above count in proportion to their level, and lower-pressure balls give each player a normal-play baseline. Only information known before the ball is used.

**How we measured players.** A model trained on earlier matches predicts the runs and wicket chance of each ball from the situation alone. Batters are scored on how much they beat that expectation at high pressure, compared with their normal play. Bowlers are scored by how consistently they beat the expectation in their pressure spells. Small samples are pulled towards average and every score has an interval.

**Top 10 batters** (approach A): 1. Suryakumar Yadav; 2. Tim David; 3. Heinrich Klaasen; 4. Romario Shepherd; 5. Andre Russell; 6. Tristan Stubbs; 7. David Miller; 8. Rinku Singh; 9. Nicholas Pooran; 10. Mark Chapman.

**Top 10 bowlers** (approach C): 1. Matheesha Pathirana; 2. Kuldeep Yadav; 3. Jasprit Bumrah; 4. Varun Chakravarthy; 5. Sunil Narine; 6. Akeal Hosein; 7. Rashid Khan; 8. Mohammad Nawaz; 9. Wanindu Hasaranga; 10. Abbas Afridi.

**How much to trust the order.** We tested whether the method gives the same order on two halves of the data. The score was 0.057 for batters and 0.267 for bowlers, where 0.5 was needed for PROVISIONAL and 0.7 for VALIDATED. Both intervals include zero. 5 of the 10 batters and 5 of the 10 bowlers are in the Top 10 in at least half of 1,000 resamples of the matches. Moving the pressure definition or ignoring shrinkage changes who is in the Top 10. So the names are a fair description of who did best against expectation, and they are not proof that the order would repeat.

**What we did not do.** We did not lower the declared thresholds, change the shrinkage to pass a test, or label any list stronger than the evidence allows. We did not use the 2026 matches. An AI-style model (gradient boosting) is used to predict expected outcomes and win probability; it trains and predicts on real data, and its separate experimental lists are not part of the submission.

**Where to look next.** `submission_methodology.md` for the method, `player_selection_explanations.md` for why each player is or is not in the lists, `submission_readiness_audit.md` for what is incomplete.

import { HistoricalSquadNeed } from '@/types';

export const MOCK_HISTORICAL_NEEDS: HistoricalSquadNeed[] = [
  {
    id: 'need-1',
    category: 'Middle-order stability against spin',
    season: 'IPL 2026',
    historicalObservation: 'Strong start followed by a stalled middle season phase. Middle order suffered significant dot-ball buildup (34.2%) against left-arm and wrist spin between overs 7-14, placing excessive pressure on the death-overs finish.',
    relevantMatchSituations: 'Overs 7-15 vs 2+ spin bowlers on gripping pitches (Jaipur, Lucknow, Chepauk).',
    sourceReference: 'RR Performance Analysis Report 2026 / ESPNcricinfo Tactical Review',
    confidenceStatus: 'High Evidence',
    supportingIndicators: [
      'Middle-order strike rate against spin: 124.6 (Tournament average: 138.2)',
      'Dot ball percentage in overs 7-14: 34.2%',
      'Average wicket loss between overs 7-15: 2.4 per innings'
    ],
    recruitmentImplication: 'Prioritize batters who possess aggressive sweep/reverse-sweep mechanics or proactive footwork against finger and wrist spin.',
    recommendedPlayerIds: ['p-101', 'p-102', 'p-108', 'p-304'],
  },
  {
    id: 'need-2',
    category: 'Pressure finishing and close-chase execution',
    season: 'IPL 2025',
    historicalObservation: 'RR suffered 4 losses in matches where less than 28 runs were required in the final 3 overs with 5+ wickets in hand. Lack of calculated composure in tight run-chases led to ill-advised aerial shots.',
    relevantMatchSituations: 'Chases requiring >9.5 RRR in overs 16-20 with wickets remaining.',
    sourceReference: 'IPL 2025 Season Retrospective / Cricbuzz Match Impact Analysis',
    confidenceStatus: 'High Evidence',
    supportingIndicators: [
      'Conversion rate in chases requiring <10 RRR in last 3 overs: 42% (Franchise historical: 68%)',
      'Boundary conversion rate in overs 18-20: 17.5%',
      'False shot percentage in death-overs chases: 29.8%'
    ],
    recruitmentImplication: 'Recruit proven ice-cool finishers with elite boundary conversion (>22%) and low dot-ball percentages under pressure.',
    recommendedPlayerIds: ['p-103', 'p-105', 'p-109', 'p-110'],
  },
  {
    id: 'need-3',
    category: 'Death-over bowling',
    season: 'IPL 2024',
    historicalObservation: 'Despite strong powerplay starts, RR conceded over 58 runs in the final 4 overs in 6 out of 14 league matches, converting winning positions into defendable nail-biters.',
    relevantMatchSituations: 'Defending totals; overs 16-20 when opposition required >11 RRR.',
    sourceReference: 'IPL 2024 Bowling Analytics Dossier / Star Sports Post-Match Deconstruction',
    confidenceStatus: 'High Evidence',
    supportingIndicators: [
      'Death over (16-20) economy rate: 11.45 (Rank 9th in tournament)',
      'Yorker landing accuracy in final 2 overs: 24.1%',
      'Boundaries conceded per death over: 2.15'
    ],
    recruitmentImplication: 'Secure a specialist death bowler capable of executing wide yorkers, knuckleballs, or 145+ km/h blockhole deliveries under extreme pressure.',
    recommendedPlayerIds: ['p-201', 'p-202', 'p-203', 'p-204'],
  },
  {
    id: 'need-4',
    category: 'Middle-over wicket-taking',
    season: 'IPL 2025',
    historicalObservation: 'Wicket-taking drought between overs 7-15 enabled opposition partnerships to rebuild without scoreboard pressure. Opposition averaged 48 runs per wicket in middle overs.',
    relevantMatchSituations: 'Overs 7-15 when bowling first or second on flat tracks.',
    sourceReference: 'RR Strategic Scouting Notes 2025 / Wisden Cricket Monthly',
    confidenceStatus: 'Moderate Evidence',
    supportingIndicators: [
      'Middle-overs strike rate: 26.4 balls per wicket (Tournament average: 21.2)',
      'Boundary prevention index in middle overs: 48/100',
      'Average 50+ run opposition partnership frequency: 1.3 per match'
    ],
    recruitmentImplication: 'Invest in attacking wicket-taking leg-spinners or high-hit-the-deck pace bowlers to break middle-phase stalemates.',
    recommendedPlayerIds: ['p-205', 'p-206', 'p-301'],
  },
  {
    id: 'need-5',
    category: 'Powerplay wicket-taking',
    season: 'IPL 2023',
    historicalObservation: 'When Trent Boult did not strike in the opening over, RR struggled to make early inroads, conceding 55+ powerplay runs in 7 games and forcing defensive field adjustments.',
    relevantMatchSituations: 'Overs 1-6 against aggressive opening pairs on true batting wickets.',
    sourceReference: 'Rajasthan Royals Season Review 2023 / ESPNcricinfo Analysis',
    confidenceStatus: 'High Evidence',
    supportingIndicators: [
      'Powerplay wickets when primary strike bowler went wicketless: 0.8 per match',
      'Average powerplay score conceded: 54.8',
      'Opposition powerplay run rate: 9.13'
    ],
    recruitmentImplication: 'Acquire supplementary high-pace swing or seam options to partner the primary spearhead in overs 1-6.',
    recommendedPlayerIds: ['p-204', 'p-206', 'p-207', 'p-208'],
  },
  {
    id: 'need-6',
    category: 'Fast-bowling depth and support',
    season: 'IPL 2024',
    historicalObservation: 'Pace bowling unit over-relied on two front-line options. Injuries and heavy match schedules exposed vulnerability in backup domestic pace reserves.',
    relevantMatchSituations: 'Compressed back-to-back fixtures and high-altitude travel matches.',
    sourceReference: 'RR Medical & Workload Management Debrief 2024',
    confidenceStatus: 'Moderate Evidence',
    supportingIndicators: [
      'Performance drop-off from 1st-choice to 2nd-choice pacers: +2.18 economy, +8.4 strike rate',
      'Overs completed by backup pacers: only 18% with 40% boundary concession rate'
    ],
    recruitmentImplication: 'Target durable Indian domestic seamers with consistent 135+ km/h pace and repeatable action.',
    recommendedPlayerIds: ['p-204', 'p-207', 'p-208'],
  },
  {
    id: 'need-7',
    category: 'Genuine all-rounder depth',
    season: 'IPL 2026',
    historicalObservation: 'Tactical imbalance forced RR to field a long tail, preventing aggressive batting intent from top-order players who feared exposing number 8 too early.',
    relevantMatchSituations: 'Matches where top 3 fell inside first 8 overs; defensive mindset triggered.',
    sourceReference: 'RR Analytics & Strategy Team Review 2026',
    confidenceStatus: 'High Evidence',
    supportingIndicators: [
      'Runs scored by batting positions 7-10: 12.4% of team total (Bottom 3 in IPL)',
      'Overs bowled by all-rounders: 1.2 per game',
      'Innings with tail exposed before 16th over: 5 matches'
    ],
    recruitmentImplication: 'Prioritize premier two-way cricketers (capable of batting top 7 and bowling 3-4 overs reliably).',
    recommendedPlayerIds: ['p-301', 'p-302', 'p-303'],
  },
];


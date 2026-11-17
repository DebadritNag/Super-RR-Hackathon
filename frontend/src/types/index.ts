// Core Types for SupeRR Selector Season 2 — Competition Submission Platform

export type Nationality = 'Indian' | 'Overseas' | 'Unknown';

export type InternationalStatus = 
  | 'Verified Capped' 
  | 'Derived Capped' 
  | 'Uncapped'
  | 'Unknown';

export type PlayerRole = 'Batter' | 'Bowler' | 'All-rounder' | 'Wicketkeeper' | 'Unknown';

export type IPLExperience = 'Experienced' | 'New' | 'Unknown';

export type Speciality =
  | 'Top-order batter'
  | 'Middle-order batter'
  | 'Finisher'
  | 'Pace bowler'
  | 'Spin bowler'
  | 'Death specialist'
  | 'Powerplay specialist'
  | 'Middle-over specialist'
  | 'Batting all-rounder'
  | 'Bowling all-rounder'
  | 'Wicketkeeper-batter';

export type PressureSituation =
  | 'Chase'
  | 'Defend'
  | 'High required run rate'
  | 'Low wickets remaining'
  | 'Powerplay'
  | 'Middle overs'
  | 'Death overs';

export type DataEligibility =
  | 'Eligible'
  | 'Insufficient sample'
  | 'Below data-weight gate'
  | 'Unknown';

export type DataStatus = 
  | 'Verified' 
  | 'Experimental' 
  | 'Provisional' 
  | 'Insufficient data' 
  | 'Restricted' 
  | 'Unknown';

export type FailureReasonCategory = 
  | 'below-cutoff'
  | 'insufficient-opportunities'
  | 'insufficient-matches'
  | 'failed-data-weight-gate'
  | 'missing-mapping'
  | 'insufficient-evidence'
  | 'outside-filter'
  | 'high-uncertainty'
  | 'extreme-variance';

// 8 Mandatory Dimensions for Pressure Batter Profile (Prompt 3.E)
export interface BatterRadarMetrics {
  pressureRunScoring: number;      // 0-100 normalized
  strikeRatePerformance: number;   // 0-100 normalized
  boundaryContribution: number;    // 0-100 normalized
  chasePerformance: number;        // 0-100 normalized
  middleOverPerformance: number;   // 0-100 normalized
  deathOverPerformance: number;    // 0-100 normalized
  wicketPreservation: number;      // 0-100 normalized
  consistency: number;             // 0-100 normalized
  // Underlying Raw Statistics for Tooltips
  rawValues: {
    pressureAverage: number;       // e.g. 42.4
    pressureStrikeRate: number;    // e.g. 172.5
    boundaryPercent: number;       // e.g. 23.8%
    chaseAverage: number;          // e.g. 46.1
    middleOverSR: number;          // e.g. 154.2
    deathStrikeRate: number;       // e.g. 214.5
    dotBallPercent: number;        // e.g. 22.4%
    sampleBalls: number;           // e.g. 412
  };
}

// 8 Mandatory Dimensions for Pressure Bowler Profile (Prompt 3.E)
export interface BowlerRadarMetrics {
  pressureWicketTaking: number;    // 0-100 normalized
  economyUnderPressure: number;    // 0-100 normalized
  dotBallContribution: number;     // 0-100 normalized
  powerplayEffectiveness: number;  // 0-100 normalized
  middleOverEffectiveness: number; // 0-100 normalized
  deathOverEffectiveness: number;  // 0-100 normalized
  chaseDefence: number;            // 0-100 normalized
  consistency: number;             // 0-100 normalized
  // Underlying Raw Statistics for Tooltips
  rawValues: {
    wicketsUnderPressure: number;  // e.g. 36
    pressureEconomy: number;       // e.g. 7.42
    dotBallPercent: number;        // e.g. 48.6%
    powerplayEconomy: number;      // e.g. 6.80
    middleOverEconomy: number;     // e.g. 7.15
    deathEconomy: number;          // e.g. 8.65
    chaseDefenceEconomy: number;   // e.g. 7.85
    sampleBalls: number;           // e.g. 480
  };
}

export interface Player {
  id: string;
  name: string;
  photoUrl?: string;
  team: string; // Current or most recent franchise
  nationality: Nationality;
  internationalStatus: InternationalStatus;
  role: PlayerRole;
  iplExperience: IPLExperience;
  speciality: Speciality;
  battingStyle: 'RHB' | 'LHB';
  bowlingStyle?: string;
  designation?: 'Captain' | string;
  
  // Pressure Performance Analytics
  pressureScore: number | null; // Composite score (e.g. 94.8)
  baselineScore: number | null; // Baseline expectation (e.g. 84.1)
  adjustedPerformance: number | null; // Residual uplift e.g. +12.7%
  sampleSize: number; // Balls in high-leverage situations
  matches: number; // Distinct matches evaluated
  effectiveSampleSize: number;
  reliability: 'High' | 'Medium' | 'Low' | 'Insufficient';
  uncertaintyInterval: [number, number] | null; // e.g. [92.0, 96.9]
  eligibility: DataEligibility;
  dataStatus: DataStatus;

  // Bowling specific metrics
  pressureWickets?: number;
  baselineEconomy?: number;
  pressureEconomy?: number;

  // Radar profiles
  batterRadar?: BatterRadarMetrics;
  bowlerRadar?: BowlerRadarMetrics;

  // Qualitative analysis & justification
  strongestAttributes: string[];
  weaknesses: string[];
  excelsInSituations: PressureSituation[];
  dataLimitations: string;
  rankingRationale: string;

  // Selection & Exclusion status
  isSelectedTop10?: boolean;
  unselectedCategory?: FailureReasonCategory;
  unselectedReasonText?: string;
  unselectedMetricDetail?: string;

  // Squad Fit for Rajasthan Royals (2025/2026 Historical Needs)
  squadFitScore?: number; // 0-100
  squadFitReason?: string;
  targetCategory?: string;

  // Auction estimates (Optional/Demonstration)
  auctionEstimatedMin?: number | null;
  auctionEstimatedMax?: number | null;
  auctionConfidence?: 'High' | 'Moderate' | 'Low' | 'Insufficient';
  auctionValueScore?: number;
  isPriceHistoryAvailable?: boolean;
}

export interface NavigationSection {
  id: string;
  name: string;
  iconName: string;
  badge?: string;
}

export interface HistoricalSquadNeed {
  id: string;
  category: string;
  season: 'IPL 2023' | 'IPL 2024' | 'IPL 2025' | 'IPL 2026' | 'Combined';
  historicalObservation: string;
  relevantMatchSituations: string;
  sourceReference: string;
  confidenceStatus: 'High Evidence' | 'Moderate Evidence' | 'Provisional / Media Hypothesis' | 'Verified Calculation' | 'Media Observation' | 'Analytical Interpretation';
  supportingIndicators: string[];
  recruitmentImplication: string;
  recommendedPlayerIds: string[];
}

export interface OrganizerSourceFile {
  fileName: string;
  dataType: string;
  recordCount: string;
  keyFields: string[];
  purpose: string;
  selectionJustification: string;
  inclusionStatus: 'Primary Calculation' | 'Supplementary Check';
}

export interface AuctionCombination {
  id: string;
  title: string;
  description: string;
  playerIds: string[];
  estimatedTotalMin: number;
  estimatedTotalMax: number;
  roleCoverage: string;
  nationalityComposition: string;
  strengths: string;
  risks: string;
}

export interface CustomConstraints {
  nationality: 'Indian only' | 'Overseas only' | 'Mixed' | 'No restriction';
  internationalStatus: 'Capped only' | 'Uncapped only' | 'Mixed' | 'No restriction';
  role: 'Batter' | 'Bowler' | 'All-rounder' | 'Wicketkeeper' | 'Any role';
  selectionCount: number;
  minIndian?: number;
  maxIndian?: number;
  exactIndian?: number;
  minOverseas?: number;
  maxOverseas?: number;
  exactOverseas?: number;
  minCapped?: number;
  maxCapped?: number;
  minUncapped?: number;
  maxUncapped?: number;
  minBatters?: number;
  minBowlers?: number;
  minAllRounders?: number;
  minKeepers?: number;
  isStrictMode: boolean;
}

export interface ConstraintReport {
  satisfied: boolean;
  messages: {
    rule: string;
    status: 'passed' | 'warning' | 'failed';
    detail: string;
  }[];
  unmetCount: number;
}

export interface SquadSlotRule {
  maxSquadSize: number;
  maxOverseas: number;
  minIndian: number;
  minBatters: number;
  minBowlers: number;
  minAllRounders: number;
  minWicketkeepers: number;
  totalPurseLimit: number;
}

export interface ShortlistItem {
  id: string;
  type: 'player' | 'custom-ranking' | 'comparison' | 'auction-target' | 'squad';
  title: string;
  targetId: string;
  playerIds?: string[];
  notes: string;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, any>;
}

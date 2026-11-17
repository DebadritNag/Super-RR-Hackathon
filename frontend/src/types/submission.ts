export type StatusLabel =
  | 'VALIDATED'
  | 'PROVISIONAL'
  | 'EXPLORATORY'
  | 'INSUFFICIENT_EVIDENCE'
  | 'DESCRIPTIVE_ONLY'
  | 'EXPERIMENTAL_NOT_VALIDATED';

export type RoleKind = 'batters' | 'bowlers';

export interface DataVersion {
  phase8_store_file?: string;
  criteria_sha256?: string;
  run_seq?: number;
  methodology_version?: string;
  data_version_hash?: string;
  generated_at?: string;
  descriptive_version?: string;
}

export interface ListStatus {
  role: string;
  list_status: StatusLabel;
  model_validation_status: string;
  approach: string;
  rank_basis: string | null;
  n_eligible: number | null;
  list_length: number | null;
  shortfall: string | null;
  banner: string;
  reason: string;
  combination_basis?: string | null;
  intensity_basis?: string | null;
}

export interface ApproachComparison {
  role: string;
  approach: string;
  sb: number;
  sb_low: number;
  sb_high: number;
  time_sb: number;
  oot: number;
  phase6_gate_passed: boolean;
  indicative_status: StatusLabel;
  chosen: boolean;
  n_eligible: number;
}

export interface SubmissionFile {
  name: string;
  bytes: number;
  sha256: string;
}

export interface OverviewData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  lists: ListStatus[];
  approaches_compared: ApproachComparison[];
  files: SubmissionFile[];
  navigation: string[];
}

export interface ComponentScores {
  comp_boundary?: number;
  comp_dot?: number;
  comp_runs?: number;
  comp_wicket?: number;
  z_A?: number;
  z_B?: number;
  z_CONS?: number;
  [key: string]: number | undefined;
}

export interface Top10Row {
  rank: number;
  player_id: number;
  player_name: string;
  role: string;
  primary_methodology: string;
  rank_basis: string;
  pressure_score: number;
  score_unit: string;
  interval_low: number;
  interval_high: number;
  interval_method: string;
  interval_flag: string;
  pressure_performance_unshrunk: number;
  normal_baseline: number;
  pressure_delta: number;
  observed_runs_per_ball: number;
  expected_runs_per_ball: number;
  observed_wicket_rate: number;
  expected_wicket_rate: number;
  component_scores: ComponentScores;
  pressure_matches: number;
  pressure_innings_or_spells: number;
  pressure_deliveries: number;
  total_matches?: number;
  ipl_matches?: number;
  t20i_matches?: number;
  ipl_contribution?: number;
  t20i_contribution?: number;
  ipl_score?: number;
  t20i_score?: number;
  combination_basis?: string;
  mean_intensity?: number;
  positive_unit_share?: number;
  list_status?: string;
  top10_inclusion_probability?: number | null;
  [key: string]: any;
}

export interface Top10Data {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  role: RoleKind;
  list_status: ListStatus;
  rows: Top10Row[];
}

export interface WhyRow {
  role: string;
  player_id: number;
  player_name: string;
  rank: number;
  kind: 'SELECTED' | 'NEAR_MISS' | 'RAW_STANDOUT' | 'EXCLUDED' | string;
  reason_code: string;
  detail: string;
  pressure_score?: number;
  deliveries?: number;
  matches?: number;
}

export interface WhyData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  role: RoleKind;
  kind: string | null;
  page: { total: number; limit: number; offset: number };
  rows: WhyRow[];
}

export interface RadarDimension {
  key: string;
  label: string;
  value: number | null;
  denominator: number | null;
  denominator_label: string;
  cohort_percentile: number | null;
  higher_is_better: boolean;
  available: boolean;
  unavailable_reason: string | null;
}

export interface RadarData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  role: RoleKind;
  player_id: number;
  player_name: string;
  format: string;
  normalisation_cohort: string;
  cohort_size: number;
  dimensions: RadarDimension[];
}

export interface DescriptiveProfile {
  player_id: number;
  player_name: string;
  format: string;
  participation_role: string;
  squad_role_listed: string;
  nationality: string;
  nationality_verification: string;
  international_status: string;
  international_status_verification: string;
  seasons_covered: string;
  matches_played: number;
  matches_with_participation: number;
  opportunities_innings: number;
  // Batting
  balls_faced?: number;
  runs?: number;
  dismissals?: number;
  fours?: number;
  sixes?: number;
  boundary_runs?: number;
  dot_balls?: number;
  strike_rate?: number;
  balls_per_dismissal?: number;
  average?: number;
  boundary_run_share?: number;
  boundary_ball_share?: number;
  dot_ball_share?: number;
  pp_balls?: number;
  pp_strike_rate?: number;
  mid_balls?: number;
  mid_strike_rate?: number;
  death_balls?: number;
  death_strike_rate?: number;
  vs_pace_balls?: number;
  vs_pace_strike_rate?: number;
  vs_spin_balls?: number;
  vs_spin_strike_rate?: number;
  // Bowling
  balls_bowled?: number;
  runs_conceded?: number;
  wickets?: number;
  economy_rate?: number;
  bowling_average?: number;
  bowling_strike_rate?: number;
  pp_balls_bowled?: number;
  pp_economy_rate?: number;
  mid_balls_bowled?: number;
  mid_economy_rate?: number;
  death_balls_bowled?: number;
  death_economy_rate?: number;
  [key: string]: any;
}

export interface ProfilesData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  role: RoleKind;
  page: { total: number; limit: number; offset: number };
  rows: DescriptiveProfile[];
}

export interface MethodologyData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  role_selection: any[];
  approach_comparison: any[];
  pressure_definitions: any[];
  documents: { title: string; filename: string; summary: string }[];
}

export interface ValidationData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  reliability: any[];
  win_probability: any[];
  win_probability_calibration: any[];
  expected_outcome_models: any[];
  gates: any[];
  sensitivity: any[];
  phase6: any;
  ai_verification: any;
  gate_results: GateResult[];
}

export interface AiPredictionRow {
  rank: number;
  player_id: number;
  player_name: string;
  predicted_score: number;
  baseline_estimate: number;
  residual_predicted: number;
  model_name: string;
  sample_deliveries: number;
  confidence_tier: string;
  [key: string]: any;
}

export interface ExperimentalAiData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  role: RoleKind;
  model_note: string;
  state: 'AVAILABLE' | 'INSUFFICIENT_DATA';
  rows: AiPredictionRow[];
  artefacts: any[];
}

export interface Explanation {
  kind: string;
  rank: number;
  reason_code: string;
  detail: string;
}

export interface PlayerEvidenceData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  role: RoleKind;
  player_id: number;
  player_name: string;
  selection_state: string;
  top10_row: Top10Row | null;
  explanations: Explanation[];
  estimate: Record<string, any> | null;
  ineligibility: string | null;
  descriptive: DescriptiveProfile[];
}

export interface CompareData {
  status_label: StatusLabel;
  caveats: string[];
  data_version: DataVersion;
  role: RoleKind;
  players: {
    player_id: number;
    profiles: DescriptiveProfile[];
    submitted_list_evidence: {
      rank: number;
      pressure_score: number;
      interval_low: number;
      interval_high: number;
      top10_inclusion_probability: number | null;
      list_status: string;
    } | null;
  }[];
  superiority_claim: string;
  superiority_note: string;
}

export interface GateResult { gate_id: string; passed: boolean; applicable: boolean; detail: string }


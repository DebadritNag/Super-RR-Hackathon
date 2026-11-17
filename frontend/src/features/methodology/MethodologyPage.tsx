import React from 'react';
import {
  BookOpen,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Info,
  Scale,
  Binary,
  Layers,
  Database,
  BarChart2,
} from 'lucide-react';
import { StatusBadge } from '@/components/shared/StatusBadge';

export const MethodologyPage: React.FC = () => {
  const sections = [
    {
      id: 'sec-1',
      title: '1. Pressure Situation Definition & Leverage Index',
      content: `Pressure is quantitatively defined as deliveries occurring under elevated Leverage Index (LI > 1.5). Key signals include: (a) Required Run Rate (RRR) exceeding 9.5 in 2nd innings chases, (b) Overs 16-20 (death phase) in contests separated by < 24 runs, (c) Early top-order collapse scenarios (e.g., losing 3 wickets within the first 6 overs), and (d) High-stakes knockout/playoff stages. Deliveries bowled or faced in ordinary low-leverage situations are filtered into baseline pools.`,
    },
    {
      id: 'sec-2',
      title: '2. Baseline Player Performance Calculation',
      content: `Each player's baseline reflects their performance across standard, neutral leverage situations (LI ≤ 1.0). For batters, this includes standard strike rate, non-boundary dot-ball percentage, and balls per dismissal. For bowlers, baseline captures neutral phase economy rate and balls per wicket. Baseline serves as the comparative anchor against which clutch delta is measured.`,
    },
    {
      id: 'sec-3',
      title: '3. Pressure-Adjusted Performance Metric',
      content: `The Adjusted Performance metric is calculated as the percentage differential between pressure-situation performance and baseline performance: Uplift = ((Pressure Index - Baseline Index) / Baseline Index) * 100. Positive uplift signifies players who elevate their output when the game is on the line, whereas negative uplift flags players whose effectiveness dips under scrutiny.`,
    },
    {
      id: 'sec-4',
      title: '4. Eligibility Rules & Sample Thresholds',
      content: `To prevent deceptive skew from microscopic samples (e.g. a batter hitting one six off two balls), a hard gating threshold is enforced: Minimum 100 tracked deliveries in high-pressure situations across IPL and T20Is. Players with between 50-99 balls are classified as 'Insufficient sample', while players under 50 balls are placed in 'Below data-weight gate'.`,
    },
    {
      id: 'sec-5',
      title: '5. Empirical Bayes Shrinkage Regularization',
      content: `To account for varying sample sizes among eligible players, an Empirical Bayes Shrinkage model pulls player estimates toward the population mean inversely proportional to their sample size. Players with large samples (e.g. 500+ balls) maintain scores close to their raw observation, while low-sample players are regularized to protect against false positives.`,
    },
    {
      id: 'sec-6',
      title: '6. Reliability Classification Framework',
      content: `Reliability is classified into four discrete tiers based on effective sample weight:
      • High: ≥ 300 pressure deliveries across ≥ 30 matches.
      • Medium: 100 - 299 pressure deliveries across ≥ 15 matches.
      • Low: Meets minimum threshold with high match-to-match variance.
      • Insufficient: Falls below gating threshold (< 100 deliveries).`,
    },
    {
      id: 'sec-7',
      title: '7. Uncertainty Intervals & Credible Bands',
      content: `Every displayed score incorporates a 90% Bayesian Credible Interval [Min, Max]. For elite veterans with extensive samples (e.g. Jasprit Bumrah), the uncertainty band is extremely tight (±1.5 pts). For emerging domestic talents (e.g. Priyansh Arya), the credible interval spans wider (±5.5 pts), transparently indicating statistical risk.`,
    },
    {
      id: 'sec-8',
      title: '8. Tournament & Competition Format Weighting',
      content: `Deliveries from the Indian Premier League (IPL) and ICC Men's T20 World Cups carry a 1.25x quality weight due to opponent bowling quality and crowd leverage. Bilateral T20 Internationals carry a 1.0x weight. Domestic T20 leagues (e.g. state T20 tournaments) carry a 0.75x weight in prior models.`,
    },
    {
      id: 'sec-9',
      title: '9. Data Quality & Missing Metric Restrictions',
      content: `Missing metrics are never substituted with zero, which would catastrophically distort averages and radar charts. If radar dimensions lack verified tracking for a candidate, they are displayed explicitly as 'N/A' or 'Unknown'.`,
    },
    {
      id: 'sec-10',
      title: '10. Independent Player Classification Fields',
      content: `The platform enforces strict orthogonality across player classification dimensions. These fields are never merged or conflated:
      • Nationality: Indian | Overseas | Unknown
      • International Status: Verified Capped | Derived Capped | Uncapped | Unknown (Derived Capped is NEVER treated as Verified Capped)
      • Role: Batter | Bowler | All-rounder | Wicketkeeper | Unknown
      • IPL Experience: Experienced | New | Unknown`,
    },
    {
      id: 'sec-11',
      title: '11. Dynamic Re-ranking Without Artificial Padding',
      content: `When filters are updated in the Pressure Rankings or Custom Top 10 Builder, the frontend recalculates true sequential ranks (1, 2, 3...) for strictly qualifying players. The platform never artificially pads lists if fewer than 10 players meet the criteria (e.g. if 6 qualify, exactly 6 are displayed with full exclusion audits).`,
    },
    {
      id: 'sec-12',
      title: '12. Auction Price Range Modeling Methodology',
      content: `Price range estimates (₹ Cr) represent illustrative historical hammer price distributions conditioned on player role, nationality, capped status, and pressure score. When historical auction transaction records are absent, the system explicitly displays: 'Insufficient auction-price history to estimate this player's market price' rather than generating ungrounded numbers.`,
    },
    {
      id: 'sec-13',
      title: '13. Dedicated Squad Fit Score Architecture',
      content: `The Rajasthan Royals Squad Fit Score (0-100) is maintained as a separate, isolated metric from the Pressure Performance Score and the Auction Value Score. It maps a candidate's specific ball-by-ball capabilities against Rajasthan Royals' 7 documented historical squad weaknesses (e.g. middle-order spin-choke, death-over economy).`,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs">
        <div className="flex items-center space-x-2">
          <span className="text-[10px] font-bold uppercase tracking-wider bg-[#246B4B] text-white px-2 py-0.5 rounded">
            Transparency Dossier
          </span>
          <span className="text-xs text-[#777F79]">Rajasthan Royals Scouting Analytics Protocol</span>
        </div>
        <h2 className="text-lg font-bold text-[#202522] tracking-tight mt-1">
          Methodology, Statistical Modeling & Data Quality Protocol
        </h2>
        <p className="text-xs text-[#777F79] mt-0.5 max-w-3xl leading-relaxed">
          Detailed documentation of mathematical formulas, Empirical Bayes shrinkage, classification integrity,
          and transparent uncertainty bands governing the SupeRR Selector Season 2 terminal.
        </p>

        {/* Status Indicators Legend */}
        <div className="mt-4 pt-4 border-t border-[#E5E8E3]">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#777F79] block mb-2">
            Standardized Data Quality Status Badges
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status="Verified" />
            <StatusBadge status="Experimental" />
            <StatusBadge status="Provisional" />
            <StatusBadge status="Insufficient data" />
            <StatusBadge status="Restricted" />
            <StatusBadge status="Unknown" />
          </div>
        </div>
      </div>

      {/* 13 Methodology Sections */}
      <div className="space-y-4">
        {sections.map(sec => (
          <div key={sec.id} className="bg-white rounded-xl border border-[#E5E8E3] p-5 shadow-xs space-y-2">
            <h3 className="font-bold text-sm text-[#202522] tracking-tight flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-[#246B4B]" />
              <span>{sec.title}</span>
            </h3>
            <p className="text-xs text-[#777F79] leading-relaxed pl-6 whitespace-pre-line">
              {sec.content}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};


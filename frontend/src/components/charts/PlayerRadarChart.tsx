import React from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { BatterRadarMetrics, BowlerRadarMetrics } from '@/types';

interface PlayerRadarChartProps {
  type: 'batter' | 'bowler';
  batterMetrics?: BatterRadarMetrics;
  bowlerMetrics?: BowlerRadarMetrics;
  playerName: string;
  comparisonMetrics?: BatterRadarMetrics | BowlerRadarMetrics;
  comparisonName?: string;
}

export const PlayerRadarChart: React.FC<PlayerRadarChartProps> = ({
  type,
  batterMetrics,
  bowlerMetrics,
  playerName,
  comparisonMetrics,
  comparisonName,
}) => {
  if (type === 'batter' && !batterMetrics) {
    return (
      <div className="h-72 flex items-center justify-center border border-dashed border-[#E5E8E3] rounded-lg bg-[#F7F6F2] text-xs text-[#777F79]">
        Insufficient data to construct 8-axis batter profile
      </div>
    );
  }

  if (type === 'bowler' && !bowlerMetrics) {
    return (
      <div className="h-72 flex items-center justify-center border border-dashed border-[#E5E8E3] rounded-lg bg-[#F7F6F2] text-xs text-[#777F79]">
        Insufficient data to construct 8-axis bowler profile
      </div>
    );
  }

  // 8 Mandatory Axes for Batter Profile
  let chartData: {
    subject: string;
    score: number;
    raw: string;
    explanation: string;
    compScore?: number;
    compRaw?: string;
  }[] = [];

  if (type === 'batter' && batterMetrics) {
    const comp = comparisonMetrics as BatterRadarMetrics | undefined;
    chartData = [
      {
        subject: 'Run Scoring',
        score: batterMetrics.pressureRunScoring,
        raw: `${batterMetrics.rawValues.pressureAverage} Avg in clutch situations`,
        explanation: 'Scoring volume & runs per wicket under high leverage index',
        compScore: comp?.pressureRunScoring,
        compRaw: comp ? `${comp.rawValues.pressureAverage} Avg` : undefined,
      },
      {
        subject: 'Strike Rate',
        score: batterMetrics.strikeRatePerformance,
        raw: `${batterMetrics.rawValues.pressureStrikeRate} SR (+uplift vs baseline)`,
        explanation: 'Velocity of run accumulation relative to innings phase baseline',
        compScore: comp?.strikeRatePerformance,
        compRaw: comp ? `${comp.rawValues.pressureStrikeRate} SR` : undefined,
      },
      {
        subject: 'Boundaries',
        score: batterMetrics.boundaryContribution,
        raw: `${batterMetrics.rawValues.boundaryPercent}% Boundary balls`,
        explanation: 'Percentage of deliveries converted into 4s or 6s in pressure overs',
        compScore: comp?.boundaryContribution,
        compRaw: comp ? `${comp.rawValues.boundaryPercent}%` : undefined,
      },
      {
        subject: 'Chase Impact',
        score: batterMetrics.chasePerformance,
        raw: `${batterMetrics.rawValues.chaseAverage} Avg chasing >9 RRR`,
        explanation: 'Match-winning execution in 2nd innings pressure targets',
        compScore: comp?.chasePerformance,
        compRaw: comp ? `${comp.rawValues.chaseAverage} Avg` : undefined,
      },
      {
        subject: 'Middle Overs',
        score: batterMetrics.middleOverPerformance,
        raw: `${batterMetrics.rawValues.middleOverSR} SR vs Spin (Overs 7-15)`,
        explanation: 'Rotation and boundary conversion against finger and wrist spin',
        compScore: comp?.middleOverPerformance,
        compRaw: comp ? `${comp.rawValues.middleOverSR} SR` : undefined,
      },
      {
        subject: 'Death Overs',
        score: batterMetrics.deathOverPerformance,
        raw: `${batterMetrics.rawValues.deathStrikeRate} SR in overs 16-20`,
        explanation: 'Boundary acceleration at the climax of the innings',
        compScore: comp?.deathOverPerformance,
        compRaw: comp ? `${comp.rawValues.deathStrikeRate} SR` : undefined,
      },
      {
        subject: 'Wkt Preservation',
        score: batterMetrics.wicketPreservation,
        raw: `${batterMetrics.rawValues.dotBallPercent}% Dots (Lower is better)`,
        explanation: 'Minimizing wasted dot deliveries without surrendering wicket',
        compScore: comp?.wicketPreservation,
        compRaw: comp ? `${comp.rawValues.dotBallPercent}% Dots` : undefined,
      },
      {
        subject: 'Consistency',
        score: batterMetrics.consistency,
        raw: `${batterMetrics.rawValues.sampleBalls} balls across sample`,
        explanation: 'Bayesian shrinkage stability and low variance across matches',
        compScore: comp?.consistency,
        compRaw: comp ? `${comp.rawValues.sampleBalls} balls` : undefined,
      },
    ];
  } else if (type === 'bowler' && bowlerMetrics) {
    const comp = comparisonMetrics as BowlerRadarMetrics | undefined;
    chartData = [
      {
        subject: 'Wicket Threat',
        score: bowlerMetrics.pressureWicketTaking,
        raw: `${bowlerMetrics.rawValues.wicketsUnderPressure} clutch wickets`,
        explanation: 'Breakthrough ability in high-leverage and late-overs phases',
        compScore: comp?.pressureWicketTaking,
        compRaw: comp ? `${comp.rawValues.wicketsUnderPressure} wkts` : undefined,
      },
      {
        subject: 'Economy Rate',
        score: bowlerMetrics.economyUnderPressure,
        raw: `${bowlerMetrics.rawValues.pressureEconomy} RPO in pressure`,
        explanation: 'Residual run suppression against expected boundary rate',
        compScore: comp?.economyUnderPressure,
        compRaw: comp ? `${comp.rawValues.pressureEconomy} RPO` : undefined,
      },
      {
        subject: 'Dot Balls',
        score: bowlerMetrics.dotBallContribution,
        raw: `${bowlerMetrics.rawValues.dotBallPercent}% Dot ball rate`,
        explanation: 'Deliveries generating zero runs under defensive pressure',
        compScore: comp?.dotBallContribution,
        compRaw: comp ? `${comp.rawValues.dotBallPercent}%` : undefined,
      },
      {
        subject: 'Powerplay',
        score: bowlerMetrics.powerplayEffectiveness,
        raw: `${bowlerMetrics.rawValues.powerplayEconomy} RPO in overs 1-6`,
        explanation: 'Early innings containment and partnership disruption',
        compScore: comp?.powerplayEffectiveness,
        compRaw: comp ? `${comp.rawValues.powerplayEconomy} RPO` : undefined,
      },
      {
        subject: 'Middle Phase',
        score: bowlerMetrics.middleOverEffectiveness,
        raw: `${bowlerMetrics.rawValues.middleOverEconomy} RPO in overs 7-15`,
        explanation: 'Squeeze efficiency during consolidation overs',
        compScore: comp?.middleOverEffectiveness,
        compRaw: comp ? `${comp.rawValues.middleOverEconomy} RPO` : undefined,
      },
      {
        subject: 'Death Phase',
        score: bowlerMetrics.deathOverEffectiveness,
        raw: `${bowlerMetrics.rawValues.deathEconomy} RPO in overs 16-20`,
        explanation: 'Yorker execution and boundary denial in final overs',
        compScore: comp?.deathOverEffectiveness,
        compRaw: comp ? `${comp.rawValues.deathEconomy} RPO` : undefined,
      },
      {
        subject: 'Chase Defence',
        score: bowlerMetrics.chaseDefence,
        raw: `${bowlerMetrics.rawValues.chaseDefenceEconomy} RPO defending totals`,
        explanation: 'Composure when defending targets against aggressive batters',
        compScore: comp?.chaseDefence,
        compRaw: comp ? `${comp.rawValues.chaseDefenceEconomy} RPO` : undefined,
      },
      {
        subject: 'Consistency',
        score: bowlerMetrics.consistency,
        raw: `${bowlerMetrics.rawValues.sampleBalls} balls bowled in pressure`,
        explanation: 'Match-to-match reliability score from Bayesian prior',
        compScore: comp?.consistency,
        compRaw: comp ? `${comp.rawValues.sampleBalls} balls` : undefined,
      },
    ];
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-[#202522] text-white p-3 rounded-md shadow-xl text-xs border border-[#3b7e5f] max-w-xs z-50">
          <div className="font-bold text-emerald-400 uppercase tracking-wider text-[11px] mb-1">
            {data.subject}
          </div>
          <div className="text-[11px] text-[#C4CBC6] mb-2 leading-relaxed">
            {data.explanation}
          </div>

          <div className="pt-2 border-t border-[#2d3430] space-y-1">
            <div className="flex justify-between items-center text-[11px]">
              <span className="font-semibold text-white">{playerName}:</span>
              <span className="font-bold text-emerald-300">
                {data.score}/100 <span className="text-[#8F9791] font-normal">({data.raw})</span>
              </span>
            </div>
            {comparisonName && data.compScore !== undefined && (
              <div className="flex justify-between items-center text-[11px]">
                <span className="font-semibold text-[#D97736]">{comparisonName}:</span>
                <span className="font-bold text-amber-300">
                  {data.compScore}/100 <span className="text-[#8F9791] font-normal">({data.compRaw})</span>
                </span>
              </div>
            )}
          </div>
          <div className="mt-2 pt-1 border-t border-[#2d3430] text-[9px] text-[#777F79] italic">
            *Axis scores normalized to 0–100 scale relative to evaluation pool
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-72 sm:h-80 select-none">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chartData}>
          <PolarGrid stroke="#E5E8E3" strokeDasharray="3 3" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: '#202522', fontSize: 10, fontWeight: 600 }}
          />
          <PolarRadiusAxis
            angle={22.5}
            domain={[0, 100]}
            tick={{ fill: '#777F79', fontSize: 9 }}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Radar
            name={playerName}
            dataKey="score"
            stroke="#246B4B"
            fill="#246B4B"
            fillOpacity={0.35}
            strokeWidth={2}
          />
          {comparisonName && (
            <Radar
              name={comparisonName}
              dataKey="compScore"
              stroke="#D97736"
              fill="#D97736"
              fillOpacity={0.25}
              strokeWidth={2}
            />
          )}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

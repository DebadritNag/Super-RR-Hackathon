import React from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import { Player } from '@/types';

interface ComparisonRadarChartProps {
  players: Player[];
  type: 'batting' | 'bowling';
}

// Strict palette: Forest green, Amber, Charcoal, Sage/Olive
const PLAYER_COLORS = [
  { stroke: '#246B4B', fill: '#246B4B' }, // Forest green
  { stroke: '#D97736', fill: '#D97736' }, // Amber
  { stroke: '#202522', fill: '#202522' }, // Dark charcoal
  { stroke: '#27845B', fill: '#27845B' }, // Sage / Emerald
];

export const ComparisonRadarChart: React.FC<ComparisonRadarChartProps> = ({ players, type }) => {
  if (players.length < 2) {
    return (
      <div className="h-72 flex items-center justify-center border border-dashed border-[#E5E8E3] rounded-lg bg-[#F7F6F2] text-xs text-[#777F79]">
        Select at least 2 compatible players to generate comparative spider chart
      </div>
    );
  }

  const subjects = type === 'batting'
    ? [
        { key: 'pressureRunScoring', label: 'Run Scoring' },
        { key: 'strikeRatePerformance', label: 'Strike Rate' },
        { key: 'boundaryContribution', label: 'Boundaries' },
        { key: 'chasePerformance', label: 'Chase Impact' },
        { key: 'middleOverPerformance', label: 'Middle Phase' },
        { key: 'deathOverPerformance', label: 'Death Overs' },
        { key: 'wicketPreservation', label: 'Wkt Preservation' },
        { key: 'consistency', label: 'Consistency' },
      ]
    : [
        { key: 'pressureWicketTaking', label: 'Wicket Threat' },
        { key: 'economyUnderPressure', label: 'Economy' },
        { key: 'dotBallContribution', label: 'Dot Balls' },
        { key: 'powerplayEffectiveness', label: 'Powerplay' },
        { key: 'middleOverEffectiveness', label: 'Middle Phase' },
        { key: 'deathOverEffectiveness', label: 'Death Overs' },
        { key: 'chaseDefence', label: 'Chase Defence' },
        { key: 'consistency', label: 'Consistency' },
      ];

  const chartData = subjects.map(sub => {
    const row: Record<string, any> = { subject: sub.label };
    players.forEach(p => {
      if (type === 'batting' && p.batterRadar) {
        row[p.name] = (p.batterRadar as any)[sub.key] ?? 50;
      } else if (type === 'bowling' && p.bowlerRadar) {
        row[p.name] = (p.bowlerRadar as any)[sub.key] ?? 50;
      } else {
        row[p.name] = 0;
      }
    });
    return row;
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#202522] text-white p-3 rounded-md shadow-xl text-xs max-w-xs border border-[#3b7e5f]">
          <p className="font-bold text-emerald-400 mb-1.5 uppercase tracking-wider text-[11px]">{label}</p>
          <div className="space-y-1">
            {payload.map((entry: any, i: number) => (
              <div key={i} className="flex justify-between items-center text-[11px]">
                <span className="flex items-center space-x-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.stroke }} />
                  <span className="text-[#C4CBC6] font-medium">{entry.name}:</span>
                </span>
                <span className="font-bold text-white ml-2">{entry.value} / 100</span>
              </div>
            ))}
          </div>
          <p className="text-[9px] text-[#777F79] mt-2 border-t border-[#2d3430] pt-1 italic">
            *Scores normalized to 0–100 scale relative to evaluation pool
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full flex flex-col items-center select-none">
      <div className="w-full h-80">
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
            <Legend
              wrapperStyle={{ paddingTop: '10px' }}
              formatter={(value, entry) => (
                <span className="text-xs font-semibold text-[#202522] mr-2">
                  {value}
                </span>
              )}
            />
            {players.map((player, idx) => {
              const color = PLAYER_COLORS[idx % PLAYER_COLORS.length];
              return (
                <Radar
                  key={player.id}
                  name={player.name}
                  dataKey={player.name}
                  stroke={color.stroke}
                  fill={color.fill}
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              );
            })}
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

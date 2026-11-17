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
import { SquadEvaluation } from '@/services/squadService';

interface SquadBalanceChartProps {
  evaluation: SquadEvaluation;
}

export const SquadBalanceChart: React.FC<SquadBalanceChartProps> = ({ evaluation }) => {
  const chartData = [
    { subject: 'Batting Depth', score: evaluation.battingDepthScore, explanation: 'Overall depth and run-scoring options down the order' },
    { subject: 'Bowling Depth', score: evaluation.bowlingDepthScore, explanation: 'Full 20-over coverage with reliable backup options' },
    { subject: 'Death Bowling', score: evaluation.deathBowlingRating, explanation: 'Specialist yorker & changeup capabilities in overs 16-20' },
    { subject: 'Powerplay Threat', score: evaluation.powerplayRating, explanation: 'Early wicket-taking and containment efficiency in overs 1-6' },
    { subject: 'Middle Phase', score: evaluation.middleOverRating, explanation: 'Spin control and partnership-breaking ability in overs 7-15' },
    { subject: 'Finishing Impact', score: evaluation.finishingRating, explanation: 'High strike-rate acceleration in death overs chases' },
  ];

  return (
    <div className="w-full flex flex-col items-center">
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chartData}>
            <PolarGrid stroke="#E5E8E3" strokeDasharray="3 3" />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: '#777F79', fontSize: 11, fontWeight: 500 }}
            />
            <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#E5E8E3" tick={false} />
            <Tooltip
              content={({ active, payload }: any) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="bg-[#202522] text-white p-2.5 rounded shadow text-xs">
                      <p className="font-semibold text-emerald-400">{d.subject}</p>
                      <p className="font-bold text-sm my-1">{d.score} / 100</p>
                      <p className="text-[11px] text-gray-300">{d.explanation}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Radar
              name="Squad Balance"
              dataKey="score"
              stroke="#D97736"
              fill="#D97736"
              fillOpacity={0.25}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="text-center mt-2">
        <span className="text-xs text-[#777F79]">Overall Balance Index: </span>
        <span className="text-sm font-bold text-[#202522]">{evaluation.overallBalanceScore} / 100</span>
      </div>
    </div>
  );
};


import React from 'react';
import { Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { RadarData, RadarDimension } from '@/types/submission';
import { fmt } from '@/lib/utils';

const COLOURS = ['#246B4B', '#D97736', '#202522', '#7a8a80'];

interface Props {
  series: { name: string; radar: RadarData }[];
}

/**
 * Descriptive radar. Axis length is the within-cohort percentile of each raw metric (the API states
 * the cohort). It is not a composite or pressure score. Dimensions that are unavailable for any
 * plotted player are left off the polygon and listed below it with the API's reason.
 */
export const PressureRadar: React.FC<Props> = ({ series }) => {
  if (series.length === 0) return null;
  const keys = series[0].radar.dimensions.map((d) => d.key);
  const lookup = (r: RadarData, k: string): RadarDimension | undefined => r.dimensions.find((d) => d.key === k);
  const plottable = keys.filter((k) =>
    series.every((s) => {
      const d = lookup(s.radar, k);
      return d && d.available && d.cohort_percentile !== null;
    }),
  );
  const skipped = keys.filter((k) => !plottable.includes(k));
  const data = plottable.map((k) => {
    const row: Record<string, any> = { key: k, label: lookup(series[0].radar, k)!.label };
    series.forEach((s, i) => {
      const d = lookup(s.radar, k)!;
      row[`p${i}`] = d.cohort_percentile;
      row[`raw${i}`] = d;
    });
    return row;
  });

  return (
    <div>
      <div className="h-72 sm:h-80 w-full" role="img" aria-label="Radar chart of descriptive metric percentiles within the stated cohort">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="68%">
            <PolarGrid stroke="#c9cec9" />
            <PolarAngleAxis dataKey="label" tick={{ fontSize: 11, fill: '#202522' }} />
            <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#4b524d' }} />
            {series.map((s, i) => (
              <Radar
                key={s.name}
                name={s.name}
                dataKey={`p${i}`}
                stroke={COLOURS[i % COLOURS.length]}
                fill={COLOURS[i % COLOURS.length]}
                fillOpacity={0.15}
                isAnimationActive={false}
              />
            ))}
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const row = payload[0].payload as Record<string, any>;
                return (
                  <div className="bg-white border border-[#b9bfb9] rounded p-2 text-xs shadow max-w-[240px]">
                    <div className="font-semibold mb-1">{row.label}</div>
                    {series.map((s, i) => {
                      const d = row[`raw${i}`] as RadarDimension;
                      return (
                        <div key={s.name} className="mb-1">
                          <span style={{ color: COLOURS[i % COLOURS.length] }} className="font-semibold">
                            {s.name}
                          </span>
                          : {fmt(d.value, 3)} over {fmt(d.denominator, 0)} {d.denominator_label}; cohort percentile{' '}
                          {fmt(d.cohort_percentile, 0)}
                        </div>
                      );
                    })}
                  </div>
                );
              }}
            />
            {series.length > 1 && <Legend />}
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-[#4b524d] mt-1">
        Normalisation cohort: {series.map((s) => `${s.name}: ${s.radar.normalisation_cohort} (n=${s.radar.cohort_size}, ${s.radar.format})`).join(' | ')}.
        Axes show percentile rank of each raw metric. No composite score is derived from this chart.
      </p>
      {skipped.length > 0 && (
        <ul className="mt-2 text-xs text-[#3a403c] list-disc pl-5">
          {skipped.map((k) => (
            <li key={k}>
              {lookup(series[0].radar, k)?.label ?? k}: unavailable for{' '}
              {series
                .filter((s) => {
                  const d = lookup(s.radar, k);
                  return !d || !d.available || d.cohort_percentile === null;
                })
                .map((s) => `${s.name} (${lookup(s.radar, k)?.unavailable_reason ?? 'no reason given'}${lookup(s.radar, k)?.value != null ? `; raw ${fmt(lookup(s.radar, k)!.value)} over ${fmt(lookup(s.radar, k)!.denominator, 0)} ${lookup(s.radar, k)!.denominator_label}` : ''})`)
                .join(', ')}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};


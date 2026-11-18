import React from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Card, Note, PageHeader } from '@/components/ui/ui';
import { GenericTable } from '@/components/ui/extras';

export const ValidationPage: React.FC = () => {
  const s = useApi(() => submissionApi.validation(), []);
  return (
    <div>
      <PageHeader title="Data and validation" subtitle="Reliability of the pressure estimates, model checks, publication gates and sensitivity of the ordering." />
      <Async state={s}>
        {(d) => (
          <div className="space-y-4">
            <Card title="Split-half reliability (Spearman-Brown corrected)">
              <GenericTable rows={d.reliability} columns={['approach', 'role', 'intensity', 'metric', 'n_players', 'r', 'spearman_brown', 'sb_low', 'sb_high']} />
              <div className="mt-2">
                <Note>Predeclared reliability thresholds: 0.5 (provisional) and 0.7 (validated). Intervals reaching zero mean reliability is not demonstrated.</Note>
              </div>
            </Card>
            <Card title="Publication gates (old engine, reported unchanged)">
              <GenericTable rows={d.gate_results as Record<string, any>[]} columns={['gate_id', 'passed', 'applicable', 'detail']} />
            </Card>
            <Card title="Approach gates">
              <GenericTable rows={d.gates} />
            </Card>
            <Card title="Win-probability model (2026 out-of-time check)">
              <GenericTable rows={d.win_probability} columns={['model', 'n_validation', 'brier', 'brier_const', 'brier_logit', 'log_loss', 'slope', 'intercept', 'n_train', 'train_matches']} />
              <div className="h-64 mt-4" role="img" aria-label="Calibration of predicted against observed win probability">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={d.win_probability_calibration} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
                    <CartesianGrid stroke="#e5e8e3" />
                    <XAxis dataKey="bin" tick={{ fontSize: 11 }} label={{ value: 'probability bin', position: 'insideBottom', offset: -2, fontSize: 11 }} />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="mean_pred" name="mean predicted" stroke="#246B4B" dot isAnimationActive={false} />
                    <Line type="monotone" dataKey="mean_obs" name="mean observed" stroke="#D97736" dot isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="Expected-outcome models">
              <GenericTable rows={d.expected_outcome_models} />
            </Card>
            <Card title="Sensitivity of the ordering">
              <GenericTable rows={d.sensitivity} columns={['role', 'approach', 'family', 'comparison', 'n_common', 'spearman', 'top10_overlap']} max={40} />
            </Card>
            <Card title="Earlier phase 6 findings">
              <pre className="text-xs whitespace-pre-wrap break-words">{JSON.stringify(d.phase6, null, 2)}</pre>
            </Card>
            <Card title="AI pipeline verification summary">
              <pre className="text-xs whitespace-pre-wrap break-words">{JSON.stringify(d.ai_verification?.summary ?? null, null, 2)}</pre>
            </Card>
          </div>
        )}
      </Async>
    </div>
  );
};

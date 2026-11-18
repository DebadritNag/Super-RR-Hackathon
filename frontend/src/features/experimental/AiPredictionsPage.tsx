import React, { useState } from 'react';
import { Lock } from 'lucide-react';
import type { ExperimentalAiData, RoleKind } from '@/types/submission';
import { ApiFailure, submissionApi } from '@/services/submissionApi';
import { Btn, Card, ErrorBox, Field, Loading, PageHeader, Notice, TableWrap, Th, Td, inputCls } from '@/components/ui/ui';
import { GenericTable, RoleToggle } from '@/components/ui/extras';
import { fmt } from '@/lib/utils';

/** Internal page. The access token is typed at runtime, held only in component state, never persisted or bundled. */
export const AiPredictionsPage: React.FC = () => {
  const [token, setToken] = useState('');
  const [role, setRole] = useState<RoleKind>('batters');
  const [data, setData] = useState<ExperimentalAiData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async (r: RoleKind) => {
    setLoading(true);
    setError(null);
    try {
      setData(await submissionApi.experimentalAi(r, token));
    } catch (e) {
      setData(null);
      const f = e as ApiFailure;
      setError(f.status === 401 ? 'The token was rejected.' : f.status === 503 ? 'Internal access is not enabled on the server.' : f.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Experimental AI predictions"
        subtitle="Internal view. Gradient-boosting residuals scored on one held-out year. Not the submitted ranking and not validated."
      />
      <Card className="mb-4">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            load(role);
          }}
        >
          <Field label="Internal access token" htmlFor="ai-token">
            <input id="ai-token" type="password" autoComplete="off" className={inputCls} value={token} onChange={(e) => setToken(e.target.value)} />
          </Field>
          <RoleToggle
            role={role}
            onChange={(r) => {
              setRole(r);
              if (data) load(r);
            }}
          />
          <Btn type="submit" tone="primary" disabled={!token || loading}>
            <Lock className="w-4 h-4" aria-hidden="true" /> {data ? 'Reload' : 'Unlock'}
          </Btn>
        </form>
      </Card>
      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {!data && !loading && !error && (
        <p className="text-sm">Locked. Enter the internal token to load the experimental output. The token is kept in memory only.</p>
      )}
      {data && (
        <>
          <Notice>Experimental model output, not the submitted ranking and not validated. {data.model_note}</Notice>
          {data.state === 'INSUFFICIENT_DATA' ? (
            <p className="text-sm">No rows: insufficient data for this role.</p>
          ) : (
            <TableWrap>
              <table className="min-w-[900px] w-full">
                <thead>
                  <tr>
                    <Th>Order</Th>
                    <Th>Player</Th>
                    <Th>Mean residual (95% interval)</Th>
                    <Th>Actual / expected runs per ball</Th>
                    <Th>Pressure balls</Th>
                    <Th>Pressure matches</Th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((r: Record<string, any>) => (
                    <tr key={r.player_id}>
                      <Td>{r.model_output_order}</Td>
                      <Td>{r.player_name}</Td>
                      <Td>
                        {fmt(r.mean_runs_residual)}
                        <span className="block text-xs text-[#4b524d]">
                          {fmt(r.ci_low)} to {fmt(r.ci_high)}
                        </span>
                      </Td>
                      <Td>
                        {fmt(r.actual_runs_per_ball)} / {fmt(r.expected_runs_per_ball)}
                      </Td>
                      <Td>{fmt(r.pressure_balls, 0)}</Td>
                      <Td>{fmt(r.pressure_matches, 0)}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          )}
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#246B4B] mt-5 mb-2">Model artefacts</h2>
          <GenericTable rows={data.artefacts} columns={['artefact', 'algorithm', 'trained_on', 'version', 'seed', 'sha256']} />
        </>
      )}
    </div>
  );
};

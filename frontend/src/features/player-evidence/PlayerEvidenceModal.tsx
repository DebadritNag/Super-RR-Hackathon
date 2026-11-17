import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Btn, Card, Field, StatusBanner, StatusPill, inputCls, Note } from '@/components/ui/ui';
import { PressureRadar } from '@/components/charts/PressureRadar';
import { fmt, pct } from '@/lib/utils';
import type { RoleKind } from '@/types/submission';

const Radar: React.FC<{ role: RoleKind; id: number; name: string }> = ({ role, id, name }) => {
  const [format, setFormat] = useState('IPL');
  const r = useApi(() => submissionApi.radar(role, id, format), [role, id, format]);
  return (
    <Card title="Descriptive radar (not a pressure score)">
      <div className="mb-2 max-w-[160px]">
        <Field label="Format" htmlFor="radar-format">
          <select id="radar-format" className={inputCls} value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="IPL">IPL</option>
            <option value="T20I">T20I</option>
          </select>
        </Field>
      </div>
      <Async state={r}>{(d) => <PressureRadar series={[{ name, radar: d }]} />}</Async>
    </Card>
  );
};

const Row: React.FC<{ k: string; v: React.ReactNode }> = ({ k, v }) => (
  <>
    <dt className="text-[#4b524d]">{k}</dt>
    <dd className="break-words">{v}</dd>
  </>
);

export const PlayerEvidenceModal: React.FC = () => {
  const { openPlayer, closePlayerEvidence } = useApp();
  useEffect(() => {
    if (!openPlayer) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closePlayerEvidence();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [openPlayer, closePlayerEvidence]);
  const s = useApi(
    () => (openPlayer ? submissionApi.player(openPlayer.role, openPlayer.id) : Promise.reject(new Error('none'))),
    [openPlayer?.id, openPlayer?.role],
  );
  if (!openPlayer) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50" onClick={closePlayerEvidence}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Player evidence"
        className="w-full max-w-3xl h-full overflow-y-auto bg-[#F7F6F2] p-4 sm:p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-end mb-2">
          <Btn autoFocus onClick={closePlayerEvidence} aria-label="Close player evidence">
            <X className="w-4 h-4" aria-hidden="true" /> Close
          </Btn>
        </div>
        <Async state={s}>
          {(d) => {
            const t = d.top10_row;
            const e = d.estimate;
            return (
              <div className="space-y-4">
                <div>
                  <h2 className="text-xl font-bold">{d.player_name}</h2>
                  <div className="flex gap-2 items-center mt-1 text-sm">
                    <StatusPill status={d.selection_state} />
                    <span>{d.role}, id {d.player_id}</span>
                  </div>
                </div>
                <StatusBanner status={t?.list_status ?? d.status_label} caveats={d.caveats} />
                {d.ineligibility && (
                  <Card title="Eligibility">
                    <p className="text-sm">{d.ineligibility}</p>
                  </Card>
                )}
                {t && (
                  <Card title="Submitted-list evidence">
                    <p className="text-sm mb-3">{t.short_explanation}</p>
                    <dl className="grid grid-cols-[170px_1fr] gap-x-3 gap-y-1 text-sm">
                      <Row k="Rank" v={t.rank} />
                      <Row k="Pressure score" v={`${fmt(t.pressure_score)} (${t.score_unit}), 95% interval ${fmt(t.interval_low)} to ${fmt(t.interval_high)}`} />
                      <Row k="Normal-play baseline" v={fmt(t.normal_baseline)} />
                      <Row k="Pressure level (unshrunk)" v={fmt(t.pressure_performance_unshrunk)} />
                      <Row k="Pressure minus baseline" v={fmt(t.pressure_delta)} />
                      <Row k="Observed / expected runs per ball" v={`${fmt(t.observed_runs_per_ball)} / ${fmt(t.expected_runs_per_ball)}`} />
                      <Row k="Observed / expected wicket rate" v={`${fmt(t.observed_wicket_rate)} / ${fmt(t.expected_wicket_rate)}`} />
                      <Row k="Components" v={Object.entries(t.component_scores).map(([k, v]) => `${k}: ${fmt(v)}`).join('; ')} />
                      <Row k="Pressure matches / units" v={`${fmt(t.pressure_matches, 0)} / ${fmt(t.pressure_innings_or_spells, 0)}`} />
                      <Row k="Pressure deliveries" v={fmt(t.pressure_deliveries, 0)} />
                      <Row k="Matches in total (IPL, T20I)" v={`${fmt(t.total_matches, 0)} (${fmt(t.ipl_matches, 0)}, ${fmt(t.t20i_matches, 0)})`} />
                      <Row k="Format contribution" v={`IPL ${pct(t.ipl_contribution)}, T20I ${pct(t.t20i_contribution)}`} />
                      <Row k="Share of units better than expected" v={pct(t.positive_unit_share)} />
                      <Row k="Mean pressure intensity" v={fmt(t.mean_intensity)} />
                      <Row k="Sample reliability (data weight)" v={fmt(t.sample_reliability)} />
                      <Row k="Top-10 inclusion probability" v={pct(t.top10_inclusion_probability)} />
                      <Row k="Rank interval" v={`${fmt(t.rank_interval_low, 0)} to ${fmt(t.rank_interval_high, 0)}`} />
                      <Row k="Rank under A / B / C" v={`${fmt(t.rank_in_A, 0)} / ${fmt(t.rank_in_B, 0)} / ${fmt(t.rank_in_C, 0)}`} />
                      <Row k="Rank in IPL / T20I only" v={`${fmt(t.rank_in_IPL, 0)} / ${fmt(t.rank_in_T20I, 0)}`} />
                      <Row k="Evidence class" v={String(t.evidence_class ?? 'unavailable')} />
                      <Row k="Eligibility flags" v={String(t.eligibility_flags ?? 'unavailable')} />
                      <Row k="Data-quality flags" v={String(t.data_quality_flags ?? 'unavailable')} />
                    </dl>
                  </Card>
                )}
                {!t && e && (
                  <Card title="Stored estimate (not on the submitted list)">
                    <dl className="grid grid-cols-[170px_1fr] gap-x-3 gap-y-1 text-sm">
                      <Row k="Estimated rank" v={fmt(e.rank, 0)} />
                      <Row k="Pressure score" v={fmt(e.estimate)} />
                      <Row k="Interval" v={`${fmt(e.est_low)} to ${fmt(e.est_high)}`} />
                      <Row k="Pressure deliveries" v={fmt(e.balls, 0)} />
                      <Row k="Pressure matches" v={fmt(e.pressure_matches, 0)} />
                      <Row k="Data weight" v={fmt(e.B)} />
                      <Row k="Top-10 inclusion probability" v={pct(e.top_k_prob)} />
                    </dl>
                  </Card>
                )}
                <Card title="Why this position">
                  {d.explanations.length === 0 ? (
                    <p className="text-sm">No stored explanation rows for this player.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {d.explanations.map((x, i) => (
                        <li key={i}>
                          <span className="font-mono text-xs bg-[#e9ebe7] rounded px-1.5 py-0.5 mr-2">{x.kind}</span>
                          {x.detail}
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
                {d.descriptive.length > 0 && (
                  <Card title="Descriptive sample coverage">
                    <ul className="text-sm space-y-1">
                      {d.descriptive.map((p) => (
                        <li key={p.format}>
                          {p.format}: {fmt(p.matches_played, 0)} matches, {fmt(p.balls_faced ?? p.legal_balls, 0)} balls,
                          sample sufficiency {String(p.sample_sufficiency ?? 'unavailable')}
                        </li>
                      ))}
                    </ul>
                  </Card>
                )}
                <Radar role={d.role} id={d.player_id} name={d.player_name} />
                <Note>Data version {String(d.data_version.data_version_hash ?? 'unavailable').slice(0, 40)}...</Note>
              </div>
            );
          }}
        </Async>
      </div>
    </div>
  );
};


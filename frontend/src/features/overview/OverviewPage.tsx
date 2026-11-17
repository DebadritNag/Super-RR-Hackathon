import React from 'react';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Card, PageHeader, StatusBanner, StatusPill, Note } from '@/components/ui/ui';
import { GenericTable } from '@/components/ui/extras';
import { useApp } from '@/context/AppContext';
import { Btn } from '@/components/ui/ui';

export const OverviewPage: React.FC = () => {
  const s = useApi(() => submissionApi.overview(), []);
  const { setActiveSection } = useApp();
  return (
    <div>
      <PageHeader
        title="Pressure performance: overview"
        subtitle="Two ordered Top 10 lists (batters and bowlers) built from official IPL and T20I ball-by-ball data from 2022 onward."
      />
      <Async state={s}>
        {(d) => (
          <>
            <StatusBanner status={d.status_label} caveats={d.caveats} />
            <div className="grid gap-4 md:grid-cols-2 mb-4">
              {d.lists.map((l) => (
                <Card key={l.role} title={`${l.role} list`}>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <StatusPill status={l.list_status} />
                    <span className="text-xs text-[#4b524d]">model validation: {l.model_validation_status}</span>
                  </div>
                  <p className="text-sm mb-2">{l.banner}</p>
                  <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                    <dt className="text-[#4b524d]">Approach</dt>
                    <dd>{l.approach}</dd>
                    <dt className="text-[#4b524d]">Eligible players</dt>
                    <dd>{l.n_eligible ?? 'unavailable'}</dd>
                    <dt className="text-[#4b524d]">List length</dt>
                    <dd>{l.list_length ?? 'unavailable'}</dd>
                    <dt className="text-[#4b524d]">Format combination</dt>
                    <dd className="break-words">{l.combination_basis ?? 'unavailable'}</dd>
                  </dl>
                  <div className="mt-3">
                    <Btn onClick={() => setActiveSection(l.role === 'batter' ? 'top10-batters' : 'top10-bowlers')}>Open list</Btn>
                  </div>
                </Card>
              ))}
            </div>
            <Card title="Approaches compared (split-half reliability, Spearman-Brown corrected)" className="mb-4">
              <GenericTable
                rows={d.approaches_compared}
                columns={['role', 'approach', 'sb', 'sb_low', 'sb_high', 'time_sb', 'oot', 'phase6_gate_passed', 'n_eligible', 'indicative_status', 'chosen']}
              />
              <div className="mt-2">
                <Note>Declared thresholds: 0.5 for PROVISIONAL and 0.7 for VALIDATED. Intervals that include zero mean the reliability is not distinguishable from none.</Note>
              </div>
            </Card>
            <Card title="Data provenance" className="mb-4">
              <dl className="text-sm grid gap-1 sm:grid-cols-[180px_1fr]">
                {Object.entries(d.data_version).map(([k, v]) => (
                  <React.Fragment key={k}>
                    <dt className="text-[#4b524d]">{k.replace(/_/g, ' ')}</dt>
                    <dd className="font-mono text-xs break-all">{String(v)}</dd>
                  </React.Fragment>
                ))}
              </dl>
            </Card>
            <Card title="Submission files (SHA-256)">
              <GenericTable rows={d.files} columns={['name', 'bytes', 'sha256']} />
            </Card>
          </>
        )}
      </Async>
    </div>
  );
};

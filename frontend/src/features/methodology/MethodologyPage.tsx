import React from 'react';
import { submissionApi } from '@/services/submissionApi';
import { useApi } from '@/hooks/useApi';
import { Async, Card, PageHeader, StatusBanner, StatusPill } from '@/components/ui/ui';
import { GenericTable } from '@/components/ui/extras';

export const MethodologyPage: React.FC = () => {
  const s = useApi(() => submissionApi.methodology(), []);
  return (
    <div>
      <PageHeader title="Pressure methodology" subtitle="How approaches were compared, which pressure definitions were tested and how each list's approach was chosen." />
      <Async state={s}>
        {(d) => (
          <div className="space-y-4">
            <StatusBanner status={d.status_label} caveats={d.caveats} />
            <Card title="Approach selection per role">
              <div className="space-y-4">
                {d.role_selection.map((r: Record<string, any>) => (
                  <div key={r.role} className="text-sm">
                    <div className="font-semibold mb-1">
                      {r.role}: approach {r.approach_chosen} <StatusPill status={r.list_status_cap} />
                    </div>
                    <p>{r.reason}</p>
                    <p className="text-xs text-[#4b524d] mt-1">Selection rule: {r.rule_text}</p>
                  </div>
                ))}
              </div>
            </Card>
            <Card title="Approaches compared">
              <GenericTable
                rows={d.approach_comparison}
                columns={['role', 'approach', 'sb', 'sb_low', 'sb_high', 'time_sb', 'oot', 'icc1', 'mean_data_weight', 'phase6_gate_passed', 'n_eligible', 'indicative_status', 'chosen']}
              />
            </Card>
            <Card title="Pressure definitions tested">
              <GenericTable rows={d.pressure_definitions} />
            </Card>
            <Card title="Supporting documents">
              <GenericTable rows={d.documents} columns={['name', 'available', 'sha256']} />
            </Card>
          </div>
        )}
      </Async>
    </div>
  );
};

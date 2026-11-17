import { Player } from '@/types';
import { MOCK_PLAYERS } from '@/data/mock/players';

export interface ComparisonResult {
  players: Player[];
  isCompatible: boolean;
  compatibilityMessage?: string;
  comparisonType: 'batting' | 'bowling' | 'incompatible';
  sections: {
    title: string;
    description: string;
    metrics: {
      name: string;
      values: { playerId: string; playerName: string; displayValue: string; normalizedScore: number }[];
    }[];
  }[];
  verdict: {
    strongerPlayerId?: string;
    strongerPlayerName?: string;
    summary: string;
    confidence: 'High' | 'Moderate' | 'Low' | 'Inconclusive';
    detailedRationale: string;
  };
}

export const comparisonService = {
  async comparePlayers(playerIds: string[]): Promise<ComparisonResult> {
    const selected = MOCK_PLAYERS.filter(p => playerIds.includes(p.id));

    if (selected.length < 2) {
      return {
        players: selected,
        isCompatible: false,
        comparisonType: 'incompatible',
        compatibilityMessage: 'Select at least 2 players to generate comparative analytics.',
        sections: [],
        verdict: {
          summary: 'Insufficient player count for head-to-head evaluation.',
          confidence: 'Inconclusive',
          detailedRationale: 'Add 2 to 4 compatible players (batters with batters, or bowlers with bowlers) to compare.',
        },
      };
    }

    const hasBatter = selected.some(p => p.role === 'Batter' || p.role === 'Wicketkeeper');
    const hasBowler = selected.some(p => p.role === 'Bowler');

    // Strict compatibility check: do not mix pure batter and pure bowler
    if (hasBatter && hasBowler) {
      return {
        players: selected,
        isCompatible: false,
        comparisonType: 'incompatible',
        compatibilityMessage: 'Cross-discipline comparison invalid: Cannot compare Batter radar metrics directly against Bowler radar metrics.',
        sections: [],
        verdict: {
          summary: 'Select players with compatible roles (e.g., Batter vs Batter or Bowler vs Bowler) to view multi-dimensional radar comparison.',
          confidence: 'Inconclusive',
          detailedRationale: 'Cricket scoring mechanics differ between disciplines. Decoupled evaluation is mandatory.',
        },
      };
    }

    const isBatting = hasBatter || selected.every(p => !!p.batterRadar);
    const comparisonType = isBatting ? 'batting' : 'bowling';

    // Build metric comparison sections
    const sections = [
      {
        title: 'Core Pressure & Reliability',
        description: 'Primary clutch indices adjusted for leverage index, baseline expectation, and sample shrinkage.',
        metrics: [
          {
            name: 'Composite Pressure Score',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: p.pressureScore ? `${p.pressureScore}/100` : 'N/A',
              normalizedScore: p.pressureScore ?? 0,
            })),
          },
          {
            name: isBatting ? 'Expected Run Residual (Uplift %)' : 'Expected Run Residual (Suppression %)',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: p.adjustedPerformance !== null ? `${p.adjustedPerformance > 0 ? '+' : ''}${p.adjustedPerformance}%` : 'N/A',
              normalizedScore: Math.min(100, Math.max(0, 50 + (p.adjustedPerformance ?? 0) * (isBatting ? 2.5 : -2.5))),
            })),
          },
          {
            name: 'Effective Sample Size (Balls)',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.sampleSize} balls (${p.matches} matches)`,
              normalizedScore: Math.min(100, (p.sampleSize / 550) * 100),
            })),
          },
          {
            name: 'Bayesian 90% Credible Interval',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: p.uncertaintyInterval ? `[${p.uncertaintyInterval[0]} - ${p.uncertaintyInterval[1]}]` : 'N/A',
              normalizedScore: p.uncertaintyInterval ? Math.max(10, 100 - (p.uncertaintyInterval[1] - p.uncertaintyInterval[0]) * 5) : 50,
            })),
          },
        ],
      },
    ];

    if (isBatting) {
      sections.push({
        title: 'Phase Execution & Shot Making',
        description: 'Striking efficiency across middle overs spin and death finishes.',
        metrics: [
          {
            name: 'Death Overs Strike Rate (16-20)',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.batterRadar?.rawValues.deathStrikeRate ?? 0} SR`,
              normalizedScore: p.batterRadar?.deathOverPerformance ?? 0,
            })),
          },
          {
            name: 'Middle Overs vs Spin (7-15)',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.batterRadar?.rawValues.middleOverSR ?? 0} SR`,
              normalizedScore: p.batterRadar?.middleOverPerformance ?? 0,
            })),
          },
          {
            name: 'Chase Execution Average (>9 RRR)',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.batterRadar?.rawValues.chaseAverage ?? 0} avg`,
              normalizedScore: p.batterRadar?.chasePerformance ?? 0,
            })),
          },
          {
            name: 'Boundary Conversion Rate',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.batterRadar?.rawValues.boundaryPercent ?? 0}%`,
              normalizedScore: p.batterRadar?.boundaryContribution ?? 0,
            })),
          },
          {
            name: 'Dot Ball Avoidance',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.batterRadar?.rawValues.dotBallPercent ?? 0}% dots`,
              normalizedScore: p.batterRadar?.wicketPreservation ?? 0,
            })),
          },
        ],
      });
    } else {
      sections.push({
        title: 'Phase Restriction & Wicket Threat',
        description: 'Dot ball capability and economy containment at death.',
        metrics: [
          {
            name: 'Death Overs Economy (16-20)',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.bowlerRadar?.rawValues.deathEconomy ?? 0} RPO`,
              normalizedScore: p.bowlerRadar?.deathOverEffectiveness ?? 0,
            })),
          },
          {
            name: 'Pressure Dot Ball Rate',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.bowlerRadar?.rawValues.dotBallPercent ?? 0}%`,
              normalizedScore: p.bowlerRadar?.dotBallContribution ?? 0,
            })),
          },
          {
            name: 'Powerplay Economy (1-6)',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.bowlerRadar?.rawValues.powerplayEconomy ?? 0} RPO`,
              normalizedScore: p.bowlerRadar?.powerplayEffectiveness ?? 0,
            })),
          },
          {
            name: 'Clutch Wickets Taken',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.bowlerRadar?.rawValues.wicketsUnderPressure ?? 0} wkts`,
              normalizedScore: p.bowlerRadar?.pressureWicketTaking ?? 0,
            })),
          },
          {
            name: 'Total Defence Economy in Chases',
            values: selected.map(p => ({
              playerId: p.id,
              playerName: p.name,
              displayValue: `${p.bowlerRadar?.rawValues.chaseDefenceEconomy ?? 0} RPO`,
              normalizedScore: p.bowlerRadar?.chaseDefence ?? 0,
            })),
          },
        ],
      });
    }

    // Determine verdict analytically
    const sorted = [...selected].sort((a, b) => (b.pressureScore ?? 0) - (a.pressureScore ?? 0));
    const top = sorted[0];
    const second = sorted[1];
    const diff = (top.pressureScore ?? 0) - (second.pressureScore ?? 0);

    let confidence: 'High' | 'Moderate' | 'Low' | 'Inconclusive' = 'Moderate';

    if (top.reliability === 'High' && second.reliability === 'High') {
      confidence = 'High';
    } else if (top.reliability === 'Insufficient' || second.reliability === 'Insufficient') {
      confidence = 'Inconclusive';
    }

    let summary = '';
    let detailedRationale = '';

    if (confidence === 'Inconclusive') {
      summary = `Comparison inconclusive due to limited sample size for ${top.reliability === 'Insufficient' ? top.name : second.name}.`;
      detailedRationale = `One or more candidates has not cleared the minimum sample threshold of 100 pressure balls faced/bowled. Raw rates cannot be directly contrasted against established veterans.`;
    } else if (diff < 1.0) {
      summary = `${top.name} and ${second.name} exhibit closely matched clutch ratings (within ${diff.toFixed(1)} pts).`;
      detailedRationale = `Both candidates operate at an elite tier under pressure. ${top.name} edges the overall composite by ${diff.toFixed(1)} points due to slightly superior baseline outperformance, but specific tactical deployment (e.g. death overs vs middle-overs spin) should drive the strategic selection.`;
    } else {
      summary = `Why ${top.name} ranks above ${second.name}: +${diff.toFixed(1)} point advantage in pressure composite.`;
      if (isBatting) {
        detailedRationale = `${top.name} demonstrates a higher Bayesian posterior score (${top.pressureScore} vs ${second.pressureScore}), driven by stronger boundary frequency under pressure (${top.batterRadar?.rawValues.boundaryPercent}% vs ${second.batterRadar?.rawValues.boundaryPercent}%) and superior residual uplift (+${top.adjustedPerformance}% vs +${second.adjustedPerformance}%). Furthermore, ${top.name}'s sample size of ${top.sampleSize} balls across ${top.matches} matches provides narrower confidence bounds.`;
      } else {
        detailedRationale = `${top.name} holds a substantial edge in runs-conceded residual suppression (${top.adjustedPerformance}% vs ${second.adjustedPerformance}%), maintaining an economy of ${top.bowlerRadar?.rawValues.pressureEconomy} RPO in high leverage index phases compared to ${second.bowlerRadar?.rawValues.pressureEconomy} RPO for ${second.name}.`;
      }
    }

    return {
      players: selected,
      isCompatible: true,
      comparisonType,
      sections,
      verdict: {
        strongerPlayerId: top.id,
        strongerPlayerName: top.name,
        summary,
        confidence,
        detailedRationale,
      },
    };
  },
};

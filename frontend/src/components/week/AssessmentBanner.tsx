import type { Assessment, SignalStatus } from '../../types/plan';

interface Props {
  assessment: Assessment;
}

const dotCls: Record<SignalStatus, string> = {
  green: 'et-signal-green',
  amber: 'et-signal-amber',
  red: 'et-signal-red',
};

export function AssessmentBanner({ assessment }: Props) {
  const signals = [
    assessment.volume,
    assessment.sport_balance,
    assessment.progression,
    assessment.event_readiness,
  ];

  return (
    <div className="et-assessment">
      <div className="et-assessment-row">
        {signals.map((sig) => (
          <div key={sig.label} className="et-assessment-signal">
            <div className={`et-signal-dot ${dotCls[sig.status]}`} />
            <div>
              <p className="et-signal-label">{sig.label}</p>
              <p className="et-signal-text">{sig.text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

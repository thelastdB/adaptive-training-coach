import { useParams } from '@tanstack/react-router';
import { AssessmentBanner } from '../components/week/AssessmentBanner';
import { WeekGrid } from '../components/week/WeekGrid';
import { WeekHeader } from '../components/week/WeekHeader';
import { usePlanWeek } from '../hooks/usePlan';

function parseWeekStart(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d);
}

const noop = () => {};

export default function HistoricalWeekView() {
  const { weekId } = useParams({ from: '/app/week/$weekId' });
  const { data: plan, isLoading, isError } = usePlanWeek(weekId);

  const weekStart = plan ? parseWeekStart(plan.week_start_date) : new Date();

  if (isLoading) {
    return (
      <main className="et-main">
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--et-stone)',
            fontSize: '13px',
          }}
        >
          Loading…
        </div>
      </main>
    );
  }

  if (isError || !plan) {
    return (
      <main className="et-main">
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--et-stone)',
            fontSize: '13px',
          }}
        >
          Week not found.
        </div>
      </main>
    );
  }

  return (
    <main className="et-main">
      <WeekHeader
        weekStart={weekStart}
        focus={plan.focus}
        eventName={plan.event_name ?? undefined}
        daysToEvent={plan.days_to_event ?? undefined}
        onPrevWeek={noop}
        onNextWeek={noop}
        onGenerate={noop}
        onRegenerate={noop}
        onFillEmpty={noop}
        onStartFresh={noop}
        onEvaluate={noop}
        readOnly
      />

      {plan.assessment && <AssessmentBanner assessment={plan.assessment} />}

      <WeekGrid plan={plan} onActivityMove={noop} readOnly />
    </main>
  );
}

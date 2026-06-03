import { Mark } from '../brand/Mark';
import { Icon } from '../ui/Icons';
import { AssessmentBanner } from './AssessmentBanner';
import { WeekGrid } from './WeekGrid';
import { WeekHeader } from './WeekHeader';
import { usePlan, useGeneratePlan, useMoveActivity } from '../../hooks/usePlan';

function parseWeekStart(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function WeekView() {
  const { data: plan, isLoading } = usePlan();
  const generatePlan = useGeneratePlan();
  const moveActivity = useMoveActivity();

  const isEmpty = !isLoading && !plan;
  const weekStart = plan ? parseWeekStart(plan.week_start_date) : new Date();

  function handleActivityMove(fromDay: string, toDay: string) {
    if (!plan) return;
    moveActivity.mutate({ weekId: plan.id, fromDay, toDay });
  }

  return (
    <main className="et-main" style={{ position: 'relative' }}>
      {/* Empty week overlay */}
      <div className={`et-empty-week-overlay${isEmpty ? ' visible' : ''}`}>
        <Mark width={32} height={46} theme="light" className="et-empty-week-mark" />
        <p className="et-empty-week-label">No plan for this week.</p>
        <p className="et-empty-week-sub">
          eigentakt will build a plan from your Strava history and weekly template. You can edit or
          move anything after.
        </p>
        <button
          className="et-generate-cta"
          onClick={() => generatePlan.mutate({})}
          disabled={generatePlan.isPending}
        >
          <Icon name="wand" size="sm" style={{ color: 'var(--et-bone)' }} aria-hidden />
          {generatePlan.isPending ? 'Generating…' : 'Generate this week'}
        </button>
      </div>

      <WeekHeader
        weekStart={weekStart}
        focus={plan?.focus}
        eventName={plan?.event_name ?? undefined}
        daysToEvent={plan?.days_to_event ?? undefined}
        onPrevWeek={() => {}}
        onNextWeek={() => {}}
        onGenerate={() => generatePlan.mutate({})}
        onRegenerate={() => generatePlan.mutate({})}
        onFillEmpty={() => generatePlan.mutate('fill')}
        onStartFresh={() => generatePlan.mutate('fresh')}
        onEvaluate={() => {}}
      />

      {plan?.assessment && <AssessmentBanner assessment={plan.assessment} />}

      {plan && <WeekGrid plan={plan} onActivityMove={handleActivityMove} />}

      {isLoading && !plan && (
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
      )}
    </main>
  );
}

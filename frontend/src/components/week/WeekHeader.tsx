import { Button } from '../ui/Button';
import { SplitButton } from '../ui/SplitButton';
import { DropdownItem, DropdownDivider } from '../ui/Dropdown';
import { Icon } from '../ui/Icons';

interface Props {
  weekStart: Date;
  focus?: string;
  eventName?: string;
  daysToEvent?: number;
  onPrevWeek: () => void;
  onNextWeek: () => void;
  onGenerate: () => void;
  onRegenerate: () => void;
  onFillEmpty: () => void;
  onStartFresh: () => void;
  onEvaluate: () => void;
  readOnly?: boolean;
}

function formatWeekRange(start: Date): string {
  const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 6);
  const startMonth = start.toLocaleString('en-US', { month: 'long' });
  const endMonth = end.toLocaleString('en-US', { month: 'long' });
  const year = end.getFullYear();
  if (startMonth === endMonth) {
    return `${startMonth} ${start.getDate()} – ${end.getDate()}, ${year}`;
  }
  return `${startMonth} ${start.getDate()} – ${endMonth} ${end.getDate()}, ${year}`;
}

export function WeekHeader({
  weekStart,
  focus,
  eventName,
  daysToEvent,
  onPrevWeek,
  onNextWeek,
  onGenerate,
  onRegenerate,
  onFillEmpty,
  onStartFresh,
  onEvaluate,
  readOnly = false,
}: Props) {
  const eventCountdown =
    eventName && daysToEvent != null ? `${eventName} in ${daysToEvent} days` : undefined;

  return (
    <div className="et-main-header">
      <div className="et-week-nav">
        <Button variant="icon" onClick={onPrevWeek} aria-label="Previous week" disabled={readOnly}>
          <Icon name="chevron-left" size="sm" aria-hidden />
        </Button>

        <div className="et-week-info">
          <span className="et-week-title">{formatWeekRange(weekStart)}</span>
          {(eventCountdown || focus) && (
            <div className="et-week-meta">
              {eventCountdown && <span className="et-week-sub">{eventCountdown}</span>}
              {focus && <span className="et-focus-badge">Focus: {focus}</span>}
            </div>
          )}
        </div>

        <Button variant="icon" onClick={onNextWeek} aria-label="Next week" disabled={readOnly}>
          <Icon name="chevron-right" size="sm" aria-hidden />
        </Button>
      </div>

      <div className="et-header-right">
        {readOnly ? (
          <span
            style={{
              fontSize: '11px',
              fontWeight: 500,
              color: 'var(--et-stone)',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}
          >
            Past week
          </span>
        ) : (
          <>
            <Button onClick={onEvaluate}>
              <Icon name="refresh" size="sm" aria-hidden /> Evaluate
            </Button>

            <SplitButton
              label={
                <>
                  <Icon name="wand" size="sm" style={{ color: 'var(--et-bone)' }} aria-hidden />
                  <span className="et-split-label">Generate</span>
                </>
              }
              onClick={onGenerate}
            >
              <DropdownItem
                label={
                  <>
                    <Icon name="wand" size="sm" style={{ color: 'var(--et-olive)' }} aria-hidden />
                    Regenerate plan
                  </>
                }
                sublabel="Replace all non-fixed activities"
                onClick={onRegenerate}
              />
              <DropdownItem
                label={
                  <>
                    <Icon name="sparkles" size="sm" style={{ color: 'var(--et-olive)' }} aria-hidden />
                    Fill empty days
                  </>
                }
                sublabel="Generate only for days with no activity"
                onClick={onFillEmpty}
              />
              <DropdownDivider />
              <DropdownItem
                label={
                  <>
                    <Icon name="trash" size="sm" style={{ color: 'var(--et-red)' }} aria-hidden />
                    Start fresh
                  </>
                }
                sublabel="Clear all activities and generate new"
                destructive
                onClick={onStartFresh}
              />
            </SplitButton>
          </>
        )}
      </div>
    </div>
  );
}

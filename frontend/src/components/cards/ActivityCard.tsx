import { forwardRef } from 'react';
import type { ActivityDay } from '../../types/plan';
import { Icon } from '../ui/Icons';
import { IntensityBadge } from './IntensityBadge';

export interface ActivityCardBaseProps {
  activity: ActivityDay;
  isDragging?: boolean;
  isGhost?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onRefresh?: () => void;
}

type ActivityCardProps = ActivityCardBaseProps & React.HTMLAttributes<HTMLDivElement>;

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h} hr` : `${h} hr ${m} min`;
}

function activityIcon(type: string): string {
  const t = type.toLowerCase();
  if (t.includes('ride') || t.includes('cycling') || t.includes('bike')) return 'bike';
  if (t.includes('run')) return 'run';
  return 'body';
}

function activityLabel(type: string): string {
  return type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function weatherIcon(note: string): string {
  const n = note.toLowerCase();
  if (n.includes('rain')) return 'cloud-rain';
  if (n.includes('cloud') || n.includes('overcast')) return 'cloud';
  return 'sun';
}

export const ActivityCard = forwardRef<HTMLDivElement, ActivityCardProps>(
  function ActivityCard(
    { activity, isDragging = false, isGhost = false, onEdit, onDelete, onRefresh, className, ...rest },
    ref,
  ) {
    const cardCls = [
      'et-card',
      activity.is_fixed ? 'fixed' : '',
      activity.is_stale ? 'stale' : '',
      isDragging ? 'dragging' : '',
      isGhost ? 'drag-ghost' : '',
      className ?? '',
    ]
      .filter(Boolean)
      .join(' ');

    const meta = [
      formatDuration(activity.duration_minutes),
      activity.time_of_day,
      activity.is_fixed ? 'Fixed' : null,
    ]
      .filter(Boolean)
      .join(' · ');

    return (
      <div ref={ref} className={cardCls} {...rest}>
        {activity.is_stale && (
          <div className="et-card-corner">
            <div className="et-stale-badge" aria-label="Needs refresh">
              <Icon
                name="refresh"
                style={{ width: '7px', height: '7px', color: 'var(--et-bone)' }}
                aria-hidden
              />
            </div>
          </div>
        )}

        {activity.is_fixed && (
          <div className="et-card-corner">
            <Icon
              name="lock"
              className="et-lock-icon"
              style={{ width: '10px', height: '10px' }}
              aria-hidden
            />
          </div>
        )}

        <div className="et-card-type">
          <Icon
            name={activityIcon(activity.activity_type)}
            size="sm"
            className="et-card-icon"
            aria-hidden
          />
          <span className="et-card-label">{activityLabel(activity.activity_type)}</span>
        </div>

        <IntensityBadge intensity={activity.intensity} />

        <p className="et-card-meta">{meta}</p>

        <p className={`et-card-desc${activity.is_stale ? ' stale' : ''}`}>
          {activity.description}
        </p>

        {activity.weather_note && (
          <div className="et-card-weather">
            <Icon name={weatherIcon(activity.weather_note)} size="xs" aria-hidden />
            {activity.weather_note}
          </div>
        )}

        {activity.is_stale && (
          <div className="et-flag">
            <Icon
              name="alert"
              style={{ width: '8px', height: '8px', color: '#6A4010', flexShrink: 0, marginTop: '2px' }}
              aria-hidden
            />
            <p className="et-flag-text">Moved from another day — description needs refresh.</p>
          </div>
        )}

        {!activity.is_fixed && (
          <div className="et-card-actions">
            {activity.is_stale && (
              <button
                className="et-card-btn stale-btn"
                aria-label="Refresh description"
                onClick={(e) => { e.stopPropagation(); onRefresh?.(); }}
              >
                <Icon name="refresh" size="sm" aria-hidden />
              </button>
            )}
            <button
              className="et-card-btn"
              aria-label="Edit"
              onClick={(e) => { e.stopPropagation(); onEdit?.(); }}
            >
              <Icon name="edit" size="sm" aria-hidden />
            </button>
            <button
              className="et-card-btn"
              aria-label="Delete"
              onClick={(e) => { e.stopPropagation(); onDelete?.(); }}
            >
              <Icon name="trash" size="sm" aria-hidden />
            </button>
          </div>
        )}
      </div>
    );
  },
);

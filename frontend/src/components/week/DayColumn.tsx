import { useDraggable, useDroppable } from '@dnd-kit/core';
import type { ActivityDay } from '../../types/plan';
import { ActivityCard, type ActivityCardBaseProps } from '../cards/ActivityCard';
import { EmptySlot } from '../cards/EmptySlot';
import { RestSlot } from '../cards/RestSlot';

interface DayColumnProps {
  day: string;
  dayLabel: string;
  date: number;
  isToday: boolean;
  activity?: ActivityDay;
  onAdd?: () => void;
  readOnly?: boolean;
}

function DraggableCard(props: ActivityCardBaseProps) {
  const { activity } = props;
  const { setNodeRef, listeners, attributes, isDragging } = useDraggable({
    id: activity.day,
    data: { day: activity.day },
    disabled: activity.is_fixed,
  });

  return (
    <ActivityCard
      ref={setNodeRef}
      isDragging={isDragging}
      {...(activity.is_fixed ? {} : { ...attributes, ...listeners })}
      {...props}
    />
  );
}

export function DayColumn({ day, dayLabel, date, isToday, activity, onAdd, readOnly = false }: DayColumnProps) {
  const hasFixed = !!activity && activity.is_fixed;
  const { isOver, setNodeRef } = useDroppable({ id: day });

  const colCls = [
    'et-day-col',
    isOver && !hasFixed ? 'drop-compatible' : '',
    isOver && hasFixed ? 'drop-incompatible' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const isRest = activity?.activity_type === 'rest';

  return (
    <div ref={setNodeRef} className={colCls} data-day={day}>
      <div className="et-day-header">
        <p className="et-day-name">{dayLabel}</p>
        <p className={`et-day-date${isToday ? ' today' : ''}`}>{date}</p>
      </div>

      {activity && !isRest && (
        readOnly
          ? <ActivityCard activity={activity} />
          : <DraggableCard activity={activity} />
      )}
      {isRest && <RestSlot />}
      {!activity && <EmptySlot day={day} onAdd={onAdd} />}
    </div>
  );
}

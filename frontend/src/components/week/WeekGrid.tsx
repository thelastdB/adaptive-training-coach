import { useState } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import type { PlanWeek } from '../../types/plan';
import { ActivityCard } from '../cards/ActivityCard';
import { DayColumn } from './DayColumn';

const DAY_ORDER = [
  'sunday',
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
] as const;

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function checkIsToday(d: Date): boolean {
  const now = new Date();
  return (
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear()
  );
}

interface Props {
  plan: PlanWeek;
  onActivityMove: (fromDay: string, toDay: string) => void;
  readOnly?: boolean;
}

export function WeekGrid({ plan, onActivityMove, readOnly = false }: Props) {
  const [activeDay, setActiveDay] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  const [year, month, startDay] = plan.week_start_date.split('-').map(Number);
  const dayMap = new Map(plan.days.map((d) => [d.day, d]));
  const activeActivity = activeDay ? dayMap.get(activeDay) : undefined;

  function handleDragStart({ active }: DragStartEvent) {
    setActiveDay((active.data.current?.day as string) ?? null);
  }

  function handleDragEnd({ active, over }: DragEndEvent) {
    setActiveDay(null);
    if (!over) return;
    const fromDay = active.data.current?.day as string;
    const toDay = over.id as string;
    if (fromDay === toDay) return;
    const target = dayMap.get(toDay);
    if (target?.is_fixed) return;
    onActivityMove(fromDay, toDay);
  }

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="et-grid-wrap">
        <div className="et-grid">
          {DAY_ORDER.map((day, i) => {
            const date = new Date(year, month - 1, startDay + i);
            return (
              <DayColumn
                key={day}
                day={day}
                dayLabel={DAY_LABELS[i]}
                date={date.getDate()}
                isToday={checkIsToday(date)}
                activity={dayMap.get(day)}
                readOnly={readOnly}
              />
            );
          })}
        </div>
      </div>

      {!readOnly && (
        <DragOverlay dropAnimation={null}>
          {activeActivity ? <ActivityCard activity={activeActivity} isGhost /> : null}
        </DragOverlay>
      )}
    </DndContext>
  );
}

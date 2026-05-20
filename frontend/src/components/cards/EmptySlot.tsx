import { Icon } from '../ui/Icons';

interface Props {
  day: string;
  onAdd?: () => void;
}

export function EmptySlot({ day, onAdd }: Props) {
  return (
    <div
      className="et-empty-slot"
      role="button"
      aria-label={`Add or generate activity for ${day}`}
      onClick={onAdd}
    >
      <Icon name="plus" size="md" style={{ color: '#8A8A86' }} aria-hidden />
      <p className="et-empty-add">Add or Generate</p>
    </div>
  );
}

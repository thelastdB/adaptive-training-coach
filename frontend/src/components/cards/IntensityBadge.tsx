import type { Intensity } from '../../types/plan';

interface Props {
  intensity: Intensity;
}

const labelMap: Record<Intensity, string> = {
  easy: 'Easy',
  moderate: 'Moderate',
  hard: 'Hard',
};

const clsMap: Record<Intensity, string> = {
  easy: 'et-intensity-easy',
  moderate: 'et-intensity-moderate',
  hard: 'et-intensity-hard',
};

export function IntensityBadge({ intensity }: Props) {
  return (
    <span className={`et-intensity ${clsMap[intensity]}`}>
      {labelMap[intensity]}
    </span>
  );
}

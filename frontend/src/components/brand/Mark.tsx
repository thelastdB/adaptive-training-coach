interface MarkProps {
  width?: number;
  height?: number;
  theme?: 'light' | 'dark';
  className?: string;
}

export function Mark({ width = 14, height = 20, theme = 'light', className }: MarkProps) {
  const outer = theme === 'light' ? '#2C2C2A' : '#F5F2EC'; // --et-graphite : --et-bone
  const inner = theme === 'light' ? '#F5F2EC' : '#2C2C2A'; // --et-bone : --et-graphite

  // viewBox crops tightly to the triangle bounds (x 64–192, y 38–220)
  // so width/height ratio 14:20 = 0.7 matches 128:182 = 0.703 without distortion
  return (
    <svg
      width={width}
      height={height}
      viewBox="64 38 128 182"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
    >
      <path d="M128 38L192 220H64L128 38Z" fill={outer} />
      <path d="M132 62L158 206H110L132 62Z" fill={inner} />
    </svg>
  );
}

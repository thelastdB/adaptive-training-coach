import { Mark } from './Mark';

interface LogoProps {
  theme?: 'light' | 'dark';
}

export function Logo({ theme = 'light' }: LogoProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
      <Mark width={14} height={20} theme={theme} />
      <span
        className="et-wordmark"
        style={theme === 'dark' ? { color: 'var(--et-bone)' } : undefined}
      >
        eigentakt
      </span>
    </div>
  );
}

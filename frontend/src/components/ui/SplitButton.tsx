import { type ReactNode, useEffect, useRef, useState } from 'react';
import { Dropdown } from './Dropdown';

interface SplitButtonProps {
  label: ReactNode;
  onClick: () => void;
  children: ReactNode; // dropdown contents
}

export function SplitButton({ label, onClick, children }: SplitButtonProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onOutsideClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('click', onOutsideClick);
    return () => document.removeEventListener('click', onOutsideClick);
  }, []);

  return (
    <div ref={ref} className={`et-split-btn${open ? ' open' : ''}`}>
      <button className="et-split-main" onClick={onClick}>
        {label}
      </button>
      <button
        className="et-split-arrow"
        aria-label="More options"
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
      >
        <svg className="ic ic-sm" style={{ color: 'var(--et-bone)' }}>
          <use href="#ic-chevron-down" />
        </svg>
      </button>
      <Dropdown>{children}</Dropdown>
    </div>
  );
}

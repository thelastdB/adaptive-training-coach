import { type ReactNode } from 'react';

interface DropdownProps {
  children: ReactNode;
  className?: string;
}

export function Dropdown({ children, className = '' }: DropdownProps) {
  return (
    <div className={`et-dropdown ${className}`}>
      {children}
    </div>
  );
}

interface DropdownItemProps {
  label: ReactNode;
  sublabel?: string;
  destructive?: boolean;
  onClick?: () => void;
}

export function DropdownItem({ label, sublabel, destructive = false, onClick }: DropdownItemProps) {
  return (
    <div className="et-dropdown-item" onClick={onClick}>
      <span className={`et-dropdown-label${destructive ? ' destructive' : ''}`}>
        {label}
      </span>
      {sublabel && <span className="et-dropdown-sub">{sublabel}</span>}
    </div>
  );
}

export function DropdownDivider() {
  return <div className="et-dropdown-divider" />;
}

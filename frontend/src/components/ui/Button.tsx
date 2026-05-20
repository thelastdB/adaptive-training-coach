import { type ButtonHTMLAttributes, type ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'icon';
  children?: ReactNode;
}

export function Button({ variant = 'default', className = '', children, ...props }: ButtonProps) {
  const cls = ['et-btn', variant === 'icon' ? 'et-btn-icon' : '', className]
    .filter(Boolean)
    .join(' ');
  return (
    <button className={cls} {...props}>
      {children}
    </button>
  );
}

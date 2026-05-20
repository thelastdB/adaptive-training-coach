interface IconProps {
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
  style?: React.CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

export function Icon({ name, size, className, style, 'aria-hidden': ariaHidden }: IconProps) {
  const cls = ['ic', size ? `ic-${size}` : '', className].filter(Boolean).join(' ');
  return (
    <svg className={cls} style={style} aria-hidden={ariaHidden}>
      <use href={`#ic-${name}`} />
    </svg>
  );
}

export function IconDefs() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" style={{ display: 'none' }} aria-hidden="true">
      <symbol id="ic-calendar-week" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <rect x="4" y="5" width="16" height="16" rx="2"/>
        <line x1="16" y1="3" x2="16" y2="7"/>
        <line x1="8" y1="3" x2="8" y2="7"/>
        <line x1="4" y1="11" x2="20" y2="11"/>
        <line x1="4" y1="16" x2="6" y2="16"/>
        <line x1="4" y1="19" x2="6" y2="19"/>
        <line x1="9" y1="16" x2="20" y2="16"/>
        <line x1="9" y1="19" x2="20" y2="19"/>
      </symbol>

      <symbol id="ic-history" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <polyline points="12 8 12 12 14 14"/>
        <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"/>
      </symbol>

      <symbol id="ic-target" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="12" cy="12" r="1"/>
        <circle cx="12" cy="12" r="5"/>
        <circle cx="12" cy="12" r="9"/>
      </symbol>

      <symbol id="ic-clock" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="12" cy="12" r="9"/>
        <polyline points="12 7 12 12 15 15"/>
      </symbol>

      <symbol id="ic-user" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="12" cy="7" r="4"/>
        <path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"/>
      </symbol>

      <symbol id="ic-flag" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <line x1="5" y1="5" x2="5" y2="21"/>
        <line x1="19" y1="5" x2="5" y2="5"/>
        <line x1="5" y1="13" x2="19" y2="13"/>
        <polyline points="19 5 15 9 19 13"/>
      </symbol>

      <symbol id="ic-chevron-left" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <polyline points="15 6 9 12 15 18"/>
      </symbol>

      <symbol id="ic-chevron-right" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <polyline points="9 6 15 12 9 18"/>
      </symbol>

      <symbol id="ic-chevron-down" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <polyline points="6 9 12 15 18 9"/>
      </symbol>

      <symbol id="ic-refresh" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"/>
        <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"/>
      </symbol>

      <symbol id="ic-wand" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <polyline points="6 21 21 6"/>
        <line x1="15" y1="6" x2="19.5" y2="2.5"/>
        <path d="M18 22l3.35 -3.35"/>
        <path d="M10 6l-1.5 -1.5"/>
        <path d="M21 15l-1.5 -1.5"/>
        <path d="M3 12l1.5 -1.5"/>
      </symbol>

      <symbol id="ic-sparkles" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M16 18a2 2 0 0 1 2 2a2 2 0 0 1 2 -2a2 2 0 0 1 -2 -2a2 2 0 0 1 -2 2z"/>
        <path d="M6 12a2 2 0 0 1 2 2a2 2 0 0 1 2 -2a2 2 0 0 1 -2 -2a2 2 0 0 1 -2 2z"/>
        <path d="M12 2a3 3 0 0 1 3 3a3 3 0 0 1 3 -3a3 3 0 0 1 -3 -3a3 3 0 0 1 -3 3z"/>
      </symbol>

      <symbol id="ic-trash" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <line x1="4" y1="7" x2="20" y2="7"/>
        <line x1="10" y1="11" x2="10" y2="17"/>
        <line x1="14" y1="11" x2="14" y2="17"/>
        <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"/>
        <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"/>
      </symbol>

      <symbol id="ic-edit" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M9 7h-3a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-3"/>
        <path d="M9 15h3l8.5 -8.5a1.5 1.5 0 0 0 -3 -3l-8.5 8.5v3"/>
        <line x1="16" y1="5" x2="19" y2="8"/>
      </symbol>

      <symbol id="ic-sun" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="12" cy="12" r="4"/>
        <line x1="12" y1="2" x2="12" y2="4"/>
        <line x1="12" y1="20" x2="12" y2="22"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="2" y1="12" x2="4" y2="12"/>
        <line x1="20" y1="12" x2="22" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </symbol>

      <symbol id="ic-cloud-rain" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M7 18a4.6 4.4 0 0 1 0 -9a5 4.5 0 0 1 11 2h1a3.5 3.5 0 0 1 0 7"/>
        <line x1="11" y1="13" x2="10" y2="18"/>
        <line x1="15" y1="13" x2="14" y2="18"/>
      </symbol>

      <symbol id="ic-cloud" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M6.657 18c-2.572 0 -4.657 -2.007 -4.657 -4.483c0 -2.475 2.085 -4.482 4.657 -4.482c.393 -1.762 1.794 -3.2 3.675 -3.773c1.88 -.572 3.956 -.193 5.444 .986c1.488 1.18 2.162 3.007 1.77 4.769h.99c1.913 0 3.464 1.56 3.464 3.486c0 1.927 -1.551 3.487 -3.465 3.487h-11.878"/>
      </symbol>

      <symbol id="ic-bike" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="5" cy="15" r="3"/>
        <circle cx="19" cy="15" r="3"/>
        <polyline points="3.5 11 5 15 9.5 10 12 15"/>
        <line x1="9" y1="6" x2="14" y2="6"/>
        <line x1="12" y1="6" x2="12" y2="15"/>
        <path d="M16 9.7v-3.7h2"/>
      </symbol>

      <symbol id="ic-run" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="13" cy="4" r="1"/>
        <path d="M4 17l5 -5"/>
        <path d="M13 17v-6l-3 -2"/>
        <path d="M8 12l1 -5l4 1l3 3h3"/>
        <path d="M13 11l1 5l3 1"/>
      </symbol>

      <symbol id="ic-body" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="12" cy="5" r="2"/>
        <path d="M10 22v-5"/>
        <path d="M14 22v-5"/>
        <path d="M6 9a3 3 0 0 1 3 -3h6a3 3 0 0 1 3 3v3l-2 3H8l-2 -3z"/>
        <line x1="12" y1="12" x2="12" y2="17"/>
      </symbol>

      <symbol id="ic-lock" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <rect x="5" y="11" width="14" height="10" rx="2"/>
        <circle cx="12" cy="16" r="1"/>
        <path d="M8 11v-4a4 4 0 0 1 8 0v4"/>
      </symbol>

      <symbol id="ic-alert" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M12 9v4"/>
        <path d="M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0z"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </symbol>

      <symbol id="ic-plus" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
      </symbol>

      <symbol id="ic-check" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <polyline points="5 12 10 17 20 7"/>
      </symbol>

      <symbol id="ic-arrow-left" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
        <line x1="5" y1="12" x2="9" y2="16"/>
        <line x1="5" y1="12" x2="9" y2="8"/>
      </symbol>

      <symbol id="ic-arrow-right" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
        <line x1="15" y1="16" x2="19" y2="12"/>
        <line x1="15" y1="8" x2="19" y2="12"/>
      </symbol>

      <symbol id="ic-trending-up" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <polyline points="3 17 9 11 13 15 21 7"/>
        <polyline points="14 7 21 7 21 14"/>
      </symbol>

      <symbol id="ic-info-circle" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="12" cy="12" r="9"/>
        <line x1="12" y1="8" x2="12.01" y2="8"/>
        <polyline points="11 12 12 12 12 16 13 16"/>
      </symbol>

      <symbol id="ic-x" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
      </symbol>

      <symbol id="ic-unlink" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M17 22v-2"/>
        <path d="M9 15l6 -6"/>
        <path d="M11 6l.463 -.536a5 5 0 0 1 7.071 7.072l-.534 .464"/>
        <path d="M13 18l-.397 .534a5.068 5.068 0 0 1 -7.127 0a4.972 4.972 0 0 1 0 -7.071l.524 -.463"/>
        <path d="M20 17h2"/>
        <path d="M2 7h2"/>
        <path d="M7 2v2"/>
      </symbol>

      <symbol id="ic-circle-check" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <circle cx="12" cy="12" r="9"/>
        <polyline points="9 12 11 14 15 10"/>
      </symbol>

      <symbol id="ic-logout" viewBox="0 0 24 24">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M14 8v-2a2 2 0 0 0 -2 -2h-7a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h7a2 2 0 0 0 2 -2v-2"/>
        <path d="M7 12h14l-3 -3m0 6l3 -3"/>
      </symbol>
    </svg>
  );
}

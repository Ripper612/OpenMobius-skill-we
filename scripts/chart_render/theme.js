// theme.js — 主题色（仅知识库语义 role）。
// 不含技术指标 role（指标暂不在 skill 范围内）。

const THEMES = {
  dark: {
    name:       'dark',
    background: '#0e1116',
    text:       '#d0d4da',
    grid:       '#1f242c',
    border:     '#2a2f38',
    upColor:    '#26a69a',
    downColor:  '#ef5350',
    roles: {
      // K 线 / 趋势相关
      bullish:    '#26a69a',
      bearish:    '#ef5350',
      muted:      '#5a6373',

      // ICT/SMC 知识库语义
      fvg:         '#26a69a',   // Fair Value Gap（默认 bullish 绿；bearish 用 fvg_bear）
      fvg_bear:    '#ef5350',
      ob:          '#9c27b0',   // Order Block
      ob_bear:     '#7b1fa2',
      breaker:     '#aa55ff',
      liquidity:   '#ff9800',   // 流动性 / sweep

      // Trade setup
      entry_long:  '#26a69a',
      entry_short: '#ef5350',
      stop_loss:   '#ef5350',
      target:      '#2196f3',
    },
  },
  light: {
    name:       'light',
    background: '#ffffff',
    text:       '#1f2937',
    grid:       '#e5e7eb',
    border:     '#d1d5db',
    upColor:    '#22a06b',
    downColor:  '#e53935',
    roles: {
      bullish:    '#22a06b',
      bearish:    '#e53935',
      muted:      '#9ca3af',

      fvg:         '#22a06b',
      fvg_bear:    '#e53935',
      ob:          '#7b1fa2',
      ob_bear:     '#5d1090',
      breaker:     '#9c27b0',
      liquidity:   '#e65100',

      entry_long:  '#22a06b',
      entry_short: '#e53935',
      stop_loss:   '#e53935',
      target:      '#1976d2',
    },
  },
};

function colorFor(theme, role, fallback) {
  fallback = fallback || '#888';
  if (!role) return fallback;
  return theme.roles[role] || fallback;
}

window.QKTheme = { THEMES, colorFor };

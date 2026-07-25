/* ============================================================
   Central ECharts theme for DRISHTI.
   Categorical series palette is CVD-validated against the
   panel surface (#121826). Sequential = one blue, light→dark.
   Status colors are reserved for risk/status semantics only.
   ============================================================ */

export const SERIES = [
  '#3987e5', // 1 blue
  '#d95926', // 2 orange
  '#199e70', // 3 aqua
  '#c98500', // 4 yellow
  '#d55181', // 5 magenta
  '#008300', // 6 green
  '#9085e9', // 7 violet
  '#e66767', // 8 red
];

export const SEQ_BLUE = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#1c5cab', '#0d366b'];

export const STATUS = {
  good: '#0ca30c',
  warning: '#fab219',
  serious: '#ec835a',
  critical: '#d03b3b',
};

export const INK = {
  primary: '#f2f5f9',
  secondary: '#a8b3c4',
  muted: '#64748b',
  grid: 'rgba(148, 163, 184, 0.10)',
  axis: 'rgba(148, 163, 184, 0.24)',
};

export const SURFACE = '#121826';

const FONT_UI = '"Segoe UI", system-ui, sans-serif';
const FONT_MONO = '"Cascadia Mono", ui-monospace, Consolas, monospace';

/** Shared tooltip config — dark elevated card, hairline border. */
export const tooltip = {
  backgroundColor: '#182031',
  borderColor: 'rgba(148, 163, 184, 0.24)',
  borderWidth: 1,
  padding: [8, 12],
  textStyle: { color: '#f2f5f9', fontSize: 12, fontFamily: FONT_UI },
  extraCssText: 'border-radius: 6px; box-shadow: 0 8px 24px rgba(0,0,0,0.45);',
};

export const axisTooltip = {
  ...tooltip,
  trigger: 'axis',
  axisPointer: {
    type: 'line',
    lineStyle: { color: 'rgba(148, 163, 184, 0.35)', width: 1 },
  },
};

/** Category axis (x) — recessive, no heavy chrome. */
export const catAxis = (data, extra = {}) => ({
  type: 'category',
  data,
  axisLine: { lineStyle: { color: INK.axis } },
  axisTick: { show: false },
  axisLabel: { color: INK.muted, fontSize: 10.5, fontFamily: FONT_MONO },
  ...extra,
});

/** Value axis (y) — hairline solid gridlines, mono tick labels. */
export const valAxis = (extra = {}) => ({
  type: 'value',
  axisLine: { show: false },
  axisTick: { show: false },
  splitLine: { lineStyle: { color: INK.grid, type: 'solid' } },
  axisLabel: { color: INK.muted, fontSize: 10.5, fontFamily: FONT_MONO },
  ...extra,
});

// `right` leaves room for the final x-axis tick label, which sits half
// outside the plot on boundaryGap:false lines and would otherwise clip.
export const baseGrid = { left: 8, right: 26, top: 28, bottom: 4, containLabel: true };

export const baseText = { fontFamily: FONT_UI, color: INK.secondary };

/** Legend for multi-series charts (>=2 series must have one). */
export const legend = (extra = {}) => ({
  top: 0,
  right: 0,
  icon: 'roundRect',
  itemWidth: 10,
  itemHeight: 10,
  itemGap: 14,
  textStyle: { color: INK.secondary, fontSize: 11, fontFamily: FONT_UI },
  ...extra,
});

export function getFailureTheme(theme = 'light') {
  const isDark = theme === 'dark'

  return {
    isDark,
    axisText: isDark ? '#94a3b8' : '#6b7280',
    labelText: isDark ? '#cbd5e1' : '#595959',
    gridColor: isDark ? 'rgba(148, 163, 184, 0.14)' : '#f0f0f0',
    labelBadgeBg: isDark ? 'rgba(30, 41, 59, 0.92)' : 'rgba(255, 240, 240, 0.92)',
    labelBadgeBorder: isDark ? 'rgba(96, 165, 250, 0.24)' : 'rgba(255, 107, 107, 0.26)',
    labelBadgeText: isDark ? '#f8fafc' : '#262626',
    heatmapEmptyBg: isDark ? '#111827' : '#ffffff',
    heatmapText: isDark ? '#e5e7eb' : '#262626',
    tooltipBg: isDark ? '#111827' : '#ffffff',
    tooltipBorder: isDark ? '#334155' : '#f0f0f0',
    tooltipText: isDark ? '#cbd5e1' : '#595959',
    tooltipAccent: isDark ? '#60a5fa' : '#1890ff',
    heatmapColors: {
      spec: isDark
        ? ['#3b1720', '#5b1f2b', '#7f1d1d']
        : ['#fce8e6', '#f4b5af', '#e8959b'],
      strife: isDark
        ? ['#3f2a0e', '#5b3b11', '#78350f']
        : ['#fffae6', '#fff2b3', '#ffe680'],
      total: isDark
        ? ['#10243a', '#143a5b', '#1d4f91']
        : ['#e6f4fa', '#b3e0f2', '#80cce8'],
    },
  }
}

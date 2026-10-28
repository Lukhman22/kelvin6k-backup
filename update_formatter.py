import re

with open('ui/src/components/AttendanceCard.tsx', 'r') as f:
    content = f.read()

old_formatter = """  const formatDuration = (start: number, end: number | null) => {
    if (!start) return "0m";
    const endTime = end || currentTime;
    const diff = Math.max(0, endTime - start);
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };"""

new_formatter = """  const formatDuration = (start: number, end: number | null) => {
    if (!start) return "0m";
    const endTime = end || currentTime;
    const diff = Math.max(0, endTime - start);
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    const mStr = h > 0 ? String(m).padStart(2, '0') : String(m);
    if (h > 0) return `${h}h ${mStr}m`;
    return `${mStr}m`;
  };"""

content = content.replace(old_formatter, new_formatter)

with open('ui/src/components/AttendanceCard.tsx', 'w') as f:
    f.write(content)

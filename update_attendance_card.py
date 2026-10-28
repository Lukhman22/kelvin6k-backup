import re

with open('ui/src/components/AttendanceCard.tsx', 'r') as f:
    content = f.read()

# 1. Add currentTime state and interval
state_injection = """  const [newRole, setNewRole] = useState("operator");

  const [currentTime, setCurrentTime] = useState<number>(Date.now() / 1000);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Date.now() / 1000);
    }, 60000);
    return () => clearInterval(timer);
  }, []);"""
content = content.replace('  const [newRole, setNewRole] = useState("operator");', state_injection)

# 2. Add formatDuration method
method_injection = """  const formatTime = (ts: number | null) => {
    if (!ts) return "--";
    return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (start: number, end: number | null) => {
    if (!start) return "0m";
    const endTime = end || currentTime;
    const diff = Math.max(0, endTime - start);
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };"""
content = content.replace("""  const formatTime = (ts: number | null) => {
    if (!ts) return "--";
    return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };""", method_injection)

# 3. Update table header
header_replace = """<th style={{ padding: '0.2rem' }}>End</th>
              <th style={{ padding: '0.2rem' }}>Worked Hours</th>
              <th style={{ padding: '0.2rem' }}>Status</th>"""
content = content.replace("""<th style={{ padding: '0.2rem' }}>End</th>
              <th style={{ padding: '0.2rem' }}>Status</th>""", header_replace)

# 4. Update colSpan when empty
content = content.replace('colSpan={5}', 'colSpan={6}')

# 5. Update table rows
row_replace = """<td style={{ padding: '0.2rem' }}>{formatTime(r.shift_end)}</td>
                <td style={{ padding: '0.2rem' }}>{formatDuration(r.shift_start, r.shift_end)}</td>
                <td style={{ padding: '0.2rem' }}>"""
content = content.replace("""<td style={{ padding: '0.2rem' }}>{formatTime(r.shift_end)}</td>
                <td style={{ padding: '0.2rem' }}>""", row_replace)

with open('ui/src/components/AttendanceCard.tsx', 'w') as f:
    f.write(content)

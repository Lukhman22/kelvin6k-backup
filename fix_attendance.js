const fs = require('fs');

let content = fs.readFileSync('ui/src/components/AttendanceCard.tsx', 'utf8');

// 1. Fix date fetching
content = content.replace(
  'const date = new Date().toISOString().split("T")[0];',
  'const d = new Date();\n      const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;'
);

// 2. Fix the table rendering
// Replace the entire table area
const tableStart = content.indexOf('<div style={{ marginTop: \'1.5rem\' }}>');
const tableEnd = content.indexOf('</div>\n    </div>');
const tableStr = content.substring(tableStart, tableEnd + 6); // include </div>

const todayDate = `
      <div style={{ marginTop: '1.5rem' }}>
        <div style={{ marginBottom: '0.5rem' }}>
          <h4 style={{ margin: '0', fontSize: '0.9rem' }}>Today's Attendance</h4>
          <div style={{ fontSize: '0.8rem', color: '#888' }}>
            {new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
          </div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ccc' }}>
              <th style={{ padding: '0.2rem' }}>Employee</th>
              <th style={{ padding: '0.2rem' }}>Start</th>
              <th style={{ padding: '0.2rem' }}>End</th>
              <th style={{ padding: '0.2rem' }}>Status</th>
              <th style={{ padding: '0.2rem' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr><td colSpan={5} style={{ textAlign: 'center', padding: '0.5rem', color: '#666' }}>No records found.</td></tr>
            ) : records.map(r => (
              <tr key={r.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '0.2rem' }}>{r.employee_name}</td>
                <td style={{ padding: '0.2rem' }}>{formatTime(r.shift_start)}</td>
                <td style={{ padding: '0.2rem' }}>{formatTime(r.shift_end)}</td>
                <td style={{ padding: '0.2rem' }}>
                  <span style={{ 
                    padding: '0.1rem 0.3rem', 
                    borderRadius: '2px', 
                    background: r.status === 'ACTIVE' ? '#28a745' : '#6c757d',
                    color: 'white',
                    fontSize: '0.75rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}>
                    {r.status === 'ACTIVE' && <span>🟢</span>}
                    {r.status}
                  </span>
                </td>
                <td style={{ padding: '0.2rem' }}>
                  {r.status === 'ACTIVE' && (
                    <button type="button"
                      onClick={() => handleCheckOut(r)}
                      style={{ padding: '0.2rem 0.4rem', background: '#dc3545', color: 'white', border: 'none', cursor: 'pointer', borderRadius: '3px', fontSize: '0.75rem' }}
                    >
                      END SHIFT
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
`;

content = content.replace(tableStr, todayDate);

fs.writeFileSync('ui/src/components/AttendanceCard.tsx', content);

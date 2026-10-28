const fs = require('fs');

let content = fs.readFileSync('ui/src/components/AttendanceCard.tsx', 'utf8');

const formatDateStart = content.indexOf('const formatDate = (dateStr: string) => {');
const formatDateEnd = content.indexOf('};', formatDateStart) + 2;

content = content.substring(0, formatDateStart) + content.substring(formatDateEnd);

fs.writeFileSync('ui/src/components/AttendanceCard.tsx', content);

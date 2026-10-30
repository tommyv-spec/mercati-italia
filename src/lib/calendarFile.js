import { localISO } from './display.js';

// All-day calendar event for the next date: hours stay as text in the description.
export function downloadCalendarEvent(market, dateStr, hours) {
  const esc = s => String(s || '').replace(/\\/g, '\\\\').replace(/[,;]/g, m => '\\' + m).replace(/\r?\n/g, '\\n');
  const day = dateStr.replace(/-/g, '');
  const next = new Date(dateStr + 'T12:00:00'); next.setDate(next.getDate() + 1);
  const url = new URL(window.location.href); url.hash = 'mercato=' + encodeURIComponent(market.id);
  const ics = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Fuori//Mercatini d Italia//IT', 'BEGIN:VEVENT',
    'UID:' + market.id + '@fuori-mercatini.com',
    'DTSTAMP:' + new Date().toISOString().replace(/[-:]/g, '').slice(0, 15) + 'Z',
    'DTSTART;VALUE=DATE:' + day, 'DTEND;VALUE=DATE:' + localISO(next).replace(/-/g, ''),
    'SUMMARY:' + esc(market.name),
    'LOCATION:' + esc([market.address, market.city].filter(Boolean).join(', ')),
    'DESCRIPTION:' + esc((hours ? 'Orari: ' + hours + '. ' : '') + 'Data prevista, controlla la fonte prima di partire. ' + url),
    'URL:' + url, 'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([ics], { type: 'text/calendar;charset=utf-8' }));
  link.download = market.id + '.ics';
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 10000);
}

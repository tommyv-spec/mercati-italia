// ponytail: visitors report a wrong card through a prefilled GitHub issue (no backend);
// swap REPORT_URL for a form or mailbox when one exists.
export function reportUrl(market) {
  const subject = 'Segnalazione Fuori Mercatini: ' + market.name + ' (' + market.city + ')';
  const body = 'Ciao! Nella scheda di ' + market.name + ' (' + market.city + ') non torna:\n\n\n\nScheda: ' + market.id + '\nFonte: ' + (market.sourceUrl || 'n.d.') + '\n';
  return 'mailto:fuori.mercatini.sagre@gmail.com?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
}

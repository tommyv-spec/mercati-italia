/**
 * Mercati d'Italia — Seed Data
 * 
 * 30 markets across Italy's regions with realistic details.
 * Dates are generated dynamically relative to today.
 */

// ─── Date generators ────────────────────────────────────────

function today() { return new Date() }

function isoDate(d) { return d.toISOString().slice(0, 10) }

function addDays(d, n) { const r = new Date(d); r.setDate(r.getDate() + n); return r }

/** Generate every occurrence of `weekday` (0=Sun..6=Sat) for the next `weeks` weeks */
function weeklyDates(weekday, weeks = 26) {
  const dates = []
  const d = today()
  // Find next occurrence
  while (d.getDay() !== weekday) d.setDate(d.getDate() + 1)
  for (let i = 0; i < weeks; i++) {
    dates.push(isoDate(d))
    d.setDate(d.getDate() + 7)
  }
  return dates
}

/** Generate nth weekday of each month (e.g. 1st Sunday) for next `months` months */
function monthlyNthWeekday(nth, weekday, months = 6) {
  const dates = []
  const now = today()
  for (let m = 0; m < months; m++) {
    const year = now.getFullYear() + Math.floor((now.getMonth() + m) / 12)
    const month = (now.getMonth() + m) % 12
    const first = new Date(year, month, 1)
    let d = new Date(first)
    while (d.getDay() !== weekday) d.setDate(d.getDate() + 1)
    d.setDate(d.getDate() + (nth - 1) * 7)
    if (d.getMonth() === month && d >= today()) dates.push(isoDate(d))
  }
  return dates
}

/** Generate every weekday (Mon-Sat) for the next `days` days */
function dailyExceptSunday(days = 60) {
  const dates = []
  for (let i = 0; i < days; i++) {
    const d = addDays(today(), i)
    if (d.getDay() !== 0) dates.push(isoDate(d))
  }
  return dates
}

/** Generate every day for next `days` days */
function dailyAll(days = 30) {
  return Array.from({ length: days }, (_, i) => isoDate(addDays(today(), i)))
}

// ─── Seed markets ───────────────────────────────────────────

export const SEED_MARKETS = [
  // ═══ TOSCANA ═══
  {
    slug: "mercato-sant-ambrogio-firenze",
    nome: "Mercato di Sant'Ambrogio",
    citta: "Firenze", provincia: "FI", regione: "Toscana",
    indirizzo: "Piazza Lorenzo Ghiberti, 50122 Firenze FI",
    lat: 43.7696, lng: 11.2644, categoria: "alimentare",
    tags: ["al chiuso", "produttori locali"],
    orario_testo: "7:00–14:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Ogni giorno tranne domenica",
    descrizione: "Storico mercato coperto nel cuore di Firenze. Frutta, verdura, carne, pesce e specialità toscane. Atmosfera autentica lontana dai circuiti turistici.",
    confidence: 95, fonte: "Mercatini d'Italia",
    get date() { return dailyExceptSunday(60) },
  },
  {
    slug: "fiera-antiquaria-arezzo",
    nome: "Fiera Antiquaria",
    citta: "Arezzo", provincia: "AR", regione: "Toscana",
    indirizzo: "Piazza Grande, 52100 Arezzo AR",
    lat: 43.4633, lng: 11.8825, categoria: "antiquariato",
    tags: ["all'aperto", "collezionismo"],
    orario_testo: "9:00–19:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Primo weekend del mese (sabato e domenica)",
    descrizione: "La più grande fiera antiquaria d'Italia, fondata nel 1968. Oltre 500 espositori in Piazza Grande e nel centro storico con antiquariato, modernariato e oggetti da collezione.",
    confidence: 97, fonte: "eventiesagre.it",
    get date() { return [...monthlyNthWeekday(1, 6), ...monthlyNthWeekday(1, 0)] },
  },
  {
    slug: "mercato-antiquario-lucca",
    nome: "Mercato Antiquario",
    citta: "Lucca", provincia: "LU", regione: "Toscana",
    indirizzo: "Piazza San Martino, 55100 Lucca LU",
    lat: 43.8376, lng: 10.5044, categoria: "antiquariato",
    tags: ["all'aperto", "modernariato"],
    orario_testo: "9:00–19:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Terzo weekend del mese",
    descrizione: "Circa 220 espositori nelle piazze del centro storico, all'ombra delle mura rinascimentali. Mobili, stampe, ceramiche e curiosità d'epoca.",
    confidence: 90, fonte: "ilturista.info",
    get date() { return [...monthlyNthWeekday(3, 6), ...monthlyNthWeekday(3, 0)] },
  },
  {
    slug: "mercato-centrale-firenze",
    nome: "Mercato Centrale",
    citta: "Firenze", provincia: "FI", regione: "Toscana",
    indirizzo: "Piazza del Mercato Centrale, 50123 Firenze FI",
    lat: 43.7764, lng: 11.2531, categoria: "alimentare",
    tags: ["al chiuso", "produttori locali"],
    orario_testo: "7:00–14:00 (piano terra) · 10:00–24:00 (primo piano)",
    ricorrenza: "giornaliero", ricorrenza_testo: "Tutti i giorni",
    descrizione: "Mercato coperto in stile liberty nel cuore di San Lorenzo. Piano terra con banchi di prodotti freschi, primo piano con ristorazione e degustazioni.",
    confidence: 96, fonte: "Mercatini d'Italia",
    get date() { return dailyAll(60) },
  },

  // ═══ LAZIO ═══
  {
    slug: "porta-portese-roma",
    nome: "Porta Portese",
    citta: "Roma", provincia: "RM", regione: "Lazio",
    indirizzo: "Via Portuense, 00153 Roma RM",
    lat: 41.8782, lng: 12.4738, categoria: "usato",
    tags: ["all'aperto", "collezionismo", "modernariato"],
    orario_testo: "6:30–14:00",
    ricorrenza: "settimanale", ricorrenza_testo: "Ogni domenica",
    descrizione: "Il più grande mercato delle pulci di Roma, attivo dal 1945. Chilometri di bancarelle con vestiti, libri, vinili, mobili, elettronica e curiosità di ogni genere.",
    confidence: 98, fonte: "ilturista.info",
    get date() { return weeklyDates(0) },
  },
  {
    slug: "mercato-testaccio-roma",
    nome: "Mercato di Testaccio",
    citta: "Roma", provincia: "RM", regione: "Lazio",
    indirizzo: "Via Beniamino Franklin, 00153 Roma RM",
    lat: 41.8764, lng: 12.4753, categoria: "alimentare",
    tags: ["al chiuso", "produttori locali"],
    orario_testo: "7:00–15:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Ogni giorno tranne domenica",
    descrizione: "Mercato coperto moderno nel cuore del quartiere Testaccio. Banchi di ortofrutta, macelleria, pescheria, gastronomia e street food romano.",
    confidence: 93, fonte: "Mercatini d'Italia",
    get date() { return dailyExceptSunday(60) },
  },
  {
    slug: "borghetto-flaminio-roma",
    nome: "Borghetto Flaminio",
    citta: "Roma", provincia: "RM", regione: "Lazio",
    indirizzo: "Piazza della Marina 32, 00196 Roma RM",
    lat: 41.9162, lng: 12.4723, categoria: "vintage_abbigliamento",
    tags: ["al chiuso", "modernariato"],
    orario_testo: "10:00–19:00",
    ricorrenza: "settimanale", ricorrenza_testo: "Ogni domenica",
    descrizione: "Mercato vintage in un garage sotterraneo a Flaminio. Abbigliamento, accessori, design e oggettistica selezionata. L'alternativa chic a Porta Portese.",
    confidence: 85, fonte: "eventiesagre.it",
    get date() { return weeklyDates(0) },
  },

  // ═══ EMILIA-ROMAGNA ═══
  {
    slug: "mercato-albinelli-modena",
    nome: "Mercato Albinelli",
    citta: "Modena", provincia: "MO", regione: "Emilia-Romagna",
    indirizzo: "Via Luigi Albinelli, 41121 Modena MO",
    lat: 44.6462, lng: 10.9237, categoria: "alimentare",
    tags: ["al chiuso", "produttori locali"],
    orario_testo: "6:30–14:30",
    ricorrenza: "giornaliero", ricorrenza_testo: "Ogni giorno tranne domenica",
    descrizione: "Lo storico mercato coperto di Modena, dal 1931. Parmigiano Reggiano, aceto balsamico tradizionale, tortellini e specialità emiliane.",
    confidence: 96, fonte: "Mercatini d'Italia",
    get date() { return dailyExceptSunday(60) },
  },
  {
    slug: "mercato-erbe-bologna",
    nome: "Mercato delle Erbe",
    citta: "Bologna", provincia: "BO", regione: "Emilia-Romagna",
    indirizzo: "Via Ugo Bassi 25, 40121 Bologna BO",
    lat: 44.4963, lng: 11.3388, categoria: "alimentare",
    tags: ["al chiuso", "produttori locali", "serale"],
    orario_testo: "7:00–24:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Ogni giorno tranne domenica",
    descrizione: "Mercato coperto storico di Bologna, dal 1910. Di giorno prodotti freschi e gastronomia, di sera si trasforma con aperitivi e cena.",
    confidence: 93, fonte: "ilturista.info",
    get date() { return dailyExceptSunday(60) },
  },
  {
    slug: "modena-antiquaria",
    nome: "Modena Antiquaria",
    citta: "Modena", provincia: "MO", regione: "Emilia-Romagna",
    indirizzo: "Parco Novi Sad, 41121 Modena MO",
    lat: 44.6471, lng: 10.9252, categoria: "antiquariato",
    tags: ["all'aperto", "modernariato"],
    orario_testo: "8:00–18:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Quarto weekend del mese",
    descrizione: "Grande mostra mercato di antiquariato e modernariato nel parco più grande di Modena. Mobili, stampe, ceramiche e curiosità.",
    confidence: 85, fonte: "eventiesagre.it",
    get date() { return [...monthlyNthWeekday(4, 6), ...monthlyNthWeekday(4, 0)] },
  },

  // ═══ LOMBARDIA ═══
  {
    slug: "east-market-milano",
    nome: "East Market",
    citta: "Milano", provincia: "MI", regione: "Lombardia",
    indirizzo: "Via Mecenate 88/A, 20138 Milano MI",
    lat: 45.4451, lng: 9.2305, categoria: "vintage_abbigliamento",
    tags: ["al chiuso", "dischi", "modernariato"],
    orario_testo: "10:00–21:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Una domenica al mese",
    descrizione: "Mercato vintage indoor in un ex capannone industriale. Abbigliamento, vinili, design, arte e street food. L'appuntamento milanese per il vintage.",
    confidence: 92, fonte: "ilturista.info",
    get date() { return monthlyNthWeekday(2, 0) },
  },
  {
    slug: "mercato-navigli-milano",
    nome: "Mercatone dell'Antiquariato",
    citta: "Milano", provincia: "MI", regione: "Lombardia",
    indirizzo: "Alzaia Naviglio Grande, 20144 Milano MI",
    lat: 45.4530, lng: 9.1680, categoria: "antiquariato",
    tags: ["all'aperto", "collezionismo", "modernariato"],
    orario_testo: "9:00–18:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Ultima domenica del mese (escluso luglio)",
    descrizione: "Oltre 400 espositori lungo il Naviglio Grande con antiquariato, vintage, modernariato e artigianato. Uno dei mercati più suggestivi di Milano.",
    confidence: 94, fonte: "eventiesagre.it",
    get date() {
      const dates = []
      const now = today()
      for (let m = 0; m < 6; m++) {
        const year = now.getFullYear() + Math.floor((now.getMonth() + m) / 12)
        const month = (now.getMonth() + m) % 12
        if (month === 6) continue // skip July
        const lastDay = new Date(year, month + 1, 0)
        while (lastDay.getDay() !== 0) lastDay.setDate(lastDay.getDate() - 1)
        if (lastDay >= today()) dates.push(isoDate(lastDay))
      }
      return dates
    },
  },

  // ═══ PIEMONTE ═══
  {
    slug: "balon-gran-balon-torino",
    nome: "Balon e Gran Balon",
    citta: "Torino", provincia: "TO", regione: "Piemonte",
    indirizzo: "Via Borgo Dora, 10152 Torino TO",
    lat: 45.0792, lng: 7.6848, categoria: "usato",
    tags: ["all'aperto", "collezionismo", "modernariato"],
    orario_testo: "8:00–18:00",
    ricorrenza: "settimanale", ricorrenza_testo: "Ogni sabato (Gran Balon: 2ª domenica del mese)",
    descrizione: "Il mercato delle pulci più antico d'Italia, nel quartiere di Borgo Dora. Oggetti curiosi, mobili, abiti vintage e modernariato piemontese.",
    confidence: 94, fonte: "Mercatini d'Italia",
    get date() { return [...weeklyDates(6), ...monthlyNthWeekday(2, 0)] },
  },

  // ═══ VENETO ═══
  {
    slug: "mercato-rialto-venezia",
    nome: "Mercato di Rialto",
    citta: "Venezia", provincia: "VE", regione: "Veneto",
    indirizzo: "Campo de le Becarie, 30125 Venezia VE",
    lat: 45.4384, lng: 12.3350, categoria: "alimentare",
    tags: ["all'aperto", "produttori locali"],
    orario_testo: "7:00–13:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Ogni giorno tranne domenica",
    descrizione: "Il mercato più antico e famoso di Venezia, nei pressi del Ponte di Rialto. Pesce fresco della laguna, frutta e verdura, spezie e prodotti tipici veneti.",
    confidence: 97, fonte: "Mercatini d'Italia",
    get date() { return dailyExceptSunday(60) },
  },
  {
    slug: "antiquariato-campo-san-maurizio-venezia",
    nome: "Mercatino dell'Antiquariato",
    citta: "Venezia", provincia: "VE", regione: "Veneto",
    indirizzo: "Campo San Maurizio, 30124 Venezia VE",
    lat: 45.4327, lng: 12.3328, categoria: "antiquariato",
    tags: ["all'aperto", "collezionismo"],
    orario_testo: "9:00–19:00",
    ricorrenza: "irregolare", ricorrenza_testo: "Cinque volte l'anno (Pasqua, Sensa, settembre, Natale, Carnevale)",
    descrizione: "Elegante mercato antiquario tra San Marco e l'Accademia. Vetri di Murano, argenti, stampe antiche e gioielli d'epoca in una delle piazze più belle di Venezia.",
    confidence: 88, fonte: "eventiesagre.it",
    get date() { return monthlyNthWeekday(1, 6, 3) },
  },
  {
    slug: "mercato-piazza-erbe-verona",
    nome: "Mercato di Piazza delle Erbe",
    citta: "Verona", provincia: "VR", regione: "Veneto",
    indirizzo: "Piazza delle Erbe, 37121 Verona VR",
    lat: 45.4431, lng: 10.9978, categoria: "misto",
    tags: ["all'aperto", "produttori locali"],
    orario_testo: "8:00–20:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Tutti i giorni",
    descrizione: "Piazza storica con mercato permanente sin dall'epoca romana. Bancarelle di frutta, souvenir, artigianato e prodotti tipici nella piazza più bella di Verona.",
    confidence: 95, fonte: "Mercatini d'Italia",
    get date() { return dailyAll(60) },
  },

  // ═══ SICILIA ═══
  {
    slug: "mercato-capo-palermo",
    nome: "Mercato del Capo",
    citta: "Palermo", provincia: "PA", regione: "Sicilia",
    indirizzo: "Via Porta Carini, 90134 Palermo PA",
    lat: 38.1157, lng: 13.3561, categoria: "alimentare",
    tags: ["all'aperto", "produttori locali"],
    orario_testo: "7:00–20:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Tutti i giorni tranne domenica",
    descrizione: "Mercato storico nel cuore di Palermo. Profumi, colori e sapori della Sicilia: pesce freschissimo, spezie, frutta, panelle e street food.",
    confidence: 90, fonte: "Mercatini d'Italia",
    get date() { return dailyExceptSunday(60) },
  },
  {
    slug: "mercato-ballaro-palermo",
    nome: "Mercato di Ballarò",
    citta: "Palermo", provincia: "PA", regione: "Sicilia",
    indirizzo: "Piazza Casa Professa, 90134 Palermo PA",
    lat: 38.1106, lng: 13.3610, categoria: "alimentare",
    tags: ["all'aperto", "produttori locali"],
    orario_testo: "7:00–19:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Tutti i giorni",
    descrizione: "Il più antico mercato di Palermo, citato già nel X secolo. Abbaniate (richiami) dei venditori, pesce, carne, frutta e street food palermitano autentico.",
    confidence: 93, fonte: "ilturista.info",
    get date() { return dailyAll(60) },
  },

  // ═══ CAMPANIA ═══
  {
    slug: "fiera-antiquariato-napoli",
    nome: "Fiera dell'Antiquariato",
    citta: "Napoli", provincia: "NA", regione: "Campania",
    indirizzo: "Via Francesco Caracciolo, 80122 Napoli NA",
    lat: 40.8303, lng: 14.2268, categoria: "antiquariato",
    tags: ["all'aperto", "collezionismo"],
    orario_testo: "8:30–14:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Primo e terzo weekend del mese",
    descrizione: "Mercato antiquario sul lungomare di Napoli con vista sul Vesuvio. Ceramiche vietresi, stampe antiche, libri rari e argenteria.",
    confidence: 87, fonte: "ilturista.info",
    get date() { return [...monthlyNthWeekday(1, 6), ...monthlyNthWeekday(1, 0), ...monthlyNthWeekday(3, 6), ...monthlyNthWeekday(3, 0)] },
  },
  {
    slug: "mercato-porta-nolana-napoli",
    nome: "Mercato di Porta Nolana",
    citta: "Napoli", provincia: "NA", regione: "Campania",
    indirizzo: "Piazza Nolana, 80142 Napoli NA",
    lat: 40.8476, lng: 14.2656, categoria: "alimentare",
    tags: ["all'aperto", "produttori locali"],
    orario_testo: "7:00–14:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Tutti i giorni",
    descrizione: "Il mercato più verace di Napoli. Pesce freschissimo, frutta, verdura, spezie e street food: pizzette, maccheroni, frittate e sfogliatelle.",
    confidence: 91, fonte: "Mercatini d'Italia",
    get date() { return dailyAll(60) },
  },

  // ═══ PUGLIA ═══
  {
    slug: "mercato-artigianato-lecce",
    nome: "Mercato dell'Artigianato",
    citta: "Lecce", provincia: "LE", regione: "Puglia",
    indirizzo: "Piazza Sant'Oronzo, 73100 Lecce LE",
    lat: 40.3524, lng: 18.1714, categoria: "artigianato",
    tags: ["all'aperto", "serale"],
    orario_testo: "10:00–22:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Primo weekend del mese",
    descrizione: "Mercato di artigianato locale nel barocco centro di Lecce. Ceramiche, cartapesta, tessuti, gioielli artigianali e prodotti tipici salentini.",
    confidence: 82, fonte: "eventiesagre.it",
    get date() { return [...monthlyNthWeekday(1, 6), ...monthlyNthWeekday(1, 0)] },
  },

  // ═══ LIGURIA ═══
  {
    slug: "mercato-orientale-genova",
    nome: "Mercato Orientale",
    citta: "Genova", provincia: "GE", regione: "Liguria",
    indirizzo: "Via XX Settembre, 16121 Genova GE",
    lat: 44.4067, lng: 8.9410, categoria: "alimentare",
    tags: ["al chiuso", "produttori locali"],
    orario_testo: "7:30–13:00 · 15:30–19:30",
    ricorrenza: "giornaliero", ricorrenza_testo: "Ogni giorno tranne domenica",
    descrizione: "Mercato storico genovese in un ex convento ottocentesco. Basilico DOP, focaccia, pesce, formaggi e il famoso preboggion (miscela di erbe liguri).",
    confidence: 92, fonte: "Mercatini d'Italia",
    get date() { return dailyExceptSunday(60) },
  },

  // ═══ FRIULI VENEZIA GIULIA ═══
  {
    slug: "mercato-antiquariato-trieste",
    nome: "Mercatino dell'Antiquariato",
    citta: "Trieste", provincia: "TS", regione: "Friuli Venezia Giulia",
    indirizzo: "Piazza Sant'Antonio, 34122 Trieste TS",
    lat: 45.6495, lng: 13.7768, categoria: "antiquariato",
    tags: ["all'aperto", "collezionismo"],
    orario_testo: "9:00–18:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Terza domenica del mese",
    descrizione: "Mercato antiquario nel cuore della città mitteleuropea. Oggetti d'epoca, cristalli, argenti e curiosità asburgiche in piazza Sant'Antonio.",
    confidence: 84, fonte: "eventiesagre.it",
    get date() { return monthlyNthWeekday(3, 0) },
  },

  // ═══ TRENTINO-ALTO ADIGE ═══
  {
    slug: "mercato-piazza-erbe-bolzano",
    nome: "Mercato di Piazza delle Erbe",
    citta: "Bolzano", provincia: "BZ", regione: "Trentino-Alto Adige",
    indirizzo: "Piazza delle Erbe, 39100 Bolzano BZ",
    lat: 46.4986, lng: 11.3548, categoria: "alimentare",
    tags: ["all'aperto", "produttori locali"],
    orario_testo: "7:00–13:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Ogni giorno tranne domenica (sabato fino alle 13:30)",
    descrizione: "Mercato quotidiano di frutta e verdura nel centro di Bolzano. Speck, formaggi di malga, mele, pane tirolese e fiori freschi.",
    confidence: 95, fonte: "Mercatini d'Italia",
    get date() { return dailyExceptSunday(60) },
  },

  // ═══ SARDEGNA ═══
  {
    slug: "mercato-san-benedetto-cagliari",
    nome: "Mercato di San Benedetto",
    citta: "Cagliari", provincia: "CA", regione: "Sardegna",
    indirizzo: "Via Francesco Ferrara, 09126 Cagliari CA",
    lat: 39.2160, lng: 9.1212, categoria: "alimentare",
    tags: ["al chiuso", "produttori locali"],
    orario_testo: "7:00–14:00",
    ricorrenza: "giornaliero", ricorrenza_testo: "Ogni giorno tranne domenica",
    descrizione: "Il più grande mercato coperto d'Italia per superficie. Pesce freschissimo, bottarga, formaggi sardi, pane carasau e specialità dell'isola.",
    confidence: 91, fonte: "Mercatini d'Italia",
    get date() { return dailyExceptSunday(60) },
  },

  // ═══ UMBRIA ═══
  {
    slug: "mercato-antiquariato-perugia",
    nome: "Perugia Antiquaria",
    citta: "Perugia", provincia: "PG", regione: "Umbria",
    indirizzo: "Piazza Italia e Giardini Carducci, 06121 Perugia PG",
    lat: 43.1107, lng: 12.3908, categoria: "antiquariato",
    tags: ["all'aperto", "modernariato"],
    orario_testo: "9:00–19:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Ultimo weekend del mese",
    descrizione: "Mostra mercato di antiquariato e modernariato nei giardini panoramici di Perugia. Mobili, quadri, gioielli, libri antichi e curiosità umbre.",
    confidence: 83, fonte: "eventiesagre.it",
    get date() {
      const dates = []
      const now = today()
      for (let m = 0; m < 6; m++) {
        const year = now.getFullYear() + Math.floor((now.getMonth() + m) / 12)
        const month = (now.getMonth() + m) % 12
        const lastDay = new Date(year, month + 1, 0)
        while (lastDay.getDay() !== 6) lastDay.setDate(lastDay.getDate() - 1)
        if (lastDay >= today()) { dates.push(isoDate(lastDay)); dates.push(isoDate(addDays(lastDay, 1))) }
      }
      return dates
    },
  },

  // ═══ MARCHE ═══
  {
    slug: "mercatino-antiquariato-fano",
    nome: "Mercatino dell'Antiquariato",
    citta: "Fano", provincia: "PU", regione: "Marche",
    indirizzo: "Centro Storico, 61032 Fano PU",
    lat: 43.8430, lng: 13.0189, categoria: "antiquariato",
    tags: ["all'aperto", "collezionismo"],
    orario_testo: "9:00–19:00",
    ricorrenza: "mensile_giorno_fisso", ricorrenza_testo: "Seconda domenica del mese",
    descrizione: "Mercatino di antiquariato, vintage e collezionismo nel centro storico di Fano. Circa 100 espositori tra le mura romane e i palazzi rinascimentali.",
    confidence: 79, fonte: "eventiesagre.it",
    get date() { return monthlyNthWeekday(2, 0) },
  },

  // ═══ ABRUZZO ═══
  {
    slug: "mercato-piazza-duomo-laquila",
    nome: "Mercato di Piazza Duomo",
    citta: "L'Aquila", provincia: "AQ", regione: "Abruzzo",
    indirizzo: "Piazza del Duomo, 67100 L'Aquila AQ",
    lat: 42.3498, lng: 13.3995, categoria: "misto",
    tags: ["all'aperto", "produttori locali"],
    orario_testo: "8:00–13:30",
    ricorrenza: "settimanale", ricorrenza_testo: "Ogni sabato",
    descrizione: "Mercato settimanale nella piazza del Duomo ricostruita dopo il terremoto. Prodotti agricoli, artigianato locale, abbigliamento e specialità abruzzesi.",
    confidence: 78, fonte: "eventiesagre.it",
    get date() { return weeklyDates(6) },
  },
]

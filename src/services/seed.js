/**
 * Mercati d'Italia — Firestore Auto-Seeder
 *
 * Checks if the `mercati` collection is empty.
 * If so, writes all seed markets as documents.
 * Runs once on app startup — subsequent loads skip seeding.
 */
import { db } from '../lib/firebase'
import {
  collection, doc, getDocs, setDoc, query, limit,
} from 'firebase/firestore'
import { SEED_MARKETS } from '../data/sampleMarkets'

const SEED_STATUS_KEY = 'mercati_seed_status'

/**
 * Check if Firestore has data. If empty, seed it.
 * Returns { seeded: boolean, count: number }
 */
export async function autoSeed() {
  try {
    // Quick check: is there at least 1 document?
    const snap = await getDocs(query(collection(db, 'mercati'), limit(1)))

    if (!snap.empty) {
      console.log('[seed] Firestore already has data, skipping.')
      return { seeded: false, count: snap.size }
    }

    console.log(`[seed] Firestore is empty. Seeding ${SEED_MARKETS.length} markets...`)

    let count = 0
    const now = new Date().toISOString()

    for (const market of SEED_MARKETS) {
      // Resolve the getter for `date` (it's a computed property)
      const dates = market.date

      const data = {
        nome: market.nome,
        slug: market.slug,
        citta: market.citta,
        provincia: market.provincia,
        regione: market.regione,
        indirizzo: market.indirizzo,
        lat: market.lat,
        lng: market.lng,
        categoria: market.categoria,
        tags: market.tags,
        status: 'attivo',
        ricorrenza: market.ricorrenza,
        ricorrenza_testo: market.ricorrenza_testo,
        orario_testo: market.orario_testo,
        descrizione: market.descrizione,
        confidence: market.confidence,
        fonte: market.fonte,
        date: dates,
        prossima_data: dates[0] || null,
        creato_il: now,
        aggiornato_il: now,
      }

      await setDoc(doc(db, 'mercati', market.slug), data)
      count++
    }

    console.log(`[seed] ✓ Seeded ${count} markets into Firestore.`)
    return { seeded: true, count }

  } catch (error) {
    console.error('[seed] Error during auto-seed:', error)

    // If it's a permissions error, log helpful message
    if (error.code === 'permission-denied') {
      console.error(
        '[seed] Firestore permissions denied. Make sure your Firestore rules allow writes.\n' +
        'For development, you can temporarily set:\n' +
        '  rules_version = "2";\n' +
        '  service cloud.firestore {\n' +
        '    match /databases/{database}/documents {\n' +
        '      match /{document=**} {\n' +
        '        allow read, write: if true;\n' +
        '      }\n' +
        '    }\n' +
        '  }'
      )
    }

    return { seeded: false, count: 0, error: error.message }
  }
}

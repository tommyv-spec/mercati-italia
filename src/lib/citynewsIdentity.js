// Keep the reviewed origins and detail-path grammar aligned with citynews_urls.py.
// A publisher label alone cannot authorize an evidence link.
export const CITYNEWS_HOSTS = new Set([
  'arezzonotizie.it', 'baritoday.it', 'bolognatoday.it', 'bresciatoday.it',
  'cagliaritoday.it', 'casertanews.it', 'cataniatoday.it', 'cesenatoday.it',
  'ferraratoday.it', 'firenzetoday.it', 'forlitoday.it', 'frosinonetoday.it',
  'genovatoday.it', 'leccotoday.it', 'modenatoday.it', 'monzatoday.it',
  'novaratoday.it', 'padovatoday.it', 'palermotoday.it', 'parmatoday.it',
  'ravennatoday.it', 'riminitoday.it', 'romatoday.it', 'torinotoday.it',
  'trevisotoday.it', 'veneziatoday.it', 'vicenzatoday.it', 'viterbotoday.it',
])

const roundConstants = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]
const rotate = (word, bits) => (word >>> bits) | (word << (32 - bits))

// Only the bounded ASCII URLs admitted below reach this synchronous SHA-256.
// It reproduces the backend's URL identity without an async render, network
// request or new dependency; the source-byte proof remains the exporter's job.
function urlFingerprint(value) {
  const bytes = new Uint8Array(Math.ceil((value.length + 9) / 64) * 64)
  for (let i = 0; i < value.length; i++) bytes[i] = value.charCodeAt(i)
  bytes[value.length] = 0x80
  const data = new DataView(bytes.buffer)
  data.setUint32(bytes.length - 4, value.length * 8)
  const state = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
  const words = new Uint32Array(64)
  for (let offset = 0; offset < bytes.length; offset += 64) {
    for (let i = 0; i < 16; i++) words[i] = data.getUint32(offset + i * 4)
    for (let i = 16; i < 64; i++) {
      const x = words[i - 15], y = words[i - 2]
      words[i] = words[i - 16] + (rotate(x, 7) ^ rotate(x, 18) ^ (x >>> 3)) +
        words[i - 7] + (rotate(y, 17) ^ rotate(y, 19) ^ (y >>> 10))
    }
    let [a, b, c, d, e, f, g, h] = state
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25)) +
        ((e & f) ^ (~e & g)) + roundConstants[i] + words[i]) >>> 0
      const t2 = ((rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22)) +
        ((a & b) ^ (a & c) ^ (b & c))) >>> 0
      h = g; g = f; f = e; e = (d + t1) >>> 0
      d = c; c = b; b = a; a = (t1 + t2) >>> 0
    }
    const block = [a, b, c, d, e, f, g, h]
    for (let i = 0; i < state.length; i++) state[i] = (state[i] + block[i]) >>> 0
  }
  return state.map(word => word.toString(16).padStart(8, '0')).join('')
}

export function citynewsSourceIdentity(value) {
  if (typeof value !== 'string' || value.length < 20 || value.length > 1200) return null
  const match = value.match(/^https:\/\/www\.([a-z]+\.it)\/eventi\/(?!tipo\/|location\/)[A-Za-z0-9][A-Za-z0-9_/-]*\.html$/)
  if (!match || match[0] !== value || !CITYNEWS_HOSTS.has(match[1])) return null
  return [match[1], 'citynews-' + urlFingerprint(value).slice(0, 24)]
}

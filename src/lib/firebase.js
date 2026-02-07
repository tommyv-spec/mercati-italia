import { initializeApp } from 'firebase/app'
import { getFirestore } from 'firebase/firestore'
import { getAuth } from 'firebase/auth'

const firebaseConfig = {
  apiKey: "AIzaSyAHi_gsRDMwhs_clBLr49wIOqWtMO1NSPI",
  authDomain: "market-ef407.firebaseapp.com",
  projectId: "market-ef407",
  storageBucket: "market-ef407.firebasestorage.app",
  messagingSenderId: "636437525366",
  appId: "1:636437525366:web:e1f06455f240f059720057"
}

const app = initializeApp(firebaseConfig)
const db = getFirestore(app)
const auth = getAuth(app)

export { app, db, auth }
export const isFirebaseConfigured = () => true

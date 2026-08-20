declare module "firebase/auth" {
  export interface User {
    uid: string;
    email: string | null;
    displayName: string | null;
    photoURL: string | null;
    getIdToken(forceRefresh?: boolean): Promise<string>;
    toJSON(): object;
  }
  export interface Auth {
    currentUser: User | null;
  }
  export interface UserCredential {
    user: User;
  }
  export function getAuth(app?: any): Auth;
  export function signOut(auth: Auth | null): Promise<void>;
  export function onAuthStateChanged(
    auth: Auth | null,
    nextOrObserver: (user: User | null) => void
  ): () => void;
  export function createUserWithEmailAndPassword(
    auth: Auth | null,
    email: string,
    password: string
  ): Promise<UserCredential>;
  export function signInWithEmailAndPassword(
    auth: Auth | null,
    email: string,
    password: string
  ): Promise<UserCredential>;
}
declare module "firebase/app" {
  export interface FirebaseApp {
    name: string;
    options: Record<string, unknown>;
  }
  export function getApps(): FirebaseApp[];
  export function initializeApp(config: Record<string, string | undefined>): FirebaseApp;
}

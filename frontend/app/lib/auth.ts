const isBrowser = typeof window !== "undefined";
const STORAGE_KEY = "pesquisa_admin_senha";

export function getAdminPassword(): string | null {
  return isBrowser ? localStorage.getItem(STORAGE_KEY) : null;
}

export function setAdminPassword(password: string): void {
  if (isBrowser) localStorage.setItem(STORAGE_KEY, password);
}

export function isAdminLoggedIn(): boolean {
  return !!getAdminPassword();
}

export function logout(): void {
  if (isBrowser) localStorage.removeItem(STORAGE_KEY);
}

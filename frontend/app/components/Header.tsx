"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { logout } from "../lib/auth";

export default function Header() {
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/admin/login");
  }

  return (
    <header className="w-full" style={{ background: "#072a3c", borderBottom: "3px solid #c2a360" }}>
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
        <Link href="/admin" className="font-heading text-lg" style={{ color: "#c2a360" }}>
          Pesquisa de Satisfação Piaseg
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <button onClick={handleLogout} className="text-white/90 hover:text-white font-semibold cursor-pointer">
            Sair
          </button>
        </nav>
      </div>
    </header>
  );
}

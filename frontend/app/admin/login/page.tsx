"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { API } from "../../lib/api";
import { setAdminPassword } from "../../lib/auth";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) throw new Error("Senha inválida");
      setAdminPassword(password);
      router.push("/admin");
    } catch {
      setError("Senha inválida. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-dvh flex items-center justify-center px-4" style={{ background: "#072a3c" }}>
      <form onSubmit={handleSubmit} className="w-full max-w-sm bg-white rounded-xl p-8 shadow-xl">
        <h1 className="font-heading text-xl mb-1" style={{ color: "#072a3c" }}>
          Pesquisa de Satisfação
        </h1>
        <p className="text-sm text-gray-500 mb-6">Acesso restrito à equipe Piaseg.</p>
        {searchParams.get("sessao_expirada") && (
          <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
            Sua sessão expirou. Entre novamente.
          </p>
        )}
        <label className="block text-sm font-medium mb-1">Senha</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2"
          style={{ ["--tw-ring-color" as string]: "#c2a360" }}
          autoFocus
          required
        />
        {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg py-2.5 font-semibold text-white cursor-pointer disabled:opacity-60"
          style={{ background: "#072a3c" }}
        >
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

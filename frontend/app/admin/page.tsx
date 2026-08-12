"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiJson } from "../lib/api";
import { isAdminLoggedIn } from "../lib/auth";
import Header from "../components/Header";
import type { CampanhaSummary } from "../lib/types";

export default function AdminPage() {
  const router = useRouter();
  const [campanhas, setCampanhas] = useState<CampanhaSummary[] | null>(null);
  const [error, setError] = useState("");
  const [novoNome, setNovoNome] = useState("");
  const [criando, setCriando] = useState(false);
  const [aviso, setAviso] = useState("");
  const [linkCopiado, setLinkCopiado] = useState<string | null>(null);
  const [origin, setOrigin] = useState("");

  useEffect(() => {
    if (!isAdminLoggedIn()) {
      router.push("/admin/login");
      return;
    }
    setOrigin(window.location.origin);
    carregar();
  }, [router]);

  async function carregar() {
    try {
      const data = await apiJson<CampanhaSummary[]>("/admin/campanhas");
      setCampanhas(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar campanhas");
    }
  }

  async function criarCampanha(e: React.FormEvent) {
    e.preventDefault();
    if (!novoNome.trim()) return;
    setCriando(true);
    setError("");
    setAviso("");
    try {
      await apiJson("/admin/campanhas", { method: "POST", body: JSON.stringify({ nome: novoNome.trim() }) });
      setNovoNome("");
      setAviso("Campanha criada. Copie o link abaixo e compartilhe com os franqueados (site, WhatsApp, onde preferir).");
      await carregar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar campanha");
    } finally {
      setCriando(false);
    }
  }

  async function excluir(id: string, nome: string) {
    if (!confirm(`Excluir a campanha "${nome}" e todas as suas respostas? Essa ação não pode ser desfeita.`)) return;
    setError("");
    setAviso("");
    try {
      await apiJson(`/admin/campanhas/${id}`, { method: "DELETE" });
      setAviso(`Campanha "${nome}" excluída.`);
      await carregar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao excluir campanha");
    }
  }

  async function copiarLink(id: string) {
    const link = `${origin}/responder/${id}`;
    await navigator.clipboard.writeText(link);
    setLinkCopiado(id);
    setTimeout(() => setLinkCopiado(null), 2000);
  }

  return (
    <>
      <Header />
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
        <h1 className="font-heading text-2xl mb-6" style={{ color: "#072a3c" }}>
          Campanhas de Pesquisa
        </h1>

        <form onSubmit={criarCampanha} className="bg-white rounded-xl p-5 shadow mb-6 flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Nome da nova campanha</label>
            <input
              value={novoNome}
              onChange={(e) => setNovoNome(e.target.value)}
              placeholder="Ex: Pesquisa de Satisfação 2026"
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
          <button
            type="submit"
            disabled={criando}
            className="rounded-lg px-5 py-2.5 font-semibold text-white cursor-pointer disabled:opacity-60"
            style={{ background: "#072a3c" }}
          >
            {criando ? "Criando..." : "Nova Campanha"}
          </button>
        </form>

        {aviso && <p className="text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 mb-4">{aviso}</p>}
        {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">{error}</p>}

        {campanhas === null ? (
          <p className="text-gray-500">Carregando...</p>
        ) : campanhas.length === 0 ? (
          <p className="text-gray-500">Nenhuma campanha criada ainda.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {campanhas.map((c) => (
              <div key={c.id} className="bg-white rounded-xl p-5 shadow flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
                <div className="flex-1 min-w-0">
                  <Link href={`/admin/campanhas/${c.id}`} className="font-semibold hover:underline" style={{ color: "#072a3c" }}>
                    {c.nome}
                  </Link>
                  <p className="text-xs text-gray-500">
                    Criada em {new Date(c.criada_em).toLocaleDateString("pt-BR")} · {c.total_respondidos} resposta(s)
                  </p>
                  {origin && (
                    <p className="text-xs text-gray-400 mt-1 truncate">
                      {origin}/responder/{c.id}
                    </p>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => copiarLink(c.id)}
                    className="rounded-lg px-4 py-2 text-sm font-semibold text-white cursor-pointer"
                    style={{ background: "#c2a360" }}
                  >
                    {linkCopiado === c.id ? "Link copiado!" : "Copiar link"}
                  </button>
                  <Link
                    href={`/admin/campanhas/${c.id}`}
                    className="rounded-lg px-4 py-2 text-sm font-semibold border cursor-pointer"
                    style={{ borderColor: "#072a3c", color: "#072a3c" }}
                  >
                    Ver resultados
                  </Link>
                  <button
                    onClick={() => excluir(c.id, c.nome)}
                    className="rounded-lg px-4 py-2 text-sm font-semibold border cursor-pointer text-red-700 border-red-300"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}

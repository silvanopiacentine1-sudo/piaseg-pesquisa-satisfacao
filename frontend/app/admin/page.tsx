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
  const [enviandoId, setEnviandoId] = useState<string | null>(null);
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    if (!isAdminLoggedIn()) {
      router.push("/admin/login");
      return;
    }
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
      const resultado = await apiJson<{
        franqueados_incluidos: number;
        franqueados_sem_email: string[];
      }>("/admin/campanhas", {
        method: "POST",
        body: JSON.stringify({ nome: novoNome.trim() }),
      });
      setNovoNome("");
      let msg = `Campanha criada com ${resultado.franqueados_incluidos} franqueado(s).`;
      if (resultado.franqueados_sem_email.length > 0) {
        msg += ` ${resultado.franqueados_sem_email.length} franqueado(s) sem e-mail cadastrado ficaram de fora: ${resultado.franqueados_sem_email.join(", ")}.`;
      }
      setAviso(msg);
      await carregar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar campanha");
    } finally {
      setCriando(false);
    }
  }

  async function enviar(id: string) {
    if (!confirm("Enviar o e-mail da pesquisa para todos os franqueados pendentes desta campanha?")) return;
    setEnviandoId(id);
    setError("");
    setAviso("");
    try {
      const resultado = await apiJson<{ enviados: number; falhas: { franqueado_nome: string; erro: string }[] }>(
        `/admin/campanhas/${id}/enviar`,
        { method: "POST" }
      );
      let msg = `${resultado.enviados} e-mail(s) enviado(s).`;
      if (resultado.falhas.length > 0) {
        msg += ` Falhou para: ${resultado.falhas.map((f) => f.franqueado_nome).join(", ")}.`;
      }
      setAviso(msg);
      await carregar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao enviar e-mails");
    } finally {
      setEnviandoId(null);
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
                <div className="flex-1">
                  <Link href={`/admin/campanhas/${c.id}`} className="font-semibold hover:underline" style={{ color: "#072a3c" }}>
                    {c.nome}
                  </Link>
                  <p className="text-xs text-gray-500">
                    Criada em {new Date(c.criada_em).toLocaleDateString("pt-BR")} · {c.total_franqueados} franqueado(s)
                  </p>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span>
                    <strong>{c.total_enviados}</strong>/{c.total_franqueados} enviados
                  </span>
                  <span>
                    <strong>{c.total_respondidos}</strong> respondidos
                  </span>
                </div>
                <div className="flex gap-2">
                  {c.total_enviados < c.total_franqueados && (
                    <button
                      onClick={() => enviar(c.id)}
                      disabled={enviandoId === c.id}
                      className="rounded-lg px-4 py-2 text-sm font-semibold text-white cursor-pointer disabled:opacity-60"
                      style={{ background: "#c2a360" }}
                    >
                      {enviandoId === c.id ? "Enviando..." : "Enviar e-mails"}
                    </button>
                  )}
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

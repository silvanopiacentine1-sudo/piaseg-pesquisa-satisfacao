"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiJson, downloadFile } from "../../../lib/api";
import { isAdminLoggedIn } from "../../../lib/auth";
import Header from "../../../components/Header";
import type { ResultadosCampanha } from "../../../lib/types";

const CATEGORIA_COLOR = "#072a3c";
const NPS_COLORS = { detratores: "#d03b3b", neutros: "#898781", promotores: "#0ca30c" };

export default function ResultadosPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [dados, setDados] = useState<ResultadosCampanha | null>(null);
  const [error, setError] = useState("");
  const [exportando, setExportando] = useState(false);

  useEffect(() => {
    if (!isAdminLoggedIn()) {
      router.push("/admin/login");
      return;
    }
    apiJson<ResultadosCampanha>(`/admin/campanhas/${id}/resultados`)
      .then(setDados)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar resultados"));
  }, [id, router]);

  async function exportar() {
    setExportando(true);
    try {
      await downloadFile(`/admin/campanhas/${id}/export`, `pesquisa_${dados?.campanha.nome ?? id}.xlsx`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao exportar");
    } finally {
      setExportando(false);
    }
  }

  if (error) {
    return (
      <>
        <Header />
        <main className="max-w-5xl w-full mx-auto px-4 py-8">
          <p className="text-red-600">{error}</p>
        </main>
      </>
    );
  }

  if (!dados) {
    return (
      <>
        <Header />
        <main className="max-w-5xl w-full mx-auto px-4 py-8">
          <p className="text-gray-500">Carregando...</p>
        </main>
      </>
    );
  }

  const { campanha, media_por_categoria, nps, comentarios, taxa_resposta } = dados;
  const npsTotal = nps.promotores + nps.neutros + nps.detratores;

  return (
    <>
      <Header />
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
        <Link href="/admin" className="text-sm hover:underline" style={{ color: "#072a3c" }}>
          ← Todas as campanhas
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-3 mt-2 mb-6">
          <h1 className="font-heading text-2xl" style={{ color: "#072a3c" }}>
            {campanha.nome}
          </h1>
          <button
            onClick={exportar}
            disabled={exportando}
            className="rounded-lg px-4 py-2 text-sm font-semibold border cursor-pointer disabled:opacity-60"
            style={{ borderColor: "#072a3c", color: "#072a3c" }}
          >
            {exportando ? "Exportando..." : "Exportar Excel"}
          </button>
        </div>

        {/* Stat tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <StatTile label="Taxa de resposta" value={`${taxa_resposta}%`} sub={`${campanha.total_respondidos} de ${campanha.total_franqueados}`} />
          <StatTile label="E-mails enviados" value={String(campanha.total_enviados)} sub={`de ${campanha.total_franqueados} franqueados`} />
          <StatTile label="NPS" value={nps.score !== null ? String(nps.score) : "—"} sub={`${npsTotal} resposta(s)`} />
        </div>

        {/* Média por categoria */}
        <section className="bg-white rounded-xl p-6 shadow mb-8">
          <h2 className="font-heading text-lg mb-4" style={{ color: "#072a3c" }}>
            Média por categoria (escala de 1 a 5)
          </h2>
          {media_por_categoria.length === 0 ? (
            <p className="text-sm text-gray-500">Ainda não há respostas suficientes.</p>
          ) : (
            <div className="flex flex-col gap-3">
              {media_por_categoria.map((c) => (
                <div key={c.categoria} className="flex items-center gap-3">
                  <span className="w-56 shrink-0 text-sm text-gray-700">{c.categoria}</span>
                  <div className="flex-1 h-4 rounded-full" style={{ background: "#e1e0d9" }}>
                    <div
                      className="h-4 rounded-full flex items-center justify-end pr-2"
                      style={{ width: `${((c.media ?? 0) / 5) * 100}%`, background: CATEGORIA_COLOR, minWidth: "2rem" }}
                    >
                      <span className="text-xs font-semibold text-white">{c.media ?? "—"}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* NPS breakdown */}
        <section className="bg-white rounded-xl p-6 shadow mb-8">
          <h2 className="font-heading text-lg mb-4" style={{ color: "#072a3c" }}>
            Net Promoter Score (recomendação)
          </h2>
          {npsTotal === 0 ? (
            <p className="text-sm text-gray-500">Ainda não há respostas suficientes.</p>
          ) : (
            <>
              <div className="flex h-6 rounded-full overflow-hidden" style={{ gap: 2 }}>
                {(["detratores", "neutros", "promotores"] as const).map((key) => {
                  const count = nps[key];
                  if (count === 0) return null;
                  return (
                    <div
                      key={key}
                      style={{ width: `${(count / npsTotal) * 100}%`, background: NPS_COLORS[key] }}
                      title={`${key}: ${count}`}
                    />
                  );
                })}
              </div>
              <div className="flex gap-6 mt-3 text-sm">
                <Legend color={NPS_COLORS.detratores} label={`Detratores (0–6)`} value={nps.detratores} />
                <Legend color={NPS_COLORS.neutros} label={`Neutros (7–8)`} value={nps.neutros} />
                <Legend color={NPS_COLORS.promotores} label={`Promotores (9–10)`} value={nps.promotores} />
              </div>
            </>
          )}
        </section>

        {/* Comentários */}
        <section className="bg-white rounded-xl p-6 shadow">
          <h2 className="font-heading text-lg mb-4" style={{ color: "#072a3c" }}>
            Respostas abertas ({comentarios.length})
          </h2>
          {comentarios.length === 0 ? (
            <p className="text-sm text-gray-500">Nenhum comentário ainda.</p>
          ) : (
            <div className="flex flex-col gap-4">
              {comentarios.map((c, i) => (
                <div key={i} className="border-b border-gray-100 pb-4 last:border-0 last:pb-0">
                  <p className="text-xs text-gray-500 mb-1">
                    <span className="font-semibold" style={{ color: "#072a3c" }}>
                      {c.franqueado_nome}
                    </span>
                    {" · "}
                    {c.pergunta_texto}
                  </p>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{c.texto}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </>
  );
}

function StatTile({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="bg-white rounded-xl p-5 shadow">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-semibold" style={{ color: "#072a3c" }}>
        {value}
      </p>
      <p className="text-xs text-gray-400 mt-1">{sub}</p>
    </div>
  );
}

function Legend({ color, label, value }: { color: string; label: string; value: number }) {
  return (
    <span className="flex items-center gap-2">
      <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
      {label}: <strong>{value}</strong>
    </span>
  );
}

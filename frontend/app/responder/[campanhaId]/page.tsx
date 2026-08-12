"use client";

import { use, useEffect, useState } from "react";
import { API } from "../../lib/api";
import type { Pesquisa } from "../../lib/types";

const SUFIXO_COMENTARIO = "__comentario";

function jaRespondeuLocalmente(campanhaId: string): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(`pesquisa_respondida_${campanhaId}`) === "1";
}

function marcarComoRespondida(campanhaId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(`pesquisa_respondida_${campanhaId}`, "1");
}

export default function ResponderPage({ params }: { params: Promise<{ campanhaId: string }> }) {
  const { campanhaId } = use(params);
  const [dados, setDados] = useState<Pesquisa | null>(null);
  const [erroCarregamento, setErroCarregamento] = useState("");
  const [respostas, setRespostas] = useState<Record<string, number | string>>({});
  const [enviando, setEnviando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [jaRespondeu, setJaRespondeu] = useState(false);

  useEffect(() => {
    setJaRespondeu(jaRespondeuLocalmente(campanhaId));
    fetch(`${API}/pesquisa/${campanhaId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Pesquisa não encontrada.");
        return res.json();
      })
      .then(setDados)
      .catch((e) => setErroCarregamento(e.message));
  }, [campanhaId]);

  function setValor(perguntaId: string, valor: number | string) {
    setRespostas((prev) => ({ ...prev, [perguntaId]: valor }));
  }

  async function enviar() {
    if (!dados) return;
    const faltando = dados.perguntas.filter((p) => p.tipo !== "texto" && respostas[p.id] === undefined);
    if (faltando.length > 0) {
      setErroEnvio("Responda todas as perguntas de escala antes de enviar.");
      document.getElementById(faltando[0].id)?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    setEnviando(true);
    setErroEnvio("");
    try {
      const res = await fetch(`${API}/pesquisa/${campanhaId}/respostas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ respostas }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Não foi possível enviar suas respostas.");
      }
      marcarComoRespondida(campanhaId);
      setEnviado(true);
    } catch (e) {
      setErroEnvio(e instanceof Error ? e.message : "Erro ao enviar");
    } finally {
      setEnviando(false);
    }
  }

  if (erroCarregamento) {
    return (
      <CenteredCard>
        <p className="text-gray-700">{erroCarregamento}</p>
      </CenteredCard>
    );
  }

  if (!dados) {
    return (
      <CenteredCard>
        <p className="text-gray-500">Carregando...</p>
      </CenteredCard>
    );
  }

  if (jaRespondeu || enviado) {
    return (
      <CenteredCard>
        <h1 className="font-heading text-xl mb-2" style={{ color: "#072a3c" }}>
          Obrigado!
        </h1>
        <p className="text-gray-600">Sua resposta já foi registrada. Agradecemos por dedicar seu tempo à pesquisa.</p>
      </CenteredCard>
    );
  }

  let categoriaAtual = "";

  return (
    <div className="min-h-dvh" style={{ background: "#f6f6f6" }}>
      <div style={{ background: "#072a3c" }} className="py-8 px-4 text-center">
        <h1 className="font-heading text-xl" style={{ color: "#c2a360" }}>
          {dados.campanha_nome}
        </h1>
        <p className="text-white/80 text-sm mt-2">Sua opinião é muito importante para nós.</p>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {dados.perguntas.map((p) => {
          const novaCategoria = p.categoria !== categoriaAtual;
          categoriaAtual = p.categoria;
          return (
            <div key={p.id}>
              {novaCategoria && (
                <h2 className="font-heading text-sm uppercase tracking-wide mt-8 mb-3" style={{ color: "#a4854a" }}>
                  {p.categoria}
                </h2>
              )}
              <div id={p.id} className="bg-white rounded-xl p-5 shadow mb-3">
                <p className="text-sm font-medium text-gray-800 mb-3">{p.texto}</p>
                {p.tipo === "escala5" && <Escala5 valor={respostas[p.id] as number} onChange={(v) => setValor(p.id, v)} />}
                {p.tipo === "nps" && <EscalaNps valor={respostas[p.id] as number} onChange={(v) => setValor(p.id, v)} />}
                {p.tipo === "texto" && (
                  <textarea
                    value={(respostas[p.id] as string) || ""}
                    onChange={(e) => setValor(p.id, e.target.value)}
                    rows={3}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    placeholder="Opcional"
                  />
                )}
                {(p.tipo === "escala5" || p.tipo === "nps") && (
                  <textarea
                    value={(respostas[p.id + SUFIXO_COMENTARIO] as string) || ""}
                    onChange={(e) => setValor(p.id + SUFIXO_COMENTARIO, e.target.value)}
                    rows={2}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mt-3"
                    placeholder="Comente sua nota (opcional)"
                  />
                )}
              </div>
            </div>
          );
        })}

        {erroEnvio && <p className="text-sm text-red-600 mb-4">{erroEnvio}</p>}

        <button
          onClick={enviar}
          disabled={enviando}
          className="w-full rounded-lg py-3 font-semibold text-white cursor-pointer disabled:opacity-60"
          style={{ background: "#072a3c" }}
        >
          {enviando ? "Enviando..." : "Enviar respostas"}
        </button>
      </div>
    </div>
  );
}

function Escala5({ valor, onChange }: { valor: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-2">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className="flex-1 h-10 rounded-lg font-semibold text-sm cursor-pointer border"
          style={
            valor === n
              ? { background: "#072a3c", color: "white", borderColor: "#072a3c" }
              : { background: "white", color: "#072a3c", borderColor: "#d1d5db" }
          }
        >
          {n}
        </button>
      ))}
    </div>
  );
}

function EscalaNps({ valor, onChange }: { valor: number; onChange: (v: number) => void }) {
  return (
    <div>
      <div className="flex gap-1 flex-wrap">
        {Array.from({ length: 11 }, (_, n) => n).map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className="w-9 h-9 rounded-lg font-semibold text-xs cursor-pointer border"
            style={
              valor === n
                ? { background: "#072a3c", color: "white", borderColor: "#072a3c" }
                : { background: "white", color: "#072a3c", borderColor: "#d1d5db" }
            }
          >
            {n}
          </button>
        ))}
      </div>
      <div className="flex justify-between text-[11px] text-gray-400 mt-1">
        <span>Nada provável</span>
        <span>Extremamente provável</span>
      </div>
    </div>
  );
}

function CenteredCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex items-center justify-center px-4" style={{ background: "#072a3c" }}>
      <div className="w-full max-w-md bg-white rounded-xl p-8 shadow-xl text-center">{children}</div>
    </div>
  );
}

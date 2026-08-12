"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson } from "../../lib/api";
import { isAdminLoggedIn } from "../../lib/auth";
import Header from "../../components/Header";
import type { Pergunta, TipoPergunta } from "../../lib/types";

const CATEGORIAS = ["Geral", "Comercial", "Operacional", "Marketing", "Comentários"];
const TIPOS: { valor: TipoPergunta; label: string }[] = [
  { valor: "escala10", label: "Escala de 0 a 10" },
  { valor: "texto", label: "Texto livre" },
];

function slugify(texto: string, existentes: Set<string>): string {
  const base =
    texto
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 40) || "pergunta";
  let slug = base;
  let i = 2;
  while (existentes.has(slug)) {
    slug = `${base}_${i}`;
    i++;
  }
  return slug;
}

export default function PerguntasPage() {
  const router = useRouter();
  const [perguntas, setPerguntas] = useState<Pergunta[] | null>(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (!isAdminLoggedIn()) {
      router.push("/admin/login");
      return;
    }
    apiJson<Pergunta[]>("/admin/perguntas")
      .then(setPerguntas)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar perguntas"));
  }, [router]);

  function atualizar(index: number, campo: keyof Pergunta, valor: string) {
    if (!perguntas) return;
    const copia = [...perguntas];
    copia[index] = { ...copia[index], [campo]: valor };
    setPerguntas(copia);
  }

  function remover(index: number) {
    if (!perguntas) return;
    setPerguntas(perguntas.filter((_, i) => i !== index));
  }

  function adicionar(categoria: string) {
    if (!perguntas) return;
    setPerguntas([
      ...perguntas,
      { id: "", categoria, tipo: categoria === "Comentários" ? "texto" : "escala10", texto: "" },
    ]);
  }

  async function salvar() {
    if (!perguntas) return;
    if (perguntas.some((p) => !p.texto.trim())) {
      setError("Toda pergunta precisa ter um texto.");
      return;
    }
    setSalvando(true);
    setError("");
    setAviso("");
    try {
      const idsExistentes = new Set(perguntas.filter((p) => p.id).map((p) => p.id));
      const comIds = perguntas.map((p) => {
        if (p.id.trim()) return p;
        const novoId = slugify(p.texto, idsExistentes);
        idsExistentes.add(novoId);
        return { ...p, id: novoId };
      });
      const salvo = await apiJson<Pergunta[]>("/admin/perguntas", {
        method: "PUT",
        body: JSON.stringify({ perguntas: comIds }),
      });
      setPerguntas(salvo);
      setAviso("Perguntas salvas. Vale só para as próximas campanhas — as já criadas mantêm o questionário original.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSalvando(false);
    }
  }

  if (error && !perguntas) {
    return (
      <>
        <Header />
        <main className="max-w-3xl w-full mx-auto px-4 py-8">
          <p className="text-red-600">{error}</p>
        </main>
      </>
    );
  }

  if (!perguntas) {
    return (
      <>
        <Header />
        <main className="max-w-3xl w-full mx-auto px-4 py-8">
          <p className="text-gray-500">Carregando...</p>
        </main>
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8">
        <h1 className="font-heading text-2xl mb-2" style={{ color: "#072a3c" }}>
          Perguntas da Pesquisa
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          Esse é o questionário que será usado na próxima campanha que você criar. Alterar aqui não muda campanhas já existentes.
          Perguntas de <strong>Escala de 0 a 10</strong> já ganham automaticamente um campo de comentário livre
          opcional ("Comente sua nota") no formulário — não precisa criar isso manualmente.
        </p>

        {aviso && <p className="text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 mb-4">{aviso}</p>}
        {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">{error}</p>}

        {CATEGORIAS.map((categoria) => (
          <section key={categoria} className="mb-8">
            <h2 className="font-heading text-lg mb-3" style={{ color: "#072a3c" }}>
              {categoria}
            </h2>
            <div className="flex flex-col gap-3">
              {perguntas.map((p, i) =>
                p.categoria === categoria ? (
                  <div key={i} className="bg-white rounded-xl p-4 shadow flex flex-col gap-2">
                    <textarea
                      value={p.texto}
                      onChange={(e) => atualizar(i, "texto", e.target.value)}
                      rows={2}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    />
                    <div className="flex items-center gap-3">
                      <select
                        value={p.tipo}
                        onChange={(e) => atualizar(i, "tipo", e.target.value)}
                        className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm"
                      >
                        {TIPOS.map((t) => (
                          <option key={t.valor} value={t.valor}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                      <select
                        value={p.categoria}
                        onChange={(e) => atualizar(i, "categoria", e.target.value)}
                        className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm"
                      >
                        {CATEGORIAS.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => remover(i)}
                        className="ml-auto text-sm font-semibold text-red-700 cursor-pointer"
                      >
                        Remover
                      </button>
                    </div>
                  </div>
                ) : null
              )}
              <button
                onClick={() => adicionar(categoria)}
                className="self-start text-sm font-semibold cursor-pointer"
                style={{ color: "#072a3c" }}
              >
                + Adicionar pergunta em {categoria}
              </button>
            </div>
          </section>
        ))}

        <button
          onClick={salvar}
          disabled={salvando}
          className="w-full rounded-lg py-3 font-semibold text-white cursor-pointer disabled:opacity-60"
          style={{ background: "#072a3c" }}
        >
          {salvando ? "Salvando..." : "Salvar alterações"}
        </button>
      </main>
    </>
  );
}

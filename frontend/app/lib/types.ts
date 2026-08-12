export type TipoPergunta = "escala5" | "nps" | "texto";

export interface Pergunta {
  id: string;
  categoria: string;
  tipo: TipoPergunta;
  texto: string;
}

export interface CampanhaSummary {
  id: string;
  nome: string;
  criada_em: string;
  perguntas: Pergunta[];
  total_franqueados: number;
  total_enviados: number;
  total_respondidos: number;
}

export interface MediaCategoria {
  categoria: string;
  media: number | null;
}

export interface NpsResumo {
  promotores: number;
  neutros: number;
  detratores: number;
  score: number | null;
  total: number;
}

export interface Comentario {
  franqueado_nome: string;
  pergunta_id: string;
  pergunta_texto: string;
  texto: string;
  respondido_em: string | null;
}

export interface ResultadosCampanha {
  campanha: CampanhaSummary;
  media_por_categoria: MediaCategoria[];
  distribuicoes: Record<string, Record<string, number>>;
  nps: NpsResumo;
  comentarios: Comentario[];
  taxa_resposta: number;
}

export interface RespostaToken {
  franqueado_nome: string;
  campanha_nome: string;
  perguntas: Pergunta[];
  respondido: boolean;
}

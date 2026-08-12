# Questionário ativo da Pesquisa de Satisfação de Franqueados.
# Cada campanha nova grava uma cópia (snapshot) dessa lista no momento da criação,
# então mudar este arquivo não altera campanhas já criadas — só as futuras.
#
# As categorias espelham as áreas reais da franqueadora (mesmos departamentos do
# Piaseg Chamados) para que o painel possa mostrar uma nota por área: Geral,
# Comercial, Operacional e Marketing. Não mudar esses 4 nomes sem atualizar
# também AREA_ORDER no frontend (app/lib/areas.ts).

QUESTIONS: list[dict] = [
    # --- Geral: relacionamento com a franqueadora como um todo ---
    {"id": "satisfacao_geral", "categoria": "Geral", "tipo": "escala5",
     "texto": "De forma geral, estou satisfeito(a) como franqueado(a) Piaseg."},
    {"id": "comunicacao_clara", "categoria": "Geral", "tipo": "escala5",
     "texto": "A franqueadora se comunica de forma clara e frequente sobre novidades e mudanças."},
    {"id": "feedback_ouvido", "categoria": "Geral", "tipo": "escala5",
     "texto": "Minhas sugestões e feedbacks são ouvidos e levados em consideração."},
    {"id": "relacionamento_lideranca", "categoria": "Geral", "tipo": "escala5",
     "texto": "Sinto que tenho um bom relacionamento com a liderança da Piaseg."},
    {"id": "orgulho_marca", "categoria": "Geral", "tipo": "escala5",
     "texto": "Tenho orgulho de fazer parte da rede Piaseg."},
    {"id": "retorno_financeiro", "categoria": "Geral", "tipo": "escala5",
     "texto": "O modelo de negócio da Piaseg oferece um retorno financeiro satisfatório."},
    {"id": "custos_justos", "categoria": "Geral", "tipo": "escala5",
     "texto": "Os custos e taxas cobrados pela franqueadora são justos em relação ao que recebo em troca."},
    {"id": "nps", "categoria": "Geral", "tipo": "nps",
     "texto": "Em uma escala de 0 a 10, o quanto você recomendaria a Piaseg para outro empreendedor?"},

    # --- Comercial ---
    {"id": "comercial_apoio_negocios", "categoria": "Comercial", "tipo": "escala5",
     "texto": "A equipe Comercial me apoia bem na geração de novos negócios."},
    {"id": "comercial_orientacao", "categoria": "Comercial", "tipo": "escala5",
     "texto": "Recebo orientação comercial (estratégias de venda, produtos, metas) de forma clara."},
    {"id": "comercial_agilidade", "categoria": "Comercial", "tipo": "escala5",
     "texto": "O suporte da equipe Comercial é ágil quando eu preciso."},

    # --- Operacional ---
    {"id": "operacional_treinamento", "categoria": "Operacional", "tipo": "escala5",
     "texto": "O treinamento inicial me preparou bem para operar a franquia."},
    {"id": "operacional_suporte", "categoria": "Operacional", "tipo": "escala5",
     "texto": "Recebo suporte operacional (dúvidas do dia a dia) de forma rápida e eficiente."},
    {"id": "operacional_sistemas", "categoria": "Operacional", "tipo": "escala5",
     "texto": "Os sistemas disponibilizados (ex: Piazinho, sistema financeiro) facilitam meu trabalho."},
    {"id": "operacional_suporte_tecnico", "categoria": "Operacional", "tipo": "escala5",
     "texto": "O suporte técnico/sistemas resolve meus problemas com agilidade."},

    # --- Marketing ---
    {"id": "marketing_geracao_negocios", "categoria": "Marketing", "tipo": "escala5",
     "texto": "As ações de marketing da franqueadora ajudam a gerar novos negócios para minha unidade."},
    {"id": "marketing_materiais", "categoria": "Marketing", "tipo": "escala5",
     "texto": "Os materiais e campanhas fornecidos têm boa qualidade."},
    {"id": "marketing_receptividade", "categoria": "Marketing", "tipo": "escala5",
     "texto": "A equipe de Marketing é receptiva às minhas sugestões e necessidades locais."},

    # --- Comentários (espaço livre) ---
    {"id": "pontos_fortes", "categoria": "Comentários", "tipo": "texto",
     "texto": "O que a Piaseg faz muito bem, na sua opinião?"},
    {"id": "pontos_melhorar", "categoria": "Comentários", "tipo": "texto",
     "texto": "O que a Piaseg poderia melhorar?"},
    {"id": "comentario_livre", "categoria": "Comentários", "tipo": "texto",
     "texto": "Espaço livre: escreva aqui qualquer sugestão, crítica ou elogio que queira compartilhar."},
]

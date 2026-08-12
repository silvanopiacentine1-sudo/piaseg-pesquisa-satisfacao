import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openpyxl import Workbook
from pydantic import BaseModel

from questions import DEFAULT_QUESTIONS

load_dotenv()

# ---------------------------------------------------------------------------
# Trava de segurança: no Render, DATA_DIR é obrigatório (mesmo padrão dos
# outros projetos Piaseg) — sem isso, um deploy sem a env var configurada
# gravaria dados no container efêmero e perderia tudo silenciosamente.
# ---------------------------------------------------------------------------
if os.getenv("RENDER") and not os.getenv("DATA_DIR"):
    raise RuntimeError(
        "DATA_DIR não está configurado no Render. Isso faria o app gravar dados "
        "fora do disco persistente, perdendo tudo no próximo deploy. Configure a "
        "env var DATA_DIR=/data no serviço antes de tentar de novo."
    )

app = FastAPI(title="Piaseg Pesquisa de Satisfação")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(APP_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)

CAMPANHAS_FILE = DATA_DIR / "campanhas.json"
RESPOSTAS_FILE = DATA_DIR / "respostas.json"
PERGUNTAS_FILE = DATA_DIR / "perguntas.json"
BACKUPS_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 30
_BACKUP_FILES = ["campanhas.json", "respostas.json", "perguntas.json"]

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TIPOS_VALIDOS = {"escala5", "nps", "texto"}

# Toda pergunta de escala (escala5/nps) ganha automaticamente um campo de
# comentário livre opcional no formulário, guardado sob "{id}__comentario"
# nas respostas — não é uma pergunta própria, por isso não entra em
# perguntas.json nem precisa ser criada manualmente pelo admin.
SUFIXO_COMENTARIO = "__comentario"


def _load(path: Path) -> list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save(path: Path, data: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_startup_backup() -> None:
    """Snapshot dos dados a cada subida do app (= cada deploy). Só roda com
    DATA_DIR explicitamente setado (produção), nunca em dev local."""
    if not os.getenv("DATA_DIR"):
        return
    snapshot_dir = BACKUPS_DIR / datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for filename in _BACKUP_FILES:
        source = DATA_DIR / filename
        if source.exists():
            shutil.copy2(source, snapshot_dir / filename)

    existing = sorted(p for p in BACKUPS_DIR.iterdir() if p.is_dir())
    for old in existing[:-MAX_BACKUPS]:
        shutil.rmtree(old, ignore_errors=True)


_run_startup_backup()


# ---------------------------------------------------------------------------
# Auth admin (senha única compartilhada, sem cadastro de usuários)
# ---------------------------------------------------------------------------

bearer = HTTPBearer()


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> None:
    if not ADMIN_PASSWORD or credentials.credentials != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha inválida")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AdminLogin(BaseModel):
    password: str


class CampanhaCreate(BaseModel):
    nome: str


class RespostaSubmit(BaseModel):
    respostas: dict[str, Any]


class PerguntaIn(BaseModel):
    id: str
    categoria: str
    tipo: str
    texto: str


class PerguntasUpdate(BaseModel):
    perguntas: list[PerguntaIn]


# ---------------------------------------------------------------------------
# Perguntas (template editável usado nas próximas campanhas)
# ---------------------------------------------------------------------------

def _load_perguntas_atuais() -> list[dict]:
    if not PERGUNTAS_FILE.exists():
        _save(PERGUNTAS_FILE, DEFAULT_QUESTIONS)
        return DEFAULT_QUESTIONS
    return json.loads(PERGUNTAS_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers de campanha/resposta
# ---------------------------------------------------------------------------

def _campanha_or_404(campanha_id: str) -> dict:
    campanha = next((c for c in _load(CAMPANHAS_FILE) if c["id"] == campanha_id), None)
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campanha


def _respostas_da_campanha(campanha_id: str) -> list[dict]:
    return [r for r in _load(RESPOSTAS_FILE) if r["campanha_id"] == campanha_id]


def _campanha_summary(campanha: dict) -> dict:
    return {**campanha, "total_respondidos": len(_respostas_da_campanha(campanha["id"]))}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Admin login
# ---------------------------------------------------------------------------

@app.post("/admin/login")
def admin_login(body: AdminLogin):
    if not ADMIN_PASSWORD or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Senha inválida")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Perguntas (admin) — template usado na criação de novas campanhas
# ---------------------------------------------------------------------------

@app.get("/admin/perguntas")
def get_perguntas(_: None = Depends(require_admin)):
    return _load_perguntas_atuais()


@app.put("/admin/perguntas")
def update_perguntas(body: PerguntasUpdate, _: None = Depends(require_admin)):
    if not body.perguntas:
        raise HTTPException(status_code=400, detail="É preciso ter ao menos uma pergunta")

    ids_vistos = set()
    for p in body.perguntas:
        if not p.id.strip() or not p.categoria.strip() or not p.texto.strip():
            raise HTTPException(status_code=400, detail="Toda pergunta precisa de id, categoria e texto preenchidos")
        if p.tipo not in TIPOS_VALIDOS:
            raise HTTPException(status_code=400, detail=f"Tipo inválido: {p.tipo}. Use um de {sorted(TIPOS_VALIDOS)}")
        if p.id in ids_vistos:
            raise HTTPException(status_code=400, detail=f"Id de pergunta duplicado: {p.id}")
        ids_vistos.add(p.id)

    perguntas = [p.model_dump() for p in body.perguntas]
    _save(PERGUNTAS_FILE, perguntas)
    return perguntas


# ---------------------------------------------------------------------------
# Campanhas (admin)
# ---------------------------------------------------------------------------

@app.get("/admin/campanhas")
def list_campanhas(_: None = Depends(require_admin)):
    campanhas = _load(CAMPANHAS_FILE)
    return sorted((_campanha_summary(c) for c in campanhas), key=lambda c: c["criada_em"], reverse=True)


@app.post("/admin/campanhas", status_code=201)
def create_campanha(body: CampanhaCreate, _: None = Depends(require_admin)):
    nome = body.nome.strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome é obrigatório")

    campanha = {
        "id": f"camp_{uuid.uuid4().hex[:8]}",
        "nome": nome,
        "criada_em": now_iso(),
        "perguntas": _load_perguntas_atuais(),
    }
    campanhas = _load(CAMPANHAS_FILE)
    campanhas.append(campanha)
    _save(CAMPANHAS_FILE, campanhas)
    return _campanha_summary(campanha)


@app.get("/admin/campanhas/{campanha_id}")
def get_campanha(campanha_id: str, _: None = Depends(require_admin)):
    campanha = _campanha_or_404(campanha_id)
    return _campanha_summary(campanha)


@app.delete("/admin/campanhas/{campanha_id}")
def delete_campanha(campanha_id: str, _: None = Depends(require_admin)):
    """Remove uma campanha e todas as suas respostas (ex: campanha de teste)."""
    _campanha_or_404(campanha_id)
    campanhas = [c for c in _load(CAMPANHAS_FILE) if c["id"] != campanha_id]
    _save(CAMPANHAS_FILE, campanhas)
    respostas = [r for r in _load(RESPOSTAS_FILE) if r["campanha_id"] != campanha_id]
    _save(RESPOSTAS_FILE, respostas)
    return {"ok": True}


@app.get("/admin/campanhas/{campanha_id}/resultados")
def resultados_campanha(campanha_id: str, _: None = Depends(require_admin)):
    campanha = _campanha_or_404(campanha_id)
    respostas = _respostas_da_campanha(campanha_id)

    perguntas = campanha["perguntas"]
    perguntas_por_id = {q["id"]: q for q in perguntas}
    nps_question = next((q["id"] for q in perguntas if q["tipo"] == "nps"), None)
    texto_ids = [q["id"] for q in perguntas if q["tipo"] == "texto"]

    categorias: dict[str, dict] = {}
    distribuicoes: dict[str, dict[str, int]] = {
        q["id"]: {str(v): 0 for v in range(1, 6)} for q in perguntas if q["tipo"] == "escala5"
    }

    for r in respostas:
        for q_id, valor in (r["respostas"] or {}).items():
            q = perguntas_por_id.get(q_id)
            if not q or q["tipo"] != "escala5" or not isinstance(valor, (int, float)):
                continue
            cat = categorias.setdefault(q["categoria"], {"soma": 0.0, "count": 0})
            cat["soma"] += valor
            cat["count"] += 1
            if q_id in distribuicoes and str(int(valor)) in distribuicoes[q_id]:
                distribuicoes[q_id][str(int(valor))] += 1

    media_por_categoria = [
        {"categoria": cat, "media": round(v["soma"] / v["count"], 2) if v["count"] else None}
        for cat, v in categorias.items()
    ]

    nps_valores = [
        r["respostas"][nps_question]
        for r in respostas
        if nps_question and r["respostas"] and isinstance(r["respostas"].get(nps_question), (int, float))
    ]
    promotores = sum(1 for v in nps_valores if v >= 9)
    neutros = sum(1 for v in nps_valores if 7 <= v <= 8)
    detratores = sum(1 for v in nps_valores if v <= 6)
    nps_score = round(((promotores - detratores) / len(nps_valores)) * 100) if nps_valores else None

    escala_ids = [q["id"] for q in perguntas if q["tipo"] in ("escala5", "nps")]

    comentarios = []
    for r in respostas:
        for q_id in texto_ids:
            texto = (r["respostas"] or {}).get(q_id)
            if texto and str(texto).strip():
                comentarios.append({
                    "pergunta_id": q_id,
                    "pergunta_texto": perguntas_por_id[q_id]["texto"],
                    "texto": texto,
                    "respondido_em": r["respondido_em"],
                })
        for q_id in escala_ids:
            texto = (r["respostas"] or {}).get(q_id + SUFIXO_COMENTARIO)
            if texto and str(texto).strip():
                comentarios.append({
                    "pergunta_id": q_id + SUFIXO_COMENTARIO,
                    "pergunta_texto": f"Comentário sobre: {perguntas_por_id[q_id]['texto']}",
                    "texto": texto,
                    "respondido_em": r["respondido_em"],
                })
    comentarios.sort(key=lambda c: c["respondido_em"], reverse=True)

    return {
        "campanha": _campanha_summary(campanha),
        "media_por_categoria": media_por_categoria,
        "distribuicoes": distribuicoes,
        "nps": {"promotores": promotores, "neutros": neutros, "detratores": detratores, "score": nps_score, "total": len(nps_valores)},
        "comentarios": comentarios,
    }


@app.get("/admin/campanhas/{campanha_id}/export")
def export_campanha(campanha_id: str, _: None = Depends(require_admin)):
    campanha = _campanha_or_404(campanha_id)
    respostas = _respostas_da_campanha(campanha_id)
    perguntas = campanha["perguntas"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Respostas"
    headers = ["Respondido em"]
    for q in perguntas:
        headers.append(q["texto"])
        if q["tipo"] in ("escala5", "nps"):
            headers.append(f"{q['texto']} (comentário)")
    ws.append(headers)
    for r in respostas:
        row = [r["respondido_em"] or ""]
        for q in perguntas:
            row.append((r["respostas"] or {}).get(q["id"], ""))
            if q["tipo"] in ("escala5", "nps"):
                row.append((r["respostas"] or {}).get(q["id"] + SUFIXO_COMENTARIO, ""))
        ws.append(row)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    filename = f"pesquisa_{campanha['nome'].replace(' ', '_')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Pesquisa (público, sem login) — mesmo formulário para todo mundo, ninguém
# vê a resposta de outro franqueado (só o admin vê os resultados agregados)
# ---------------------------------------------------------------------------

@app.get("/pesquisa/{campanha_id}")
def get_pesquisa(campanha_id: str):
    campanha = _campanha_or_404(campanha_id)
    return {"campanha_nome": campanha["nome"], "perguntas": campanha["perguntas"]}


@app.post("/pesquisa/{campanha_id}/respostas", status_code=201)
def submit_resposta(campanha_id: str, body: RespostaSubmit):
    campanha = _campanha_or_404(campanha_id)

    for q in campanha["perguntas"]:
        valor = body.respostas.get(q["id"])
        if q["tipo"] == "escala5":
            if not isinstance(valor, int) or not (1 <= valor <= 5):
                raise HTTPException(status_code=400, detail=f"Resposta inválida para '{q['texto']}'")
        elif q["tipo"] == "nps":
            if not isinstance(valor, int) or not (0 <= valor <= 10):
                raise HTTPException(status_code=400, detail=f"Resposta inválida para '{q['texto']}'")

    respostas = _load(RESPOSTAS_FILE)
    respostas.append({
        "id": f"resp_{uuid.uuid4().hex[:8]}",
        "campanha_id": campanha_id,
        "respostas": body.respostas,
        "respondido_em": now_iso(),
    })
    _save(RESPOSTAS_FILE, respostas)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Backups (admin) — mesmo padrão dos outros projetos Piaseg
# ---------------------------------------------------------------------------

@app.get("/admin/backups")
def list_backups(_: None = Depends(require_admin)):
    if not BACKUPS_DIR.exists():
        return []
    return sorted((p.name for p in BACKUPS_DIR.iterdir() if p.is_dir()), reverse=True)


@app.post("/admin/backups/{name}/restore")
def restore_backup(name: str, _: None = Depends(require_admin)):
    if "/" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Nome de backup inválido")
    snapshot_dir = BACKUPS_DIR / name
    if not snapshot_dir.is_dir():
        raise HTTPException(status_code=404, detail="Backup não encontrado")

    _run_startup_backup()
    for filename in _BACKUP_FILES:
        source = snapshot_dir / filename
        if source.exists():
            shutil.copy2(source, DATA_DIR / filename)
    return {"ok": True, "restored_from": name}

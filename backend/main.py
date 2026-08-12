import os
import shutil
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import json
import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openpyxl import Workbook
from pydantic import BaseModel

from questions import QUESTIONS

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
BACKUPS_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 30
_BACKUP_FILES = ["campanhas.json", "respostas.json"]

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

SMTP_HOST = os.getenv("SMTP_HOST", "email02.webplusidc.com.br")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "franchising@piaseg.com.br")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "franchising@piaseg.com.br")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://piaseg-pesquisa-satisfacao.vercel.app")
FRANQUEADOS_API_URL = os.getenv("FRANQUEADOS_API_URL", "https://piaseg-franqueados-backend.onrender.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

NPS_QUESTION_ID = "nps"
SCALE_QUESTION_IDS = [q["id"] for q in QUESTIONS if q["tipo"] == "escala5"]
TEXT_QUESTION_IDS = [q["id"] for q in QUESTIONS if q["tipo"] == "texto"]


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


# ---------------------------------------------------------------------------
# Franqueados (fonte externa)
# ---------------------------------------------------------------------------

def _fetch_franqueados_ativos() -> list[dict]:
    try:
        resp = requests.get(f"{FRANQUEADOS_API_URL}/franqueados", params={"status": "ativo"}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Não foi possível buscar os franqueados: {e}")
    return resp.json()


def _primary_contact(franqueado: dict) -> Optional[dict]:
    for contato in franqueado.get("contatos", []):
        if contato.get("email"):
            return contato
    return None


# ---------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------

def _send_email(to: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, [to], msg.as_string())


def _render_convite_html(nome: str, link: str) -> str:
    return f"""
    <div style="font-family: Arial, Helvetica, sans-serif; max-width: 560px; margin: 0 auto;">
      <div style="background:#072a3c; padding: 28px; text-align:center;">
        <h1 style="color:#c2a360; font-size:20px; margin:0;">Pesquisa de Satisfação Piaseg</h1>
      </div>
      <div style="padding: 28px; color:#111;">
        <p>Olá, {nome},</p>
        <p>Sua opinião é muito importante para a Piaseg. Preparamos uma pesquisa rápida
        (leva cerca de 5 minutos) para entender como está sendo sua experiência como
        franqueado(a) e onde podemos melhorar.</p>
        <p style="text-align:center; margin: 32px 0;">
          <a href="{link}" style="background:#072a3c; color:#ffffff; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:bold; display:inline-block;">
            Responder a Pesquisa
          </a>
        </p>
        <p style="font-size:13px; color:#555;">
          Suas respostas ajudam a franqueadora a priorizar melhorias reais na rede. Obrigado
          por dedicar alguns minutos a isso.
        </p>
      </div>
    </div>
    """


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


def _save_resposta(resposta: dict) -> None:
    respostas = _load(RESPOSTAS_FILE)
    for i, r in enumerate(respostas):
        if r["id"] == resposta["id"]:
            respostas[i] = resposta
            _save(RESPOSTAS_FILE, respostas)
            return
    respostas.append(resposta)
    _save(RESPOSTAS_FILE, respostas)


def _campanha_summary(campanha: dict) -> dict:
    respostas = _respostas_da_campanha(campanha["id"])
    enviados = sum(1 for r in respostas if r["enviado_em"])
    respondidos = sum(1 for r in respostas if r["respondido"])
    return {
        **campanha,
        "total_franqueados": len(respostas),
        "total_enviados": enviados,
        "total_respondidos": respondidos,
    }


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

    franqueados = _fetch_franqueados_ativos()

    campanha = {
        "id": f"camp_{uuid.uuid4().hex[:8]}",
        "nome": nome,
        "criada_em": now_iso(),
        "perguntas": QUESTIONS,
    }
    campanhas = _load(CAMPANHAS_FILE)
    campanhas.append(campanha)
    _save(CAMPANHAS_FILE, campanhas)

    respostas = _load(RESPOSTAS_FILE)
    sem_email = []
    criados = 0
    for f in franqueados:
        contato = _primary_contact(f)
        if not contato:
            sem_email.append(f.get("nome_fantasia", f.get("id")))
            continue
        respostas.append({
            "id": f"resp_{uuid.uuid4().hex[:8]}",
            "token": uuid.uuid4().hex,
            "campanha_id": campanha["id"],
            "franqueado_id": f.get("id"),
            "franqueado_nome": f.get("nome_fantasia", ""),
            "email": contato["email"],
            "enviado_em": None,
            "respondido": False,
            "respostas": None,
            "respondido_em": None,
        })
        criados += 1
    _save(RESPOSTAS_FILE, respostas)

    return {**_campanha_summary(campanha), "franqueados_sem_email": sem_email, "franqueados_incluidos": criados}


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


@app.post("/admin/campanhas/{campanha_id}/enviar")
def enviar_campanha(campanha_id: str, _: None = Depends(require_admin)):
    _campanha_or_404(campanha_id)
    respostas = _load(RESPOSTAS_FILE)
    pendentes = [r for r in respostas if r["campanha_id"] == campanha_id and not r["enviado_em"]]

    falhas = []
    for r in pendentes:
        link = f"{FRONTEND_URL}/responder/{r['token']}"
        try:
            _send_email(r["email"], "Pesquisa de Satisfação Piaseg — sua opinião é importante", _render_convite_html(r["franqueado_nome"], link))
            r["enviado_em"] = now_iso()
        except Exception as e:
            falhas.append({"franqueado_nome": r["franqueado_nome"], "email": r["email"], "erro": str(e)})
    _save(RESPOSTAS_FILE, respostas)

    return {"enviados": len(pendentes) - len(falhas), "falhas": falhas}


@app.get("/admin/campanhas/{campanha_id}/resultados")
def resultados_campanha(campanha_id: str, _: None = Depends(require_admin)):
    campanha = _campanha_or_404(campanha_id)
    respostas = [r for r in _respostas_da_campanha(campanha_id) if r["respondido"]]

    perguntas = campanha["perguntas"]
    perguntas_por_id = {q["id"]: q for q in perguntas}

    categorias: dict[str, dict] = {}
    distribuicoes: dict[str, dict[str, int]] = {}
    for q in perguntas:
        if q["tipo"] != "escala5":
            continue
        distribuicoes[q["id"]] = {str(v): 0 for v in range(1, 6)}

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
        r["respostas"][NPS_QUESTION_ID]
        for r in respostas
        if r["respostas"] and isinstance(r["respostas"].get(NPS_QUESTION_ID), (int, float))
    ]
    promotores = sum(1 for v in nps_valores if v >= 9)
    neutros = sum(1 for v in nps_valores if 7 <= v <= 8)
    detratores = sum(1 for v in nps_valores if v <= 6)
    nps_score = round(((promotores - detratores) / len(nps_valores)) * 100) if nps_valores else None

    comentarios = []
    for r in respostas:
        for q_id in TEXT_QUESTION_IDS:
            texto = (r["respostas"] or {}).get(q_id)
            if texto and str(texto).strip():
                comentarios.append({
                    "franqueado_nome": r["franqueado_nome"],
                    "pergunta_id": q_id,
                    "pergunta_texto": perguntas_por_id[q_id]["texto"],
                    "texto": texto,
                    "respondido_em": r["respondido_em"],
                })

    todas_respostas = _respostas_da_campanha(campanha_id)
    return {
        "campanha": _campanha_summary(campanha),
        "media_por_categoria": media_por_categoria,
        "distribuicoes": distribuicoes,
        "nps": {"promotores": promotores, "neutros": neutros, "detratores": detratores, "score": nps_score, "total": len(nps_valores)},
        "comentarios": comentarios,
        "taxa_resposta": round(len(respostas) / len(todas_respostas) * 100, 1) if todas_respostas else 0,
    }


@app.get("/admin/campanhas/{campanha_id}/export")
def export_campanha(campanha_id: str, _: None = Depends(require_admin)):
    campanha = _campanha_or_404(campanha_id)
    respostas = _respostas_da_campanha(campanha_id)
    perguntas = campanha["perguntas"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Respostas"
    headers = ["Franqueado", "E-mail", "Enviado em", "Respondido", "Respondido em"] + [q["texto"] for q in perguntas]
    ws.append(headers)
    for r in respostas:
        row = [r["franqueado_nome"], r["email"], r["enviado_em"] or "", "Sim" if r["respondido"] else "Não", r["respondido_em"] or ""]
        for q in perguntas:
            row.append((r["respostas"] or {}).get(q["id"], ""))
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
# Respostas (público, via token)
# ---------------------------------------------------------------------------

@app.get("/respostas/token/{token}")
def get_resposta_por_token(token: str):
    respostas = _load(RESPOSTAS_FILE)
    resposta = next((r for r in respostas if r["token"] == token), None)
    if not resposta:
        raise HTTPException(status_code=404, detail="Link inválido")
    campanha = _campanha_or_404(resposta["campanha_id"])
    return {
        "franqueado_nome": resposta["franqueado_nome"],
        "campanha_nome": campanha["nome"],
        "perguntas": campanha["perguntas"],
        "respondido": resposta["respondido"],
    }


@app.post("/respostas/token/{token}")
def submit_resposta(token: str, body: RespostaSubmit):
    respostas = _load(RESPOSTAS_FILE)
    resposta = next((r for r in respostas if r["token"] == token), None)
    if not resposta:
        raise HTTPException(status_code=404, detail="Link inválido")
    if resposta["respondido"]:
        raise HTTPException(status_code=409, detail="Esta pesquisa já foi respondida")

    campanha = _campanha_or_404(resposta["campanha_id"])
    for q in campanha["perguntas"]:
        valor = body.respostas.get(q["id"])
        if q["tipo"] == "escala5":
            if not isinstance(valor, int) or not (1 <= valor <= 5):
                raise HTTPException(status_code=400, detail=f"Resposta inválida para '{q['texto']}'")
        elif q["tipo"] == "nps":
            if not isinstance(valor, int) or not (0 <= valor <= 10):
                raise HTTPException(status_code=400, detail=f"Resposta inválida para '{q['texto']}'")

    resposta["respostas"] = body.respostas
    resposta["respondido"] = True
    resposta["respondido_em"] = now_iso()
    _save_resposta(resposta)
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

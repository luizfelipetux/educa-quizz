import csv
import os
import random
import sqlite3
from functools import wraps
from io import TextIOWrapper
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "show_milhao.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "troque-esta-chave-em-producao")


# -----------------------------------------------------------------------------
# Banco de dados
# -----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS perguntas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tema TEXT NOT NULL,
                nivel TEXT NOT NULL,
                enunciado TEXT NOT NULL,
                alternativa_a TEXT NOT NULL,
                alternativa_b TEXT NOT NULL,
                alternativa_c TEXT NOT NULL,
                alternativa_d TEXT NOT NULL,
                resposta_correta TEXT NOT NULL CHECK(resposta_correta IN ('A','B','C','D')),
                usada INTEGER NOT NULL DEFAULT 0,
                criada_em TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS equipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                pontuacao INTEGER NOT NULL DEFAULT 0,
                ajuda_perguntar INTEGER NOT NULL DEFAULT 0,
                ajuda_anular INTEGER NOT NULL DEFAULT 0,
                ajuda_pular INTEGER NOT NULL DEFAULT 0,
                criada_em TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def query_all(sql, params=()):
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


def query_one(sql, params=()):
    with get_db() as conn:
        return conn.execute(sql, params).fetchone()


def execute(sql, params=()):
    with get_db() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


@app.before_request
def ensure_db_exists():
    init_db()


# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------
def normalizar_resposta(valor):
    valor = (valor or "").strip().upper()
    if valor not in {"A", "B", "C", "D"}:
        raise ValueError("A resposta correta deve ser A, B, C ou D.")
    return valor


def pontos_por_nivel(nivel):
    mapa = {
        "Fácil": 10,
        "Médio": 20,
        "Difícil": 30,
    }
    return mapa.get(nivel, 10)


def pergunta_atual():
    pergunta_id = session.get("pergunta_atual_id")
    if not pergunta_id:
        return None
    return query_one("SELECT * FROM perguntas WHERE id = ?", (pergunta_id,))


def equipes_ordenadas():
    return query_all("SELECT * FROM equipes ORDER BY nome ASC")


def rodada_atual():
    rodada = session.get("rodada_atual", 1)
    try:
        rodada = int(rodada)
    except (TypeError, ValueError):
        rodada = 1
    if rodada < 1:
        rodada = 1
    session["rodada_atual"] = rodada
    return rodada


def equipe_atual():
    equipes = equipes_ordenadas()
    if not equipes:
        session.pop("equipe_atual_id", None)
        return None

    equipe_id = session.get("equipe_atual_id")
    equipe = None
    if equipe_id:
        equipe = query_one("SELECT * FROM equipes WHERE id = ?", (equipe_id,))

    if not equipe:
        equipe = equipes[0]
        session["equipe_atual_id"] = equipe["id"]

    rodada_atual()
    return equipe


def avancar_equipe():
    equipes = equipes_ordenadas()
    if not equipes:
        session.pop("equipe_atual_id", None)
        session["rodada_atual"] = 1
        return None

    atual = equipe_atual()
    ids = [e["id"] for e in equipes]
    try:
        indice_atual = ids.index(atual["id"])
    except (ValueError, TypeError):
        indice_atual = -1

    proximo_indice = (indice_atual + 1) % len(ids)
    if proximo_indice == 0:
        session["rodada_atual"] = rodada_atual() + 1

    session["equipe_atual_id"] = ids[proximo_indice]
    return query_one("SELECT * FROM equipes WHERE id = ?", (ids[proximo_indice],))


# -----------------------------------------------------------------------------
# Páginas principais
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    total_perguntas = query_one("SELECT COUNT(*) AS total FROM perguntas")["total"]
    total_equipes = query_one("SELECT COUNT(*) AS total FROM equipes")["total"]
    return render_template("index.html", total_perguntas=total_perguntas, total_equipes=total_equipes)


@app.route("/perguntas")
def perguntas():
    termo = request.args.get("q", "").strip()
    if termo:
        like = f"%{termo}%"
        itens = query_all(
            """
            SELECT * FROM perguntas
            WHERE tema LIKE ? OR nivel LIKE ? OR enunciado LIKE ?
            ORDER BY id DESC
            """,
            (like, like, like),
        )
    else:
        itens = query_all("SELECT * FROM perguntas ORDER BY id DESC")
    return render_template("perguntas.html", perguntas=itens, termo=termo)


@app.route("/perguntas/nova", methods=["GET", "POST"])
def pergunta_nova():
    if request.method == "POST":
        try:
            dados = coletar_dados_pergunta(request.form)
            execute(
                """
                INSERT INTO perguntas
                (tema, nivel, enunciado, alternativa_a, alternativa_b, alternativa_c, alternativa_d, resposta_correta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                dados,
            )
            flash("Pergunta cadastrada com sucesso.", "success")
            return redirect(url_for("perguntas"))
        except Exception as exc:
            flash(str(exc), "danger")
    return render_template("pergunta_form.html", pergunta=None, titulo="Nova pergunta")


@app.route("/perguntas/<int:pergunta_id>/editar", methods=["GET", "POST"])
def pergunta_editar(pergunta_id):
    pergunta = query_one("SELECT * FROM perguntas WHERE id = ?", (pergunta_id,))
    if not pergunta:
        flash("Pergunta não encontrada.", "danger")
        return redirect(url_for("perguntas"))

    if request.method == "POST":
        try:
            dados = coletar_dados_pergunta(request.form)
            execute(
                """
                UPDATE perguntas
                SET tema = ?, nivel = ?, enunciado = ?, alternativa_a = ?, alternativa_b = ?,
                    alternativa_c = ?, alternativa_d = ?, resposta_correta = ?
                WHERE id = ?
                """,
                (*dados, pergunta_id),
            )
            flash("Pergunta atualizada com sucesso.", "success")
            return redirect(url_for("perguntas"))
        except Exception as exc:
            flash(str(exc), "danger")

    return render_template("pergunta_form.html", pergunta=pergunta, titulo="Editar pergunta")


@app.route("/perguntas/<int:pergunta_id>/excluir", methods=["POST"])
def pergunta_excluir(pergunta_id):
    execute("DELETE FROM perguntas WHERE id = ?", (pergunta_id,))
    if session.get("pergunta_atual_id") == pergunta_id:
        session.pop("pergunta_atual_id", None)
        session.pop("alternativas_ocultas", None)
    flash("Pergunta excluída.", "success")
    return redirect(url_for("perguntas"))


def coletar_dados_pergunta(form):
    campos = [
        "tema",
        "nivel",
        "enunciado",
        "alternativa_a",
        "alternativa_b",
        "alternativa_c",
        "alternativa_d",
    ]
    valores = [(form.get(c) or "").strip() for c in campos]
    if any(not v for v in valores):
        raise ValueError("Preencha todos os campos da pergunta.")
    resposta = normalizar_resposta(form.get("resposta_correta"))
    return (*valores, resposta)


@app.route("/perguntas/importar", methods=["GET", "POST"])
def importar_perguntas():
    if request.method == "POST":
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename:
            flash("Selecione um arquivo CSV.", "danger")
            return redirect(url_for("importar_perguntas"))

        inseridas = 0
        try:
            stream = TextIOWrapper(arquivo.stream, encoding="utf-8-sig")
            leitor = csv.DictReader(stream)
            obrigatorios = {
                "tema", "nivel", "enunciado", "alternativa_a", "alternativa_b",
                "alternativa_c", "alternativa_d", "resposta_correta"
            }
            if not leitor.fieldnames or not obrigatorios.issubset(set(leitor.fieldnames)):
                raise ValueError("O CSV não possui todos os cabeçalhos obrigatórios.")

            for linha in leitor:
                dados = (
                    linha["tema"].strip(),
                    linha["nivel"].strip(),
                    linha["enunciado"].strip(),
                    linha["alternativa_a"].strip(),
                    linha["alternativa_b"].strip(),
                    linha["alternativa_c"].strip(),
                    linha["alternativa_d"].strip(),
                    normalizar_resposta(linha["resposta_correta"]),
                )
                execute(
                    """
                    INSERT INTO perguntas
                    (tema, nivel, enunciado, alternativa_a, alternativa_b, alternativa_c, alternativa_d, resposta_correta)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    dados,
                )
                inseridas += 1
            flash(f"Importação concluída. {inseridas} pergunta(s) cadastrada(s).", "success")
            return redirect(url_for("perguntas"))
        except Exception as exc:
            flash(f"Erro ao importar: {exc}", "danger")

    return render_template("importar.html")


# -----------------------------------------------------------------------------
# Equipes e placar
# -----------------------------------------------------------------------------
@app.route("/equipes", methods=["GET", "POST"])
def equipes():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        if not nome:
            flash("Informe o nome da equipe.", "danger")
        else:
            try:
                execute("INSERT INTO equipes (nome) VALUES (?)", (nome,))
                flash("Equipe cadastrada.", "success")
            except sqlite3.IntegrityError:
                flash("Já existe uma equipe com esse nome.", "danger")
        return redirect(url_for("equipes"))

    itens = query_all("SELECT * FROM equipes ORDER BY pontuacao DESC, nome ASC")
    return render_template("equipes.html", equipes=itens)


@app.route("/equipes/<int:equipe_id>/excluir", methods=["POST"])
def equipe_excluir(equipe_id):
    execute("DELETE FROM equipes WHERE id = ?", (equipe_id,))
    flash("Equipe excluída.", "success")
    return redirect(url_for("equipes"))


@app.route("/placar")
def placar():
    equipes = query_all("SELECT * FROM equipes ORDER BY pontuacao DESC, nome ASC")
    return render_template("placar.html", equipes=equipes)


@app.route("/reiniciar", methods=["POST"])
def reiniciar():
    execute("UPDATE equipes SET pontuacao = 0, ajuda_perguntar = 0, ajuda_anular = 0, ajuda_pular = 0")
    execute("UPDATE perguntas SET usada = 0")
    session.pop("pergunta_atual_id", None)
    session.pop("alternativas_ocultas", None)
    session.pop("equipe_atual_id", None)
    session["rodada_atual"] = 1
    flash("Jogo reiniciado: placar, ajudas, rodadas e perguntas usadas foram zerados.", "success")
    return redirect(url_for("index"))


# -----------------------------------------------------------------------------
# Jogo
# -----------------------------------------------------------------------------
@app.route("/jogo")
def jogo():
    equipes = equipes_ordenadas()
    temas = query_all("SELECT DISTINCT tema FROM perguntas ORDER BY tema ASC")
    pergunta = pergunta_atual()
    atual = equipe_atual()
    alternativas_ocultas = set(session.get("alternativas_ocultas", []))
    return render_template(
        "jogo.html",
        equipes=equipes,
        equipe_atual=atual,
        rodada=rodada_atual(),
        temas=temas,
        pergunta=pergunta,
        alternativas_ocultas=alternativas_ocultas,
        pontos=pontos_por_nivel(pergunta["nivel"]) if pergunta else 0,
        tempo_pergunta=30,
    )


@app.route("/jogo/sortear", methods=["POST"])
def jogo_sortear():
    nivel = request.form.get("nivel", "").strip()
    tema = request.form.get("tema", "").strip()

    sql = "SELECT * FROM perguntas WHERE usada = 0"
    params = []
    if nivel:
        sql += " AND nivel = ?"
        params.append(nivel)
    if tema:
        sql += " AND tema = ?"
        params.append(tema)
    sql += " ORDER BY RANDOM() LIMIT 1"

    pergunta = query_one(sql, tuple(params))
    if not pergunta:
        flash("Não há pergunta disponível com esses filtros. Tente outro tema/nível ou reinicie o jogo.", "warning")
    else:
        session["pergunta_atual_id"] = pergunta["id"]
        session.pop("alternativas_ocultas", None)
        flash("Pergunta sorteada.", "success")
    return redirect(url_for("jogo"))


@app.route("/jogo/responder", methods=["POST"])
def jogo_responder():
    pergunta = pergunta_atual()
    if not pergunta:
        flash("Nenhuma pergunta sorteada.", "danger")
        return redirect(url_for("jogo"))

    resposta = normalizar_resposta(request.form.get("resposta"))
    equipe = equipe_atual()
    if not equipe:
        flash("Cadastre pelo menos uma equipe antes de responder.", "danger")
        return redirect(url_for("jogo"))

    correta = resposta == pergunta["resposta_correta"]
    pontos = pontos_por_nivel(pergunta["nivel"])
    if correta:
        execute("UPDATE equipes SET pontuacao = pontuacao + ? WHERE id = ?", (pontos, equipe["id"]))
        flash(f"Resposta correta! {equipe['nome']} ganhou {pontos} ponto(s).", "success")
    else:
        flash(f"Resposta incorreta. A resposta correta era {pergunta['resposta_correta']}.", "danger")

    execute("UPDATE perguntas SET usada = 1 WHERE id = ?", (pergunta["id"],))
    session.pop("pergunta_atual_id", None)
    session.pop("alternativas_ocultas", None)
    avancar_equipe()
    return redirect(url_for("jogo"))


@app.route("/jogo/ajuda/perguntar", methods=["POST"])
def ajuda_perguntar():
    equipe = equipe_atual()
    if not equipe:
        flash("Cadastre pelo menos uma equipe antes de usar a ajuda.", "danger")
    elif equipe["ajuda_perguntar"]:
        flash("Essa equipe já utilizou a ajuda 'Perguntar à equipe'.", "warning")
    else:
        execute("UPDATE equipes SET ajuda_perguntar = 1 WHERE id = ?", (equipe["id"],))
        flash(f"Ajuda liberada para {equipe['nome']}: 30 segundos para conversar.", "info")
    return redirect(url_for("jogo"))


@app.route("/jogo/ajuda/anular", methods=["POST"])
def ajuda_anular():
    pergunta = pergunta_atual()
    equipe = equipe_atual()
    if not pergunta:
        flash("Sorteie uma pergunta antes de usar a ajuda.", "danger")
    elif not equipe:
        flash("Cadastre pelo menos uma equipe antes de usar a ajuda.", "danger")
    elif equipe["ajuda_anular"]:
        flash("Essa equipe já utilizou a ajuda 'Anular 2 alternativas'.", "warning")
    else:
        alternativas = ["A", "B", "C", "D"]
        erradas = [a for a in alternativas if a != pergunta["resposta_correta"]]
        ocultas = random.sample(erradas, 2)
        session["alternativas_ocultas"] = ocultas
        execute("UPDATE equipes SET ajuda_anular = 1 WHERE id = ?", (equipe["id"],))
        flash("Duas alternativas erradas foram anuladas.", "info")
    return redirect(url_for("jogo"))


@app.route("/jogo/ajuda/pular", methods=["POST"])
def ajuda_pular():
    pergunta = pergunta_atual()
    equipe = equipe_atual()
    if not pergunta:
        flash("Sorteie uma pergunta antes de pular.", "danger")
    elif not equipe:
        flash("Cadastre pelo menos uma equipe antes de usar a ajuda.", "danger")
    elif equipe["ajuda_pular"]:
        flash("Essa equipe já utilizou a ajuda 'Pular'.", "warning")
    else:
        execute("UPDATE equipes SET ajuda_pular = 1 WHERE id = ?", (equipe["id"],))
        execute("UPDATE perguntas SET usada = 1 WHERE id = ?", (pergunta["id"],))
        session.pop("pergunta_atual_id", None)
        session.pop("alternativas_ocultas", None)
        flash("Pergunta pulada. Sorteie uma nova pergunta.", "info")
    return redirect(url_for("jogo"))


@app.route("/jogo/proxima-equipe", methods=["POST"])
def jogo_proxima_equipe():
    session.pop("pergunta_atual_id", None)
    session.pop("alternativas_ocultas", None)
    proxima = avancar_equipe()
    if proxima:
        flash(f"Vez da equipe {proxima['nome']}.", "info")
    return redirect(url_for("jogo"))


@app.route("/exemplo-csv")
def exemplo_csv():
    from flask import Response
    conteudo = """tema,nivel,enunciado,alternativa_a,alternativa_b,alternativa_c,alternativa_d,resposta_correta
Cabos UTP,Fácil,Qual categoria suporta 1 Gbps em até 100 metros?,Cat 3,Cat 5e,Cat 4,Cabo coaxial,B
Redes,Fácil,Qual equipamento conecta dispositivos em uma rede local?,Switch,Estabilizador,Projetor,Teclado,A
HTML,Médio,Qual tag cria um link em HTML?,<p>,<a>,<img>,<table>,B
"""
    return Response(
        conteudo,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=perguntas_exemplo.csv"},
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)

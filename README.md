# Educa Quizz

Aplicação web para revisão gamificada de conteúdos em equipes, conduzida pelo professor. O sistema permite organizar perguntas por tema e dificuldade, registrar respostas, acompanhar a pontuação e utilizar ajudas durante a dinâmica.

A interface desta versão utiliza o nome **Show da Informática**, enquanto **Educa Quizz** identifica o produto didático documentado neste repositório.

## 1. Identificação e autoria

| Campo | Informação |
| --- | --- |
| Autor responsável | Luiz Felipe de Sousa|


## 2. Finalidade pedagógica

O Educa Quizz foi desenvolvido para apoiar a revisão de conteúdos em sala de aula por meio da participação de equipes e da mediação docente. O professor registra a alternativa apresentada pelo representante da equipe e utiliza os resultados para discutir dúvidas e retomar conceitos.


## 3. Funcionalidades

- Cadastro, edição, exclusão e busca de perguntas.
- Organização por tema e níveis Fácil, Médio e Difícil.
- Importação de perguntas por CSV e download de exemplo.
- Cadastro e exclusão de equipes.
- Sorteio de perguntas disponíveis por tema e nível.
- Indicação da equipe da vez e do número da rodada.
- Registro da resposta e atualização da pontuação.
- Avanço automático de equipe após a resposta e avanço manual pelo professor.
- Ajudas por equipe: perguntar à equipe, anular duas alternativas incorretas e pular.
- Cronômetro visual de 30 segundos.
- Placar e reinício da dinâmica.

## 4. Tecnologias

- Python: 3
- Flask 3.1.0 e Gunicorn 23.0.0, conforme `requirements.txt`.
- SQLite, acessado pelo módulo `sqlite3` do Python.
- HTML com templates Jinja, CSS e JavaScript.

## 5. Organização do código

A aplicação conserva a organização dos arquivos do pacote original:

~~~text
educa-quizz/
├── app.py
├── wsgi.py
├── requirements.txt
├── .env.example
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── perguntas.html
│   ├── pergunta_form.html
│   ├── importar.html
│   ├── equipes.html
│   ├── jogo.html
│   └── placar.html
└── static/
    └── style.css
~~~

`app.py` reúne rotas, acesso ao banco e regras da dinâmica. `wsgi.py` expõe a aplicação para o Gunicorn. Os templates compõem a interface; o cronômetro permanece em `templates/jogo.html`, e os estilos permanecem em `static/style.css`.

O banco `show_milhao.db` é criado na pasta de `app.py` no primeiro acesso. As tabelas são `perguntas` e `equipes`.

O repositório pode acrescentar `.gitignore` e uma pasta `docs/` com os documentos de desenvolvimento e as evidências disponíveis, preservando os caminhos do código.

## 6. Instalação e execução local

Em Linux, a partir da raiz do projeto:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python -m flask --app app run --host 127.0.0.1 --port 5000
~~~

Acesse [http://127.0.0.1:5000](http://127.0.0.1:5000).

O código lê `FLASK_SECRET_KEY` pelo ambiente do processo. Na versão recebida, copiar `.env.example` para `.env` não carrega a variável automaticamente. A chave gerada no exemplo acima vale para a sessão atual do terminal; no servidor, configure uma chave estável no ambiente do serviço.

Em uma implantação Linux com Gunicorn, com a chave configurada e o ambiente virtual ativo:

~~~bash
gunicorn --bind 127.0.0.1:8000 wsgi:app
~~~


## 7. Importação de perguntas por CSV

Use arquivo UTF-8 separado por vírgulas. Cabeçalho e exemplo compatíveis com a aplicação:

~~~csv
tema,nivel,enunciado,alternativa_a,alternativa_b,alternativa_c,alternativa_d,resposta_correta
Redes,Fácil,Qual equipamento conecta dispositivos em uma rede local?,Switch,Estabilizador,Projetor,Teclado,A
~~~

A resposta correta deve ser A, B, C ou D. Use os níveis com a grafia da interface. Campos com vírgulas devem estar entre aspas.

Na implementação atual, cada pergunta importada é confirmada individualmente no banco; em caso de erro posterior, confira o que já foi cadastrado antes de repetir a importação.

## 8. Uso e regras da dinâmica

1. Cadastre equipes e perguntas, ou importe um CSV.
2. Abra a tela do jogo, confira a equipe da vez e sorteie uma pergunta.
3. Conduza a discussão, utilizando as ajudas conforme necessário.
4. Registre a resposta apresentada pelo representante.
5. Acompanhe o resultado, a passagem de equipe e o placar.

Perguntas Fácil, Médio e Difícil atribuem, respectivamente, 10, 20 e 30 pontos por acerto. Respostas incorretas não somam nem descontam pontos. Cada equipe dispõe de um uso de cada ajuda até o reinício. Pular uma pergunta mantém a equipe da vez.

O cronômetro é visual e não bloqueia respostas automaticamente. Reiniciar a dinâmica zera pontuação, ajudas, rodadas e marcações de uso das perguntas, mantendo os cadastros.

# Show da Informática

Sistema web simples em Flask para dinâmica de perguntas e respostas no estilo Show do Milhão.

## Recursos

- Cadastro, edição e exclusão de perguntas
- Cadastro de equipes
- Placar
- Sorteio de perguntas por tema e nível
- Ajudas por equipe:
  - Perguntar à equipe
  - Anular 2 alternativas erradas
  - Pular pergunta
- Importação de perguntas via CSV
- Banco SQLite local

## Execução local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse: http://127.0.0.1:5000

## CSV de perguntas

Cabeçalho esperado:

```csv
tema,nivel,enunciado,alternativa_a,alternativa_b,alternativa_c,alternativa_d,resposta_correta
```

A resposta correta deve ser A, B, C ou D.


## Atualização da dinâmica

Esta versão inclui:

- exibição automática da equipe da vez;
- avanço automático para a próxima equipe após registrar uma resposta;
- contador de rodada;
- cronômetro visual de 30 segundos por pergunta;
- painel mostrando quais ajudas a equipe atual ainda possui;
- botão manual para passar a vez, caso o professor precise ajustar a dinâmica.

Para atualizar uma instalação existente, substitua os arquivos do projeto e reinicie o serviço:

```bash
sudo systemctl restart show_milhao
```

O banco SQLite existente pode ser mantido. As tabelas continuam compatíveis.

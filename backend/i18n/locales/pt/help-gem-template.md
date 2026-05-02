## Escrever um bom modelo de instrução

O modelo é a instrução que dá à IA. Use `{{ nome_variável }}` em qualquer parte do texto para criar um campo que o utilizador preenche antes de executar o Gem.

**Exemplo:**

```
Resume o seguinte texto em {{ idioma }}, usando no máximo {{ pontos_max }} pontos:

{{ texto }}
```

Isto cria três campos de entrada: *idioma*, *pontos_max* e *texto*.

**Dicas para uma boa instrução:**

- **Seja específico** — diga ao modelo exatamente o que quer que produza.
- **Indique o formato** — lista com pontos, parágrafo curto, passos numerados, tabela…
- **Dê um exemplo** — se a tarefa for difícil, mostre como é uma boa resposta.
- **Seja conciso** — o modelo funciona melhor com instruções claras e concisas.
- **Nomeie as variáveis claramente** — `{{ nome_doente }}` é melhor do que `{{ nome }}`.

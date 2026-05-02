## A janela de contexto

A janela de contexto controla quanto texto o modelo pode ler e escrever numa única tarefa. É medida em **tokens** — aproximadamente três quartos de uma palavra cada.

**Orientações:**

- **4.096–8.192** — adequado para prompts curtos e respostas breves. O mais rápido e que usa menos memória.
- **16.384–32.768** — apropriado quando as tarefas envolvem documentos longos ou saídas detalhadas.
- **Valores mais elevados** — usam significativamente mais memória. Em máquinas com pouca RAM, isto pode abrandar o servidor ou torná-lo sem resposta.

Uma boa regra geral: defina-o para o valor mais pequeno que lide confortavelmente com a sua tarefa mais longa prevista. Se uma resposta parecer cortada a meio de uma frase, aumente este valor e clique em **Guardar definições** para reconstruir.

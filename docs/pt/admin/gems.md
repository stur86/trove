# Gerir gems

Um **Gem** é uma tarefa de IA reutilizável com um propósito fixo. Os utilizadores veem os gems como cartões no ecrã inicial e preenchem um formulário curto para os executar.

## Criar um gem

1. Abra o separador **Gems** no painel de administração.
2. Clique em **Novo gem**.
3. Preencha o formulário:

| Campo | O que faz |
|---|---|
| **Nome** | Apresentado no cartão do gem. Mantenha-o curto e descritivo. |
| **Descrição** | Opcional. Uma dica de uma linha apresentada sob o nome. |
| **Matiz** | A cor do ícone do gem. Use cores diferentes para distinguir facilmente os gems num relance. |
| **Modelo de prompt** | A instrução para a IA. Use marcadores de posição `{{ variable_name }}` para os campos que o utilizador preenche. |
| **Capacidades** | Assinale *Aceita entrada de imagem* se a tarefa precisar de uma foto ou captura de ecrã. |
| **Modo de saída** | *Texto* para saída normal; *Estruturado (JSON)* para saída legível por máquina. |
| **Acesso a documentos** | Quais pastas de documentos ou ficheiros individuais a IA pode ler ao executar este gem. |

4. Clique em **Criar**.

## Escrever um bom modelo de prompt

O modelo é a instrução que a IA recebe. Pode incluir qualquer texto, mais marcadores:

```
Resume o seguinte texto em {{ language }}, usando no máximo 5 tópicos:

{{ text }}
```

Isto cria dois campos de entrada para o utilizador: *language* e *text*.

**Dicas:**

- Seja específico. Diga à IA exatamente o formato que pretende.
- Indique o idioma esperado da resposta se for importante.
- Mantenha as instruções curtas — o modelo funciona melhor com prompts claros e concisos.
- Teste o gem você mesmo antes de o partilhar com os utilizadores.

## Acesso a documentos

Cada gem pode ter acesso a parte da biblioteca de documentos através da árvore de pastas e documentos no formulário do gem:

- **Acesso a pasta** — assinale a caixa junto ao nome de uma pasta. A IA pode ver cada documento nessa pasta, incluindo novos adicionados posteriormente. Assinalar uma pasta assinala automaticamente todos os documentos dentro dela.
- **Acesso a documento individual** — expanda uma pasta e assinale apenas os documentos específicos que pretende. Uma pasta com alguns documentos assinalados mas não todos mostra um indicador parcial (−).
- **Sem acesso** (predefinição) — deixe todas as caixas desmarcadas. A IA não usa a biblioteca de documentos para este gem.

Quando um gem tem acesso a documentos, a IA decide por si própria se deve consultar documentos ou responder a partir do seu próprio conhecimento.

## Editar e eliminar

Clique em **Editar** junto a um gem para alterar as suas definições. Clique em **Eliminar** para o remover permanentemente. Não há opção de desfazer.

!!! warning "Eliminar um gem"
    Os gems eliminados não podem ser recuperados. Os utilizadores que tentarem abrir o URL de um gem eliminado verão um erro.

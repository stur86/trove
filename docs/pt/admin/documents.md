# Gerir documentos

A biblioteca de documentos permite-lhe dar à IA acesso aos ficheiros da sua instituição — políticas, manuais, folhas de referência — sem os incorporar nos prompts de cada gem individualmente.

## Carregar um documento

1. Abra o separador **Documentos** no painel de administração.
2. Selecione uma pasta de destino (ou crie uma nova).
3. Clique em **Carregar** e escolha um ficheiro.

Os formatos suportados incluem PDF, Word (`.docx`), texto simples e a maioria dos formatos de escritório comuns. O Trove converte os ficheiros carregados para texto simples internamente usando o [Markitdown](https://github.com/microsoft/markitdown). O ficheiro original é mantido junto da versão convertida.

Após o carregamento, a IA gera automaticamente uma descrição de uma linha do documento. Esta descrição é apresentada no painel de administração e usada quando a IA decide quais documentos consultar.

## Pastas

Os documentos são organizados em pastas. As pastas são a unidade de controlo de acesso: quando cria um gem, concede acesso a pastas inteiras ou a documentos individuais dentro delas.

Para criar uma pasta, escreva um nome no campo **Nova pasta** e prima Enter (ou o botão de adicionar).

Para renomear uma pasta ou um documento, clique no seu nome no painel de administração.

## Como a IA usa os documentos

Quando um gem tem acesso a documentos, o Trove fornece à IA um resumo de todos os documentos acessíveis antes de começar. A IA pode então solicitar o texto completo de qualquer documento que considere relevante. Não há pesquisa vetorial — a IA raciocina a partir dos resumos e obtém o conteúdo completo sob pedido.

Isto significa:
- **Documentos curtos, bem nomeados e com boas descrições** são mais fáceis de encontrar e usar para a IA.
- **Documentos muito grandes** podem ser truncados para caber na janela de contexto do modelo.
- A IA nem sempre usará documentos — usa-os apenas quando parecem relevantes para o pedido do utilizador.

## Transferir documentos

Pode transferir documentos individuais ou pastas inteiras diretamente a partir do separador Documentos.

- **Pasta** — clique no ícone de transferência (↓) junto ao nome de uma pasta para receber um ficheiro ZIP com a versão Markdown convertida de cada documento nessa pasta.
- **Documento** — clique no ícone de transferência junto ao nome de um documento para receber o seu ficheiro Markdown convertido (`.md`).

Estas transferências contêm a versão em texto simples de cada ficheiro como o Trove o vê, não o ficheiro original carregado.

## Remover um documento

Clique no botão **Eliminar** junto a um documento no painel de administração. O ficheiro e os seus metadados são eliminados permanentemente.

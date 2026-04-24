# Definições

O separador **Definições** controla o modelo de IA e as preferências de visualização para todo o servidor.

## Modelo de IA

| Definição | O que faz |
|---|---|
| **Modelo base** | A variante Gemma 4 que o Trove utiliza. Apenas os modelos já transferidos aparecem na lista. |
| **Janela de contexto (num_ctx)** | Quanto texto o modelo pode manter em memória de uma vez, medido em tokens (aproximadamente ¾ de uma palavra cada). Valores maiores lidam com documentos mais longos mas usam mais RAM. |

Após alterar o modelo ou a janela de contexto, clique em **Guardar e reconstruir** para aplicar a alteração. O Trove reconstrói a sua configuração interna do modelo; demora cerca de 30 segundos e mostra o progresso na página.

### Escolher um modelo

| Modelo | Parâmetros efetivos | RAM mínima | Áudio | Melhor para |
|---|---|---|---|---|
| `gemma4:e2b` | 2,3B | ~4 GB | Sim | Computadores muito lentos, as respostas mais rápidas |
| `gemma4:e4b` | 4,5B | ~6 GB | Sim | Equilibrado — predefinição recomendada |
| `gemma4:26b` | 4B ativos (MoE) | ~10 GB | Não | Melhor qualidade, velocidade semelhante a e4b |
| `gemma4:31b` | 31B denso | ~20 GB | Não | A melhor qualidade, necessita de um computador potente |

!!! tip "Gems de áudio e escolha de modelo"
    Apenas `gemma4:e2b` e `gemma4:e4b` suportam entrada de áudio. Se mudar para um modelo sem suporte de áudio, os gems que usam entrada de áudio ficarão ocultos para os utilizadores até mudar de volta.

## Idioma

O seletor de **Idioma** altera o idioma de visualização de toda a interface do Trove, incluindo o ecrã inicial e o executor de gems do lado do utilizador. Idiomas atualmente suportados: inglês, francês, alemão, espanhol, português, chinês, italiano.

## Dados

A secção **Dados** permite-lhe fazer cópia de segurança de toda a configuração do Trove ou restaurar uma cópia de segurança anterior.

### Exportar um bundle

Clique em **Exportar bundle** para transferir um único ficheiro ZIP (`trove-bundle.zip`) contendo:

- Todos os gems e as suas definições.
- Todas as pastas de documentos, metadados de documentos e o texto convertido de cada documento.

Utilize isto para fazer cópia de segurança da sua configuração antes de efetuar grandes alterações, ou para copiar uma configuração para outra instância do Trove.

### Importar um bundle

Clique em **Importar bundle** para abrir o diálogo de importação. Escolha um ficheiro `.zip` exportado de qualquer instância do Trove e selecione um modo de importação:

| Modo | O que faz |
|---|---|
| **Adicionar** (predefinição) | Combina o bundle com os dados atuais. Os gems e documentos existentes são mantidos. Se um item importado tiver o mesmo ID que um existente, é importado com um novo ID (ex. `policy-2`). |
| **Substituir** | Elimina todos os gems, documentos e pastas atuais, depois importa tudo do bundle. |

!!! warning "O modo Substituir é irreversível"
    O modo Substituir elimina permanentemente todos os gems e documentos existentes antes de importar. Exporte uma cópia de segurança primeiro se quiser manter o estado atual.

Após uma importação bem-sucedida, um resumo mostra quantos gems e documentos foram importados e se algum foi renomeado devido a conflitos de ID.

## URL de LAN

O URL de LAN mostrado no separador Definições é o endereço que os utilizadores da sua rede devem abrir. Use o botão **Copiar** e partilhe-o — por exemplo, coloque-o num quadro de avisos ou envie-o por e-mail.

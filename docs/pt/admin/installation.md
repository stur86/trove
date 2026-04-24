# Instalação

Este guia destina-se à pessoa que vai configurar o Trove. Não são necessários conhecimentos de programação.

## O que precisa

- Um computador com **Linux** (Ubuntu 22.04 ou posterior recomendado)
- Pelo menos **4 GB de RAM** (8 GB ou mais é melhor)
- Pelo menos **10 GB de espaço livre em disco**
- Ligação à internet *apenas durante a instalação* — depois, o Trove funciona completamente offline

## Passo 1 — Instalar o Trove

Abra um terminal e execute:

```bash
curl -LsSf https://raw.githubusercontent.com/stur86/trove/main/install.sh | bash
```

Isto transfere o instalador, obtém a versão mais recente do Trove e configura tudo. Demora alguns minutos.

!!! tip "Comando não encontrado depois?"
    Se vir `trove: command not found` após o instalador terminar, execute o comando que apresenta (algo como `export PATH="$HOME/.local/bin:$PATH"`), e depois abra uma nova janela de terminal.

## Passo 2 — Executar o assistente de configuração

Execute o assistente de configuração **no mesmo computador onde acabou de instalar o Trove**. A página de configuração só é acessível a partir desse computador — isto é intencional.

```bash
trove setup
```

Em seguida, abra um browser **nesse mesmo computador** e aceda a:

```
http://localhost:7071
```

O assistente guia-o por seis passos:

1. **Idioma** — escolha o idioma da interface
2. **Boas-vindas** — confirma o seu hardware e o que o Trove vai instalar
3. **Instalar o Ollama** — transfere o motor de IA (ignorado se já instalado)
4. **Escolher um modelo** — escolha um modelo Gemma 4; apenas são mostrados os modelos que o seu hardware consegue executar. Este passo requer ligação à internet e pode demorar 10–30 minutos.
5. **Conta de administrador** — defina um nome de utilizador e palavra-passe para o painel de administração
6. **Instalar serviço** — regista o Trove para iniciar automaticamente no arranque

Após concluir, o painel mostra o endereço para dar aos seus utilizadores.

## Passo 3 — Dar aos utilizadores um endereço fiável

Quando o Trove inicia, mostra um endereço como `http://192.168.1.42:7770`. Os utilizadores noutros dispositivos abrem-no em qualquer browser — sem aplicações para instalar.

**O endereço pode mudar** sempre que o servidor reinicia, porque os routers domésticos e de escritório reatribuem endereços automaticamente. Se mudar, os utilizadores obterão um erro de "site inacessível".

!!! info "Resolver com um IP estático"
    Definir um endereço IP fixo ("estático") para o computador servidor impede que o endereço mude. Faz-se apenas uma vez, nas definições do router.

    1. Abra a página de administração do seu router — normalmente `http://192.168.1.1` ou `http://192.168.0.1` (verifique a etiqueta no router).
    2. Procure a secção chamada **DHCP**, **LAN** ou **Reserva de IP**.
    3. Encontre o servidor Trove na lista de dispositivos ligados e atribua-lhe um endereço fixo.
    4. Guarde e reinicie o router se solicitado.

    Se precisar de ajuda, contacte o seu suporte informático — é uma tarefa de rotina.

## Iniciar e parar o Trove

Se instalou o serviço durante a configuração, o Trove inicia automaticamente no arranque. Também pode controlá-lo manualmente:

```bash
systemctl --user status trove    # verificar se está a funcionar
systemctl --user restart trove   # reiniciar
systemctl --user stop trove      # parar
```

Se ignorou o serviço, inicie o Trove manualmente quando necessário:

```bash
trove start
```

Prima `Ctrl + C` para parar. Para manter o serviço a funcionar mesmo quando ninguém está com sessão iniciada (útil num servidor sem interface gráfica):

```bash
loginctl enable-linger $USER   # configuração única; pode requerer sudo
```

## Guia de seleção de modelos

| Modelo | RAM mínima | Áudio | Melhor para |
|---|---|---|---|
| Gemma 4 E2B | 4 GB | Sim | Computadores muito lentos, as respostas mais rápidas |
| Gemma 4 E4B | 6 GB | Sim | Equilibrado — predefinição recomendada |
| Gemma 4 26B | 10 GB | Não | Melhor qualidade, velocidade semelhante a E4B |
| Gemma 4 31B | 20 GB | Não | A melhor qualidade, necessita de um computador potente |

## Resolução de problemas

**"trove: command not found"**
Execute `export PATH="$HOME/.local/bin:$PATH"` e tente novamente. Para tornar permanente, adicione essa linha a `~/.bashrc`.

**A página de configuração não carrega**
Certifique-se de que está no mesmo computador onde executou `trove setup` e que o comando ainda está a correr no terminal.

**Outros dispositivos não conseguem aceder ao Trove**
Verifique que `trove start` (ou o serviço) está a funcionar. Certifique-se de que todos os dispositivos estão na mesma rede Wi-Fi ou com fio. Se o endereço continuar a mudar, defina um IP estático no router (ver Passo 3).

**A transferência do modelo é muito lenta**
A primeira transferência pode demorar 10–30 minutos dependendo da ligação à internet. Acontece apenas uma vez.

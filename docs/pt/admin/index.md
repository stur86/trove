# Visão geral da administração

O painel de administração só é acessível a partir do computador que executa o Trove. Abra `http://localhost:7770/admin` num browser nesse computador e inicie sessão com as credenciais que definiu durante a configuração.

!!! warning "O acesso de administrador é apenas para localhost"
    O início de sessão de administrador está intencionalmente oculto para todos os outros dispositivos da rede. Esta é uma medida de segurança. Para gerir o Trove tem de estar fisicamente no servidor ou usar um túnel SSH.

## Os quatro separadores

| Separador | O que pode fazer |
|---|---|
| **Definições** | Escolher o modelo de IA, definir o tamanho da janela de contexto, alterar o idioma de visualização |
| **Documentos** | Carregar ficheiros, organizá-los em pastas, ver resumos gerados por IA |
| **Gems** | Criar, editar e eliminar gems |
| **Registos** | Ver as últimas 1.000 linhas do registo do servidor, atualizado automaticamente a cada 5 segundos |

## URL de LAN

O separador Definições mostra o **URL de LAN** — o endereço que outros dispositivos devem usar para aceder ao Trove. Copie-o e partilhe-o com os seus utilizadores.

## Passos seguintes

- [Instalação](installation.md)
- [Gerir gems](gems.md)
- [Gerir documentos](documents.md)
- [Referência de definições](settings.md)

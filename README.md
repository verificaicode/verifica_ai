# Verifica AI

&nbsp;&nbsp;&nbsp;&nbsp;O Verifica AI é um sistema automatizado para análise e verificação de postagens do Instagram. Utilizando a API Gemini para inteligência artificial e a biblioteca Instaloader para coleta de dados, o projeto identifica a veracidade do conteúdo de acordo com os [**tipos de notícia**](#tipos-de-notícia) e fornece uma análise detalhada com fontes ordenadas por grau de confiança.

---

## Tipos de notícia

O sistema identifica 7 tipos principais de notícia:

- **Fato:** Afirmativa baseada em informações verdadeiras, sustentada por evidências verificáveis e fontes confiáveis.

- **Informações insuficientes:** A postagem apresenta dados que não podem ser confirmados ou refutados devido à falta de contexto, detalhes ou evidências disponíveis no momento da análise.

- **Sátira ou paródia:** Não têm a intenção de causar danos, mas podem enganar. Embora sejam formas legítimas de expressão artística, podem ser confundidas com fatos reais em ambientes digitais onde as informações circulam rapidamente. Entram nessa classificação os memese posts com intenção de divertir o leitor, mostrando informações absurdas ou claramente fora de contexto, ambas inofensivas.

- **Conexão falsa:** Ocorre quando títulos, imagens ou legendas não têm relação com o conteúdo da matéria. Essa prática visa atrair cliques e engajamento, mas engana o leitor ao apresentar informações desconectadas.

- **Conteúdo enganoso:** Uso distorcido de informações verdadeiras para manipular a interpretação dos fatos. Pode envolver a seleção parcial de dados, estatísticas ou citações, bem como o uso de imagens de forma a induzir a erro.

- **Contexto falso:** Informações verdadeiras são retiradas de seu contexto original e reapresentadas de maneira enganosa.

- **Conteúdo impostor:** Ocorre quando alguém se passa por uma fonte confiável (instituições, veículos de imprensa ou pessoas públicas) para dar credibilidade a informações falsas.

- **Conteúdo manipulado:** Conteúdo genuíno (como vídeos, imagens ou documentos) é alterado de forma intencional para enganar.

- **Conteúdo fabricado:** Todo o conteúdo é falso, criado do zero. Pode ser textual, visual ou multimodal. Para analisar esse tipo de conteúdo, é útil considerar os elementos da desordem informacional: o agente (quem cria, produz ou distribui), a mensagem e os intérpretes. É essencial entender as motivações dos envolvidos e os tipos de mensagens disseminadas.


---

## Funcionalidades

- Processa mensagens de texto, imagens e vídeos compartilhados via Instagram.
- Faz análise detalhada do conteúdo com auxílio de LLM (Large Language Models) Gemini.
- Realiza buscas online para validar informações temporais e contextuais.
- Classifica o conteúdo como fato, fake ou informações insuficientes.
- Envia respostas automáticas para usuários via Instagram Messenger.
- Suporta múltiplas mídias em postagens (sidecar).

---

## Tecnologias Utilizadas

- Python 3.11
- Instaloader (para baixar conteúdo do Instagram)
- Google Gemini API (modelo de linguagem para análise e geração de texto)
- Requests (para requisições HTTP)
- python-dotenv (para gerenciar variáveis de ambiente)
- APIs do Instagram Graph para mensagens e webhooks

---
## Fluxograma
```mermaid
flowchart TD
    U1(User)
    B(Verifica AI)
    T1(Extrai texto)
    T2(Extrai imagem, legenda, data)
    T3(Extrai vídeo, legenda, data)
    EG(GEMINI)
    C1(Classificação 1)
    D1{Fato ou Indeterminado?}
    C2(Classificação 2)
    U2(User)

    U1 --> |mensagem| B

    B --> |texto| T1
    B --> |imagem| T2
    B --> |video| T3

    T1 --> |API| EG
    T2 --> |API| EG
    T3 --> |API| EG

    EG --> |modelo 1| C1
    C1 --> D1

    D1 --> |Sim| U2
    D1 --> |Não: Desinformação| C2
    C2 --> U2

%% class Text1 myStyle;

%% classDef myStyle fill:#fff, stroke:blue, stroke-width:2px;
```

### Descrição do fluxo

**Usuário:** Envia uma mensagem que pode conter texto, imagem ou vídeo.

**Verifica AI:** Recebe a mensagem e, de forma automática e transparente para o usuário, extrai os dados relevantes (texto, legenda, data, imagem ou vídeo) e os envia para análise.

**Análise com Inteligência Artificial (GEMINI):**
A IA realiza uma classificação primária, identificando se o conteúdo é:
- Fato
- Indeterminado
- Desinformação

&nbsp;&nbsp;&nbsp;&nbsp;Se o conteúdo for fato ou indeterminado, o Verifica AI retorna imediatamente o resultado ao usuário.

&nbsp;&nbsp;&nbsp;&nbsp;Se o conteúdo for classificado como desinformação, uma segunda análise é realizada para identificar o tipo específico de desinformação, entre as seguintes categorias:

- Sátira ou paródia
- Conexão falsa
- Conteúdo enganoso
- Contexto falso
- Conteúdo impostor
- Conteúdo manipulado
- Conteúdo fabricado

&nbsp;&nbsp;&nbsp;&nbsp;Após essa etapa, o resultado final é enviado ao usuário, que vê apenas o diagnóstico final, sem ter acesso às etapas intermediárias.

---
## Diagrama de classes
```mermaid
classDiagram
  class AppContext{
    +models
    +posts
    +instaloader_context
    +TEMP_PATH
    +USERNAME
    +PASSWORD
    +API_GEMINI_KEY
    +PAGE_ACCESS_TOKEN
    +DEBUG
    +VERIFY_TOKEN
    +VERIFICA_AI_SERVER
    +VERIFICA_AI_PROXY
  }

  class Server {
    +process()
    +connect_to_server()
    +connect()
    +disconnect()
    +resgister_routes()
    +webhook_socketio()
    +webhook_flask()
    +loop()
    +run_app_flask()
    +run_flask_server()
  }

  class InputHandler {
    +process_webhook_message()
    +process_input()
  }

  class ContentExtractor {
    +instaloader_context
    +posts
    +get_content_object()
  }

  class Uploader {
    +file_uploader()
  }

  class ResponseProcessor {
    +client
    +models
    +content_categories
    +type_fake_name_classes
    +get_result_from_process()
  }

  class GeminiResponseGenerator {
    +generate_response()
    +get_gemini_response()
  }

  Server --> AppContext : «2» define constantes
  Server --> InputHandler
  InputHandler --> ContentExtractor : «3» extrai conteúdo
  InputHandler --> Uploader        : «4» upload de mídia para servidor GEMINI
  InputHandler --> ResponseProcessor : «5» processa a resposta gerada pela IA
  ResponseProcessor --> GeminiResponseGenerator : «5» gera resposta
```

## Diagrama de sequência

```mermaid
sequenceDiagram
  participant User
  participant Server
  participant InputHandler
  participant ContentExtractor
  participant Uploader
  participant ResponseProcessor
  participant GeminiResponseGenerator

  User->>Server: envia mensagem (webhook)
  Server->>InputHandler: process_input()
  InputHandler->>ContentExtractor: get_content_object()
  InputHandler->>Uploader: file_uploader()
  InputHandler->>ResponseProcessor: get_result_from_process()
  ResponseProcessor->>GeminiResponseGenerator: get_gemini_response()
  GeminiResponseGenerator-->>ResponseProcessor: resposta
  ResponseProcessor-->>InputHandler: resultado final
  InputHandler-->>Server: resposta processada
  Server-->>User: envia resposta
```

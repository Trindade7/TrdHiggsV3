🌐 Read in: [English](README.md) | [Português](README.pt.md)

# ComfyUI-HiggsV3-v02

**TTS em Português de Portugal Local com clonagem de voz — um nó personalizado para o ComfyUI**

## Contexto

Mudei-me recentemente para Portugal e, enquanto esperava que a papelada do meu visto ficasse resolvida (finalmente tive a minha entrevista na AIMA — está tudo tratado agora), aceitei alguns trabalhos como freelancer para me manter ocupado (nota: se tiverem um projeto interessante na área de IA, áudio ou ComfyUI, estou atualmente disponível para contratação — sintam-se à vontade para entrar em contacto! Sou um fullstack developer com experiência sólida na integração de IA em projetos de produção).

Um projeto em particular destacou-se: um cliente queria converter texto em fala utilizando a sua própria voz, de forma totalmente local — sem envios para a cloud, por motivos de privacidade. Parecia simples à primeira vista, mas ele fala Português de Portugal (PT-PT), e acontece que a maioria dos modelos de TTS são treinados quase exclusivamente com Português do Brasil. O sotaque, o ritmo e a cadência simplesmente não correspondiam ao que ele precisava.

Para resolver isto de forma adequada, acabei por escrever este nó personalizado para o ComfyUI. Ele lida com o Português Europeu de forma fiável e também divide textos longos de forma inteligente para evitar a degradação de qualidade que normalmente acontece quando se fornecem grandes blocos de texto aos modelos de TTS de uma só vez.

Acredito que esta abordagem — e honestamente o próprio nó — possa ser útil para quem trabalha com idiomas que não o inglês, onde "o modelo tecnicamente suporta a língua" não significa que soe realmente bem.

## Por que motivo a maioria dos pipelines de TTS tem dificuldades com o Português Europeu

A maioria dos modelos open-source de TTS anuncia "suporte para Português", mas na prática isso significa Português do Brasil. O Português Europeu tem uma redução vocálica distinta, uma prosódia diferente e uma cadência que os modelos treinados com sotaque brasileiro falham consistentemente. O resultado é um áudio que soa estranho para um ouvinte nativo de PT-PT.

O Higgs Audio v3 lida com isto significativamente melhor, especialmente quando combinado com uma referência de clonagem de voz gravada por um falante nativo de Português Europeu. O áudio de referência ancora o modelo ao sotaque, ritmo e entoação corretos.

## Como funciona a estratégia de divisão (Chunking)

Fornecer a um modelo TTS um grande bloco de texto normalmente faz com que a qualidade degrade — o ritmo perde-se, a pronúncia torna-se desleixada e o modelo pode perder a coerência por completo a partir de um certo tamanho.

Este nó divide o texto de entrada em pedaços de cerca de 250 caracteres, respeitando os limites das frases (dividindo em `.`, `!`, `?` e quebras de linha). Frases curtas são unidas até que a próxima exceda o limite. Cada pedaço é sintetizado de forma independente e, em seguida, as formas de onda (waveforms) resultantes são unidas ao longo do eixo temporal.

Isto mantém cada geração individual curta o suficiente para que o modelo a processe de forma limpa, produzindo um resultado final contínuo e sem interrupções.

## Funcionalidades

- Liga-se a um servidor Higgs Audio v3 a correr localmente — nada sai da sua máquina
- Divide automaticamente textos longos em pedaços ao nível da frase e une o resultado final
- Suporta clonagem de voz via áudio de referência + transcrição
- Temperatura e comprimento máximo de tokens configuráveis
- Funciona bem com Português Europeu e outros idiomas sub-representados

## Pré-requisitos

Precisa de um servidor de inferência do [Higgs Audio v3](https://huggingface.co/bosonai/higgs-tts-3-4b) em funcionamento. Para este projeto, estou a utilizar especificamente o [**sglang-omni**](https://github.com/sgl-project/sglang-omni) como servidor backend. O nó liga-se a ele via HTTP (por defeito: `http://127.0.0.1:8000`).

> **Nota:** Conseguir que os modelos de áudio sejam servidos corretamente pode ser complicado. Se desejar, posso criar uma configuração de deployment completa do ComfyUI e do sglang-omni para o seu caso de uso específico.

Certifique-se de que o servidor está iniciado antes de executar qualquer workflow que utilize este nó.

## Instalação

Clone o repositório para a sua diretoria de custom nodes do ComfyUI:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/ComfyUI-HiggsV3-v02.git
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Reinicie o ComfyUI. O nó aparecerá em **Audio/TTS** com o nome "Higgs Audio v3".

## Configuração Passo a Passo

1. **Inicie o servidor Higgs** na sua máquina local (porta por defeito: 8000).
2. **Abra o ComfyUI** e adicione o nó "Higgs Audio v3" a partir da categoria Audio/TTS.
3. **Insira o seu texto** no campo `text`. Tags de emoção como `<|emotion:enthusiasm|>` são suportadas.
4. **Defina o `server_url`** para apontar para o seu servidor em funcionamento (por defeito: `http://127.0.0.1:8000`).
5. **Ajuste os parâmetros de geração:**
   - `temperature` — controla a aleatoriedade (0.8 é um bom ponto de partida)
   - `max_new_tokens` — limite superior por pedaço (1024 por defeito, aumente para frases mais longas)
6. **Inicie a geração (Queue prompt).** O nó irá dividir o seu texto, gerar áudio para cada pedaço e devolver um único resultado AUDIO unido.

## Clonagem de Voz

Para clonar uma voz:

1. **Grave um clipe de referência** — um ficheiro WAV limpo de 5 a 15 segundos do locutor alvo. Com o mínimo de ruído de fundo e um ritmo natural.
2. **Ligue-o** à entrada `reference_audio` no nó (utilize um nó LoadAudio ou qualquer nó que devolva AUDIO).
3. **Forneça a transcrição** exata do que foi dito no clipe de referência através da entrada `reference_text`. A precisão é importante aqui — o modelo usa-a para alinhar as características da voz.
4. **Execute o workflow.** Todos os pedaços gerados utilizarão a voz de referência.

Especificamente para o Português Europeu, usar um clipe de referência de um falante nativo de PT-PT é o que faz a diferença entre ser "tecnicamente Português" e "soar realmente bem".

> **Nota:** O caminho (path) do ficheiro de áudio de referência é passado ao servidor Higgs como um caminho do sistema de ficheiros local. Tanto o ComfyUI como o servidor Higgs devem estar a correr na mesma máquina ou ter acesso ao mesmo sistema de ficheiros.

## Referência do Nó

**Nome do nó:** Higgs Audio v3

**Entradas (Inputs):**

| Entrada         | Tipo   | Obrigatório | Descrição                                   |
| --------------- | ------ | ----------- | ------------------------------------------- |
| text            | STRING | Sim         | Texto a sintetizar (suporta tags de emoção) |
| server_url      | STRING | Sim         | URL do servidor API Higgs                   |
| temperature     | FLOAT  | Sim         | Temperatura de amostragem (0.1 - 2.0)       |
| max_new_tokens  | INT    | Sim         | Máximo de tokens por pedaço (128 - 4096)    |
| reference_audio | AUDIO  | Não         | Áudio de referência para clonagem de voz    |
| reference_text  | STRING | Não         | Transcrição do áudio de referência          |

**Saída (Output):** AUDIO — um dicionário contendo a `waveform` (Tensor) e o `sample_rate` (int).

## Limitações Conhecidas e Possíveis Melhorias

- **Sem timeout nos pedidos.** Se o servidor Higgs bloquear, o ComfyUI bloqueia indefinidamente. Adicionar um timeout configurável (ex: 120s) resolveria isto.
- **O áudio de referência requer acesso local ao sistema de ficheiros.** O ficheiro WAV de referência é guardado num ficheiro temporário e o caminho é enviado ao servidor. Isto só funciona quando ambos correm na mesma máquina.
- **Frases demasiado longas não são sub-divididas.** Uma frase única com mais de 250 caracteres é enviada por inteiro, o que pode exceder o contexto efetivo do modelo. Uma divisão de recurso (fallback) por limites de palavras ajudaria.
- **O `top_k` está fixo (hardcoded) em 50.** Poderia ser exposto como uma entrada opcional no nó para maior controlo sobre a geração.
- **Sem lógica de repetição (retry).** Um erro de rede temporário faz falhar toda a geração. Implementar uma repetição com backoff melhoraria a fiabilidade.
- **Assunção do número de canais.** O passo de união assume que todos os pedaços devolvem o mesmo número de canais de áudio (mono ou estéreo). Uma incompatibilidade causaria um erro de execução.

## Licença

MIT

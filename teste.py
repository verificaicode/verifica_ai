from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch, File, FileState
import os
from dotenv import load_dotenv
import time

load_dotenv()

model = "gemini-2.0-flash"

# Chave e inicialização do cliente
client = genai.Client(api_key=os.getenv("API_KEY_GEMINI"))
google_search_tool = Tool(
            google_search = GoogleSearch()
)

start = time.time()

def upload_file(filename: str) -> File:
    state = FileState.PROCESSING
    file = client.files.upload(file=filename)

    while state != FileState.ACTIVE:
        state = client.files.get(name=file.name).state
        time.sleep(0.5)

    return file

def verify_caption_fact(caption: str, filepath: str) -> str:
    file = upload_file(filepath)

    research_prompt = "\n".join([
        f"CAPTION: “{caption}”",
        "1. Analise a legenda e o arquivo (se houver) e identifique os principais temas que devem ser verificados.",
        "2. Para cada tema, realize pesquisas simuladas com base em fontes confiáveis e atuais.",
        "3. Responda somente com um JSON no seguinte formato:",
        r"""{"tema1": ["resultado de uma pesquisa", "resultado de outra pesquisa"], "tema2": ["..."]}""",
        "Não adicione nenhuma explicação ou comentário fora do JSON."
    ])
    research_out = client.models.generate_content(
        model=model,
        contents=[research_prompt, file],
        config=GenerateContentConfig(
            tools=[google_search_tool],
            response_modalities=["TEXT"],
            temperature=0.0
        )
    ).text.strip()

    # print("Pesquisa simulada:\n", research_out)

    # Fase 2: Classificação + explicação detalhada
    classification_prompt = f"""
Você é um verificador de fatos especializado em desinformação. Analise cuidadosamente a legenda, o arquivo (se houver) e o resumo da pesquisa simulada abaixo.

Legenda: "{caption}"
Resumo da pesquisa: {research_out}

Com base nas evidências e fontes encontradas, classifique a legenda com uma das seguintes categorias, e escreva uma explicação detalhada e contextualizada com até 800 caracteres. Evite termos genéricos como “não há provas”. Foque em explicar *por que* a legenda é enganosa, falsa, fabricada, ou verdadeira, com base nas informações mais relevantes.

Categorias possíveis:
- 🤣 Satira ou paródia
- 🤷 Conexao falsa
- 🎭 Conteudo enganoso
- 🗓️ Contexto falso
- 👀 Conteudo impostor
- ✂️ Conteudo manipulado
- 🧪 Conteudo fabricado
- 🤔 Informacoes insuficientes
- ✅ É fato

Formato da resposta:
<categoria>
<explicação detalhada com base nas evidências>
A resposta deve ter obrigatoriamente no mínimo 700 caracteres e no máximo 850.
"""
    final_response = client.models.generate_content(
        model=model,
        contents=[classification_prompt, file],
        config=GenerateContentConfig(
            response_modalities=["TEXT"],
            temperature=0.3
        )
    ).text.strip()

    return final_response
# Uso:
result = verify_caption_fact("Muito ruim.", 'tmp/files/vl_DL8Gv-uPJ5D_s1.mp4')

print(time.time() - start)
print(result)

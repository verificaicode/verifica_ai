# Reimportar dependências após reset
import csv
from pathlib import Path
import random

# Estrutura base
base_template = (
    "O vídeo retrata um evento real, provavelmente relacionado a {evento}, onde {descricao_evento}. "
    "A legenda \"{legenda}\" adiciona uma camada de crítica social, sugerindo que {interpretacao_legenda}. "
    "A análise dos temas confirma que tanto {tema_confirmado_1} quanto {tema_confirmado_2} são reais."
)

# Dados para preenchimento
eventos = [
    "o aniversário da cidade de São Paulo",
    "uma celebração tradicional em uma cidade brasileira",
    "a inauguração de um programa social",
    "um evento comunitário de distribuição de alimentos",
    "uma festividade pública organizada pela prefeitura"
]

descricoes_evento = [
    "a distribuição de um bolo gigante gerou tumulto e desorganização",
    "a entrega de alimentos acabou em confusão",
    "a população formou filas desorganizadas para receber doações",
    "a distribuição gratuita atraiu uma multidão descontrolada",
    "a tentativa de distribuição acabou sendo marcada por empurra-empurra"
]

legendas = [
    "LET THEM EAT CAKE",
    "UM PEDAÇO PARA CADA UM",
    "DISTRIBUIÇÃO DE RIQUEZA",
    "FESTA PARA TODOS",
    "O POVO MERECE"
]

interpretacoes = [
    "a oferta pode ser uma medida superficial que não resolve os problemas de desigualdade",
    "a ação simbólica não substitui políticas públicas efetivas",
    "a distribuição de alimentos não soluciona a raiz da pobreza",
    "ações isoladas não resolvem a carência estrutural da população",
    "o gesto é mais publicitário do que funcional para quem precisa"
]

temas_1 = [
    "a tradição de eventos populares com distribuição gratuita",
    "o simbolismo de grandes festas públicas",
    "o uso político de ações de caridade",
    "a realização de festas com forte apelo popular",
    "ações simbólicas em datas comemorativas"
]

temas_2 = [
    "o risco de caos em distribuições públicas de alimentos",
    "a dificuldade de logística em ações massivas",
    "a possibilidade de tumulto em aglomerações",
    "o problema da má organização em eventos públicos",
    "a tensão social gerada em ações de distribuição coletiva"
]

# Gerar as frases
generated_critique_explanations = []

for _ in range(50):
    frase = base_template.format(
        evento=random.choice(eventos),
        descricao_evento=random.choice(descricoes_evento),
        legenda=random.choice(legendas),
        interpretacao_legenda=random.choice(interpretacoes),
        tema_confirmado_1=random.choice(temas_1),
        tema_confirmado_2=random.choice(temas_2),
    )
    generated_critique_explanations.append(frase)

# Salvar em CSV
csv_path = Path("explicacoes_criticas_bolo.csv")

with open(csv_path, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["explicacao"])
    for explanation in generated_critique_explanations:
        writer.writerow([explanation])


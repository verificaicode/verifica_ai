from verifica_ai.types import DetalhedFont

class PosProcessor:
    """
    Realiza algumas melhorias na resposta.

    :param response: Uma tupla contendo a resposta gerada pela LLM e as uma lista com as fontes utilizadas para a pesquisa.
    :type response: tuple[str, list[str]]
    """

    def get_result(self, response: tuple[str, list[str]]) -> str:
        response_text, fonts = response

        fonts = self.order_by_confiability(fonts)

        return self.process_response(response_text, fonts)

    def process_response(self, response_text: str, fonts: list[str]) -> str:
        """
        Processa a resposta gerada pelo Gemini.

        Garante que a resposta final não ultrapasse 1000 caracteres, colocando o máximo de fontes possível que não ultrapasse o limite.
        
        :param response_text: Resposta bruta retornada pelo Gemini.

        :param fonts: Uma lista contendo as fontes utilizadas para as pesquisas acerca do conteúdo da mensagem.

        :return response_text: String contendo a explicação e suas fontes.
        """

        formated_fonts = ""
        acc_fonts = []

        for font in fonts:
            acc_fonts.append(font)
            temp_formated = "\n\nFontes:\n" + "\n\n".join(acc_fonts)
            if len(f"{response_text}{temp_formated}") > 1000:
                # Se ultrapassou, para antes de adicionar essa fonte
                acc_fonts.pop()
                break

            formated_fonts = ("\n\nFontes:\n" + "\n\n".join(acc_fonts)) if len(fonts) > 0 else ""

        return f"{response_text}{formated_fonts}"
    
    def order_by_confiability(self, detalhed_fonts: list[DetalhedFont]) -> list[str]:
        """
        Ordena as fontes por confiabilidade.

        :param detalhed_fonts: Uma lista contendo `DetalhedFont` que será processada.

        :return: Uma lista ordenada contendo URIs ordenadas por confiabilidade.
        """

        confiable_sites_dict = {
            "weather.com": ["The Weather Channel", 1.00],
            "bbc.com": ["BBC", 0.95],
            "g1.globo.com": ["G1", 0.92],
            "reuters.com": ["Reuters", 0.92],
            "apnews.com": ["Associated Press", 0.91],
            "folha.uol.com.br": ["Folha de S.Paulo", 0.91],
            "estadao.com.br": ["Estadão", 0.90],
            "nytimes.com": ["The New York Times", 0.90],
            "snopes.com": ["Snopes", 0.90],
            "nexojornal.com.br": ["Nexo Jornal", 0.89],
            "politifact.com": ["PolitiFact", 0.89],
            "npr.org": ["NPR", 0.89],
            "oglobo.globo.com": ["O Globo", 0.89],
            "uol.com.br": ["UOL Notícias", 0.88],
            "theguardian.com": ["The Guardian", 0.88],
            "cnnbrasil.com.br": ["CNN Brasil", 0.87],
            "poder360.com.br": ["Poder360", 0.86],
            "veja.abril.com.br": ["Veja", 0.85],
            "theglobeandmail.com": ["The Globe and Mail", 0.85],
            "elpais.com": ["El País", 0.84],
            "correiobraziliense.com.br": ["Correio Braziliense", 0.83],
            "cbc.ca": ["CBC News", 0.83], 
            "cbsnews.com": ["CBS News", 0.83],
            "aljazeera.com": ["Al Jazeera", 0.82],
            "cartacapital.com.br": ["CartaCapital", 0.81],
            "dw.com": ["Deutsche Welle", 0.80],
            "r7.com": ["R7 Notícias", 0.80],
            "foxnews.com": ["Fox News", 0.75]
        }

        ordenated_fonts = sorted(detalhed_fonts, key=lambda f: confiable_sites_dict[f.domain][1] if f.domain in confiable_sites_dict else 0, reverse=True)
        
        # Extrai apenas os URIs
        return [f.uri for f in ordenated_fonts]
        
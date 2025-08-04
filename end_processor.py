class EndProcessor:
    def get_result(self, response: str) -> str:
        # response = response.split("É fato")[1] if "É fato" in response else response.split("É fake")[1] if "É fake" in response else response


        # x = [self.is_fact_tokenizer.infer_vector(response.lower().split())]

        # return f"{response}{fonts}"
        return response

        classe = self.models.is_fact_predict(response)
        print(classe)
        if classe == 2:
            return f"✅ É fato\n\n{response}"
        
        elif classe == 1:
            return f"🤔 Informações insuficientes\n\n{response}"
        
        else:
            type_fake_class = self.type_fake_name_classes[self.models.type_fake_predict(response)]
            return f"{type_fake_class}\n\n{response}"
def extrair_invoice(pdf):
    import pandas as pd
    import pdfplumber
    import re

    dados = []
    sns_por_item = {}

    with pdfplumber.open(pdf) as pdf_file:
        texto = ""
        for page in pdf_file.pages:
            texto += page.extract_text() + "\n"

    linhas = texto.split("\n")

    current_item = None

    for linha in linhas:
        linha = linha.strip()

        # Detecta linha principal do item
        match = re.match(r"^\d+\s+(\d+)\s+([\d\.]+)\s+qty\s+([\d']+\.\d+)\s+([\d']+\.\d+)", linha)

        if match:
            codigo = match.group(1)
            quantidade = float(match.group(2))

            valor_unit = float(match.group(3).replace("'", ""))
            valor_total = float(match.group(4).replace("'", ""))

            current_item = codigo

            dados.append({
                "codigo": codigo,
                "quantidade_invoice": quantidade,
                "valor_unit_invoice": valor_unit,
                "valor_total_invoice": valor_total
            })

            sns_por_item[codigo] = []

        # Captura SN
        elif "SN:" in linha and current_item:
            sn = linha.replace("SN:", "").strip()
            sns_por_item[current_item].append(sn)

    df_invoice = pd.DataFrame(dados)

    return df_invoice, sns_por_item

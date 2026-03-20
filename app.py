import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO

st.set_page_config(page_title="BRISK Import Validator", layout="centered")

st.title("BRISK Import Validator")
st.caption("Automação de integração e validação de itens (DI/DUIMP)")

excel_file = st.file_uploader("Upload Excel - Instrução", type=["xlsx"])
pdf_file = st.file_uploader("Upload PDF - Invoice", type=["pdf"])

def extrair_invoice(pdf):
    dados = []
    sns_por_item = {}

    with pdfplumber.open(pdf) as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text() + "\n"

    linhas = texto.split("\n")
    current_item = None

    for linha in linhas:
        match_item = re.match(r"^\d+\s+(\d+)\s+([\d\.]+)\s+qty\s+([\d',\.]+)\s+([\d',\.]+)", linha)
        if match_item:
            current_item = match_item.group(1)
            dados.append({
                "codigo": current_item,
                "quantidade_invoice": float(match_item.group(2)),
                "valor_unit_invoice": float(match_item.group(3).replace("'", "").replace(",", ".")),
                "valor_total_invoice": float(match_item.group(4).replace("'", "").replace(",", "."))
            })
            sns_por_item[current_item] = []
        
        if "SN:" in linha and current_item:
            sns = re.findall(r"SN:\s*([\w\d]+)", linha)
            sns_por_item[current_item].extend(sns)

    return pd.DataFrame(dados), sns_por_item

def processar(excel_file, pdf_file):
    df_instrucao = pd.read_excel(excel_file)
    df_invoice, sns = extrair_invoice(pdf_file)

    resultado = []

    for _, row in df_instrucao.iterrows():
        codigo = str(row.get("codigo", "")).strip()
        match = df_invoice[df_invoice["codigo"] == codigo]

        status = "OK"
        obs = ""
        qtd = row.get("quantidade", 0)
        valor = row.get("valor_unitario", 0)

        if match.empty:
            status = "ITEM NÃO ENCONTRADO"
            obs = "Não localizado na invoice"
            sn_texto = ""
        else:
            inv = match.iloc[0]

            if qtd != inv["quantidade_invoice"]:
                status = "DIVERGÊNCIA QTD"

            if valor != inv["valor_unit_invoice"]:
                status = "DIVERGÊNCIA VALOR"

            lista_sn = sns.get(codigo, [])
            sn_texto = " / ".join([f"SN: {sn}" for sn in lista_sn])

        descricao_final = f"{row.get('descricao', '')} {sn_texto}"

        resultado.append({
            "codigo": codigo,
            "descricao": descricao_final,
            "ncm": row.get("ncm", ""),
            "quantidade": qtd,
            "valor_unitario": valor,
            "status": status,
            "observacao": obs
        })

    return pd.DataFrame(resultado)

def gerar_excel(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name="Itens", index=False)

        resumo = pd.DataFrame({
            "Métrica": ["Total Itens", "OK", "Divergências"],
            "Valor": [
                len(df),
                len(df[df["status"] == "OK"]),
                len(df[df["status"] != "OK"])
            ]
        })

        resumo.to_excel(writer, sheet_name="Validação", index=False)

    return output.getvalue()

if st.button("Processar Arquivos"):
    if not excel_file or not pdf_file:
        st.error("Envie os dois arquivos obrigatórios")
    else:
        with st.spinner("Processando..."):
            df_final = processar(excel_file, pdf_file)

            st.success("Processamento concluído!")

            st.subheader("Resumo")
            st.write(f"Total de itens: {len(df_final)}")
            st.write(f"OK: {len(df_final[df_final['status']=='OK'])}")
            st.write(f"Divergências: {len(df_final[df_final['status']!='OK'])}")

            excel_bytes = gerar_excel(df_final)

            st.download_button(
                label="Baixar Excel Integrado",
                data=excel_bytes,
                file_name="Integracao_Itens_Validado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

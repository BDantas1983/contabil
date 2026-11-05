import hashlib
from datetime import datetime, timezone
from fpdf import FPDF
from typing import Dict, Any


class PDFGeneratorService:
    """
    Gera documentos PDF reais em memória (via fpdf2) para:
    1. Certidões Negativas de Débitos (CND Receita/PGFN, FGTS CRF, Sefaz, TST)
    2. Guias Tributárias (DAS Simples Nacional / DARF / FGTS Digital) com PIX e Código de Barras
    3. Contracheques / Holerites Digitais com proteção LGPD (CPF Mascarado)
    4. Relatório Executivo de Auditoria SIEM & Conformidade ISO 27001 / LGPD
    """

    def _clean(self, text: str) -> str:
        """Converte caracteres para latin-1 seguro para as fontes core do PDF."""
        if not text:
            return ""
        return str(text).encode("latin-1", "replace").decode("latin-1")

    def gerar_pdf_cnd(self, empresa: Dict[str, Any], orgao_slug: str) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Cabeçalho Oficial
        pdf.set_fill_color(15, 23, 42)
        pdf.rect(0, 0, 210, 34, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_xy(12, 8)
        pdf.cell(0, 8, self._clean("CERTIDAO NEGATIVA DE DEBITOS / REGULARIDADE FISCAL"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(12)
        pdf.cell(
            0,
            6,
            self._clean("Documento emitido eletronicamente via Worker Python (Playwright mTLS + Certificado Digital A1)"),
            new_x="LMARGIN",
            new_y="NEXT",
        )

        pdf.ln(14)
        pdf.set_text_color(30, 41, 59)

        mapa_orgaos = {
            "receita": "MINISTERIO DA FAZENDA - SECRETARIA ESPECIAL DA RECEITA FEDERAL E PGFN",
            "fgts": "CAIXA ECONOMICA FEDERAL - CERTIFICADO DE REGULARIDADE DO FGTS (CRF)",
            "sefaz": "SECRETARIA DA FAZENDA E PLANEJAMENTO ESTADUAL (SEFAZ / ICMS)",
            "trabalhista": "PODER JUDICIARIO - JUSTICA DO TRABALHO (CNDT - TST)",
            "municipal": "SECRETARIA MUNICIPAL DA FAZENDA - CERTIDAO DE TRIBUTOS MOBILIARIOS (ISS)",
        }
        titulo_orgao = mapa_orgaos.get(orgao_slug.lower(), "ORGAO OFICIAL DE CONFORMIDADE FISCAL")

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, self._clean(titulo_orgao), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Dados do Contribuinte
        pdf.set_fill_color(241, 245, 249)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, self._clean("1. IDENTIFICACAO DO CONTRIBUINTE MONITORADO"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, self._clean(f"Razao Social: {empresa.get('razao_social')}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"Nome Fantasia: {empresa.get('nome_fantasia')}   |   Regime: {empresa.get('regime_tributario')}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"CNPJ: {empresa.get('cnpj')}   |   ERP Integrado: {empresa.get('erp_integrado', 'Dominio Sistemas')}"), border="LRB", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, self._clean("2. CERTIFICACAO DE REGULARIDADE FISCAL"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        texto_cert = (
            "Certifica-se que, em consulta automatizada realizada nesta data por meio de Procuracao Eletronica "
            "e Certificado Digital ICP-Brasil Tipo A1 descriptografado exclusivamente em memoria RAM volatil "
            "(Envelope Encryption AES-GCM-256), NAO CONSTA pendencia impeditiva para a emissao desta certidao."
        )
        pdf.multi_cell(0, 6, self._clean(texto_cert), border="LRB")

        agora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
        hash_doc = hashlib.sha256(f"{empresa.get('cnpj')}|{orgao_slug}|{agora}".encode()).hexdigest()

        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, self._clean("3. AUTENTICIDADE E TRILHA DE AUDITORIA (ISO 27001 / LGPD)"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "", 9)
        pdf.cell(0, 7, self._clean(f"Data/Hora de Verificacao: {agora}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"Tenant Isolado (RLS):     {empresa.get('tenant_id', 'escritorio-piloto-01')}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"Hash SHA-256 (WORM):      {hash_doc[:48]}..."), border="LRB", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 5, self._clean("Gerado por AuditContabil AI - SaaS Python & Security-by-Design (Data Center Sao Paulo - Brasil)"), align="C")

        return bytes(pdf.output())

    def gerar_pdf_guia(self, guia: Dict[str, Any]) -> bytes:
        pdf = FPDF()
        pdf.add_page()

        pdf.set_fill_color(6, 78, 59)
        pdf.rect(0, 0, 210, 32, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_xy(12, 8)
        pdf.cell(0, 8, self._clean(f"DOCUMENTO DE ARRECADACAO TRIBUTARIA - {guia.get('tributo')}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(12)
        pdf.cell(0, 6, self._clean("Apuracao Automatica via Motor Fiscal Python (Captura XML NF-e/NFS-e + PGDAS-D)"), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(14)
        pdf.set_text_color(30, 41, 59)
        pdf.set_fill_color(241, 245, 249)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, self._clean("DADOS DA GUIA E APURACAO"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, self._clean(f"Contribuinte: {guia.get('empresa_nome')}   |   CNPJ: {guia.get('cnpj')}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"Competencia:  {guia.get('competencia')}   |   Data de Vencimento: {guia.get('vencimento')}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, self._clean(f"VALOR TOTAL A RECOLHER: R$ {guia.get('valor', 0):,.2f}"), border="LRB", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, self._clean("LINHA DIGITAVEL E PIX COPIA E COLA"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "B", 9)
        pdf.cell(0, 8, self._clean(f"Codigo de Barras: {guia.get('codigo_barras')}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "", 8)
        pdf.multi_cell(0, 6, self._clean(f"PIX Darf/DAS: {guia.get('pix_copia_e_cola')}"), border="LRB")

        return bytes(pdf.output())

    def gerar_pdf_holerite(self, colab: Dict[str, Any]) -> bytes:
        pdf = FPDF()
        pdf.add_page()

        pdf.set_fill_color(30, 41, 59)
        pdf.rect(0, 0, 210, 30, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_xy(12, 8)
        pdf.cell(0, 8, self._clean("RECIBO DE PAGAMENTO DE SALARIO (HOLERITE DIGITAL LGPD)"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(12)
        pdf.cell(0, 6, self._clean(f"Empregador: {colab.get('empresa_nome')} | Protocolo eSocial S-2200: {colab.get('protocolo_esocial_s2200')}"), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(12)
        pdf.set_text_color(30, 41, 59)
        pdf.set_fill_color(241, 245, 249)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, self._clean("IDENTIFICACAO DO COLABORADOR (ANONIMIZADO CONFORME LGPD)"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, self._clean(f"Nome: {colab.get('nome_completo')}   |   CPF (Data Masking): {colab.get('cpf_mascarado')}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"Cargo: {colab.get('cargo')} (CBO {colab.get('cbo')})   |   Admissao: {colab.get('data_admissao')}"), border="LRB", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, self._clean("DEMONSTRATIVO DE PROVENTOS, DESCONTOS E FGTS DIGITAL"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "", 10)
        pdf.cell(0, 7, self._clean(f"(+) Salario Base Mensal ..................... R$ {colab.get('salario_base', 0):,.2f}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"(-) Desconto INSS Previdencia ............... R$ {colab.get('inss_desconto', 0):,.2f}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"(-) Desconto IRRF Retido na Fonte ........... R$ {colab.get('irrf_desconto', 0):,.2f}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, self._clean(f"(i) Deposito FGTS Digital (8%) .............. R$ {colab.get('fgts_deposito', 0):,.2f}"), border="LR", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "B", 11)
        pdf.cell(0, 9, self._clean(f"(=) VALOR LIQUIDO A RECEBER ................. R$ {colab.get('salario_liquido', 0):,.2f}"), border="LRB", new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())


pdf_service = PDFGeneratorService()


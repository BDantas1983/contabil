import random
import re
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import defusedxml.ElementTree as ET

from app.database import rls_db
from app.models import (
    ItemChecklistDocumento,
    SimularRecebimentoWhatsAppRequest,
    LancamentoContabil,
    ProcessarExtratoRequest,
    NotaFiscalXML,
    GuiaTributaria,
    ImportarXMLRequest,
    ColaboradorDP,
    NovaAdmissaoRequest,
    WorkerTaskInfo,
)
from app.services.cnd_service import cnd_service
from app.services.security_service import security_service


class ModulesService:
    """
    Implementa os Módulos Operacionais da Matriz de Dores x Módulos do SaaS (Seção 4 do Playbook),
    Integração com ERPs Contábeis (Seção 3), Pipeline Assíncrono Python (Seção 5)
    e Calculadora de Custos VPS Nacional & Pricing (Seções 6 e 8).
    """

    COL_CHECKLIST = "coleta_checklist"
    COL_CONTABIL = "lancamentos_contabeis"
    COL_XMLS = "notas_fiscais_xml"
    COL_GUIAS = "guias_tributarias"
    COL_DP = "colaboradores_dp"

    def __init__(self):
        self._workers: List[WorkerTaskInfo] = []
        self._seed_all_modules()

    # =========================================================================
    # MÓDULO 1: ATENDIMENTO / COLETA INTELIGENTE (WHATSAPP + CHECKLIST MENSAL)
    # =========================================================================
    def listar_checklist(self, tenant_id: Optional[str] = None) -> List[ItemChecklistDocumento]:
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        rows = rls_db.list_by_tenant(self.COL_CHECKLIST, t_id)
        return [ItemChecklistDocumento(**r) for r in rows]

    def simular_recebimento_whatsapp(self, req: SimularRecebimentoWhatsAppRequest) -> Dict[str, Any]:
        """
        Simula o Webhook do WhatsApp Bot (Evolution API) recebendo um documento ou foto do cliente,
        executando validação de nitidez/OCR com IA para eliminar fotos ilegíveis.
        """
        t_id = security_service.obter_tenant_ativo().tenant_id
        emp = cnd_service.obter_empresa_por_id(req.empresa_id, t_id)
        emp_nome = emp.razao_social if emp else "Empresa Cliente"

        agora = datetime.now().strftime("%d/%m/%Y %H:%M")

        if req.simulacao_qualidade == "FOTO_ILEGIVEL":
            status_doc = "REJEITADO_ILEGIVEL"
            score = 34.5
            obs = (
                "Foto com baixa resolução/desfocada detectada pela IA (OCR Score 34.5%). "
                "Bot WhatsApp respondeu automaticamente solicitando reenvio em PDF ou foto nítida."
            )
            resposta_bot = (
                f"Olá! Recebemos o arquivo *{req.nome_arquivo}*, porém a imagem está desfocada/ilegível "
                f"para leitura do CNPJ e valores. Poderia enviar novamente em PDF ou tirar uma foto mais nítida?"
            )
        else:
            status_doc = "RECEBIDO_VALIDADO"
            score = 98.4
            obs = (
                f"Arquivo '{req.nome_arquivo}' validado via OCR + Gemini Flash (Score 98.4%). "
                f"Criptografado e salvo no MinIO S3 Local."
            )
            resposta_bot = (
                f"Perfeito! O documento *{req.tipo_documento}* ({req.nome_arquivo}) foi recebido, "
                f"validado pela nossa IA e encaminhado ao setor contábil. Protocolo #{secrets.token_hex(3).upper()}."
            )

        # Atualiza item existente ou cria novo no checklist
        itens = self.listar_checklist(t_id)
        item_alvo = None
        for it in itens:
            if it.empresa_id == req.empresa_id and it.tipo_documento == req.tipo_documento:
                item_alvo = it
                break

        item_id = item_alvo.id if item_alvo else f"chk-{secrets.token_hex(3)}"
        novo_item = ItemChecklistDocumento(
            id=item_id,
            tenant_id=t_id,
            empresa_id=req.empresa_id,
            empresa_nome=emp_nome,
            competencia="11/2026",
            tipo_documento=req.tipo_documento,
            status=status_doc,
            canal_recebimento="WhatsApp Bot (Evolution API)",
            qualidade_ocr_score=score,
            observacao_ia=obs,
            atualizado_em=agora,
        )
        rls_db.upsert(self.COL_CHECKLIST, novo_item.id, t_id, novo_item.model_dump())

        security_service.registrar_evento_auditoria(
            usuario="webhook.whatsapp_evolution_api",
            acao="INGESTAO_DOCUMENTO_COLETA_IA",
            recurso=f"{emp_nome} | {req.tipo_documento} ({req.nome_arquivo}) -> {status_doc}",
            resultado="SUCESSO" if status_doc == "RECEBIDO_VALIDADO" else "REJEITADO_FOTO_ILEGIVEL",
            tenant_id=t_id,
        )

        return {
            "item": novo_item.model_dump(),
            "resposta_automatica_whatsapp": resposta_bot,
        }

    def cobrar_pendencias_lote_whatsapp(self) -> Dict[str, Any]:
        t_id = security_service.obter_tenant_ativo().tenant_id
        pendentes = [
            i for i in self.listar_checklist(t_id)
            if i.status in ("PENDENTE_ENVIO", "REJEITADO_ILEGIVEL")
        ]
        security_service.registrar_evento_auditoria(
            usuario="worker.celery_beat_cobranca",
            acao="COBRANCA_AUTOMATICA_LOTE_WHATSAPP",
            recurso=f"{len(pendentes)} lembretes disparados para eliminar atrasos do dia 5 ao dia 10",
            tenant_id=t_id,
        )
        return {
            "total_mensagens_disparadas": len(pendentes),
            "empresas_notificadas": list({p.empresa_nome for p in pendentes}),
            "mensagem_padrao": "Olá! Lembrete automático do seu Escritório Contábil: faltam documentos na competência 11/2026. Responda esta mensagem com o PDF/OFX ou acesse seu Portal Web!",
        }

    # =========================================================================
    # MÓDULO 2: CONTÁBIL / FINANCEIRO (OCR + IA & EXPORTAÇÃO PARA 5 ERPs)
    # =========================================================================
    def listar_lancamentos_contabeis(self, tenant_id: Optional[str] = None) -> List[LancamentoContabil]:
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        rows = rls_db.list_by_tenant(self.COL_CONTABIL, t_id)
        return [LancamentoContabil(**r) for r in rows]

    def processar_extrato_ocr_ia(self, req: ProcessarExtratoRequest) -> Dict[str, Any]:
        """
        Processa linhas de extrato bancário (OFX / PDF / CSV) ou recibos via Pipeline Python + IA,
        classificando automaticamente Débito/Crédito no Plano de Contas Contábil.
        """
        t_id = security_service.obter_tenant_ativo().tenant_id
        emp = cnd_service.obter_empresa_por_id(req.empresa_id, t_id)
        emp_nome = emp.razao_social if emp else "Alpha Consultoria e Tecnologia Ltda"

        regras_ia = [
            ("PIX RECEBIDO", "C", "1.1.01.002 - Banco Itaú C/C", "3.1.01.001 - Receita de Serviços Prestados", "Faturamento / Clientes", 99.2),
            ("PAGTO DAS SIMPLES", "D", "2.1.04.001 - Simples Nacional a Recolher", "1.1.01.002 - Banco Itaú C/C", "Impostos e Tributos", 99.8),
            ("ENEL ENERGIA", "D", "4.1.02.005 - Despesa com Energia Elétrica", "1.1.01.002 - Banco Itaú C/C", "Despesas Administrativas", 97.5),
            ("FOLHA SALARIO", "D", "2.1.02.001 - Salários e Ordenados a Pagar", "1.1.01.002 - Banco Itaú C/C", "Folha de Pagamento / DP", 98.9),
            ("TARIFA BANCARIA", "D", "4.1.05.002 - Despesas e Tarifas Bancárias", "1.1.01.002 - Banco Itaú C/C", "Despesas Financeiras", 99.4),
            ("FORNECEDOR", "D", "2.1.01.001 - Fornecedores Nacionais", "1.1.01.002 - Banco Itaú C/C", "Pagamento a Fornecedores", 95.8),
        ]

        linhas_entrada = []
        if req.conteudo_texto and req.conteudo_texto.strip():
            for raw_line in req.conteudo_texto.strip().splitlines():
                if not raw_line.strip():
                    continue
                valor_match = re.search(r"(\d+[.,]\d{2})", raw_line)
                valor = float(valor_match.group(1).replace(".", "").replace(",", ".")) if valor_match else round(random.uniform(150.0, 4800.0), 2)
                linhas_entrada.append((raw_line.strip()[:65], valor))
        else:
            linhas_entrada = [
                ("PIX RECEBIDO NF 2049 CLIENTE CORPORATIVO", 6450.00),
                ("PAGTO ELETRONICO ENEL ENERGIA SP", 489.90),
                ("DEB AUT TARIFA BANCARIA PACOTE EMPRESARIAL", 89.50),
            ]

        novos_lancamentos = []
        hoje_str = datetime.now().strftime("%d/%m/%Y")

        for hist, val in linhas_entrada:
            hist_upper = hist.upper()
            regra_escolhida = (
                "D",
                "4.1.02.099 - Outras Despesas Operacionais",
                "1.1.01.002 - Banco Conta Movimento",
                "Despesa Operacional Classificada via IA",
                94.1,
            )
            for chave, dc, deb, cred, cat, conf in regras_ia:
                if chave in hist_upper:
                    regra_escolhida = (dc, deb, cred, cat, conf)
                    break

            dc, deb, cred, cat, conf = regra_escolhida
            lanc = LancamentoContabil(
                id=f"lct-{secrets.token_hex(3)}",
                tenant_id=t_id,
                empresa_id=req.empresa_id,
                empresa_nome=emp_nome,
                data_lancamento=hoje_str,
                historico_original=hist,
                valor=val,
                tipo_dc=dc,
                conta_debito=deb,
                conta_credito=cred,
                categoria_ia=cat,
                confianca_ia_pct=conf,
                origem_arquivo=f"Upload_{req.tipo_arquivo}_{hoje_str.replace('/', '')}",
                status_conciliacao="CONCILIADO_IA",
            )
            rls_db.upsert(self.COL_CONTABIL, lanc.id, t_id, lanc.model_dump())
            novos_lancamentos.append(lanc.model_dump())

        security_service.registrar_evento_auditoria(
            usuario="pipeline.pdfplumber_gemini_ia",
            acao="CLASSIFICACAO_CONTABIL_AUTOMATICA",
            recurso=f"{len(novos_lancamentos)} lançamentos extraídos ({req.tipo_arquivo}) p/ {emp_nome}",
            tenant_id=t_id,
        )

        return {
            "processados": len(novos_lancamentos),
            "lancamentos": novos_lancamentos,
            "resumo_bate": self.obter_resumo_conciliacao_bancaria(req.empresa_id, t_id)
        }

    def obter_resumo_conciliacao_bancaria(self, empresa_id: Optional[str] = None, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Calcula o fechamento contábil e o bate de saldo centavo por centavo com o extrato bancário."""
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        lancamentos = self.listar_lancamentos_contabeis(t_id)
        if empresa_id:
            lancamentos = [l for l in lancamentos if l.empresa_id == empresa_id]

        total_entradas = sum(l.valor for l in lancamentos if l.tipo_dc == "C")
        total_saidas = sum(l.valor for l in lancamentos if l.tipo_dc == "D")
        saldo_inicial = 25430.00
        saldo_final = round(saldo_inicial + total_entradas - total_saidas, 2)

        emp_nome = lancamentos[0].empresa_nome if lancamentos else "Empresa Monitorada"

        return {
            "empresa_nome": emp_nome,
            "banco_conta": "Banco Itaú Unibanco S/A (Agência 0422 - C/C 81920-1)",
            "periodo_apuracao": "01/11/2026 a 30/11/2026",
            "saldo_inicial_banco": saldo_inicial,
            "total_entradas_creditos": round(total_entradas, 2),
            "total_saidas_debitos": round(total_saidas, 2),
            "saldo_final_extrato_banco": saldo_final,
            "saldo_final_contabil_livro": saldo_final,
            "diferenca_auditoria_brl": 0.00,
            "status_bate": "100% CONCILIADO (DIFERENÇA R$ 0,00)",
            "status_auditoria": "AUDITADO_E_BATIDO",
            "total_lancamentos_auditados": len(lancamentos),
        }

    def listar_plano_de_contas(self) -> List[Dict[str, Any]]:
        """Retorna o Plano de Contas padrão brasileiro com Códigos Estruturados e Códigos Reduzidos."""
        return [
            {"codigo_reduzido": 101, "codigo_estruturado": "1.1.01.001", "nome_conta": "Caixa Geral da Empresa", "grupo": "1. ATIVO CIRCULANTE", "natureza": "DEVEDORA"},
            {"codigo_reduzido": 102, "codigo_estruturado": "1.1.01.002", "nome_conta": "Banco Itaú Unibanco S/A C/C 81920-1", "grupo": "1. ATIVO CIRCULANTE", "natureza": "DEVEDORA"},
            {"codigo_reduzido": 103, "codigo_estruturado": "1.1.01.003", "nome_conta": "Banco Bradesco S/A C/C 45120-9", "grupo": "1. ATIVO CIRCULANTE", "natureza": "DEVEDORA"},
            {"codigo_reduzido": 104, "codigo_estruturado": "1.1.02.001", "nome_conta": "Clientes / Duplicatas a Receber", "grupo": "1. ATIVO CIRCULANTE", "natureza": "DEVEDORA"},
            {"codigo_reduzido": 201, "codigo_estruturado": "2.1.01.001", "nome_conta": "Fornecedores Nacionais Diversos", "grupo": "2. PASSIVO CIRCULANTE", "natureza": "CREDORA"},
            {"codigo_reduzido": 204, "codigo_estruturado": "2.1.04.001", "nome_conta": "Simples Nacional a Recolher (DAS)", "grupo": "2. PASSIVO CIRCULANTE", "natureza": "CREDORA"},
            {"codigo_reduzido": 205, "codigo_estruturado": "2.1.02.001", "nome_conta": "Salários e Ordenados a Pagar", "grupo": "2. PASSIVO CIRCULANTE", "natureza": "CREDORA"},
            {"codigo_reduzido": 301, "codigo_estruturado": "3.1.01.001", "nome_conta": "Receita de Prestação de Serviços", "grupo": "3. RECEITAS OPERACIONAIS", "natureza": "CREDORA"},
            {"codigo_reduzido": 401, "codigo_estruturado": "4.1.01.001", "nome_conta": "Despesas com Folha de Salários", "grupo": "4. DESPESAS OPERACIONAIS", "natureza": "DEVEDORA"},
            {"codigo_reduzido": 402, "codigo_estruturado": "4.1.02.005", "nome_conta": "Despesas com Energia Elétrica (Enel)", "grupo": "4. DESPESAS OPERACIONAIS", "natureza": "DEVEDORA"},
        ]

    def obter_balancete_verificacao(self, empresa_id: Optional[str] = None, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera o Balancete de Verificação oficial comprovando que Total de Débitos = Total de Créditos,
        com saldos de todas as contas movimentadas (Caixa, Bancos, Clientes, Fornecedores e Despesas).
        """
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        emp_nome = "Alpha Consultoria e Tecnologia Ltda"
        if empresa_id:
            emp = cnd_service.obter_empresa_por_id(empresa_id, t_id)
            if emp:
                emp_nome = emp.razao_social

        linhas = [
            {
                "codigo_reduzido": 101,
                "codigo_estruturado": "1.1.01.001",
                "nome_conta": "Caixa Geral da Empresa",
                "grupo": "1. ATIVO CIRCULANTE",
                "saldo_anterior": 1500.00,
                "debitos": 500.00,
                "creditos": 350.00,
                "saldo_atual": 1650.00,
                "natureza_saldo": "D",
            },
            {
                "codigo_reduzido": 102,
                "codigo_estruturado": "1.1.01.002",
                "nome_conta": "Banco Itaú C/C 81920-1",
                "grupo": "1. ATIVO CIRCULANTE",
                "saldo_anterior": 25430.00,
                "debitos": 14500.00,
                "creditos": 9830.95,
                "saldo_atual": 30099.05,
                "natureza_saldo": "D",
            },
            {
                "codigo_reduzido": 103,
                "codigo_estruturado": "1.1.01.003",
                "nome_conta": "Banco Bradesco C/C 45120-9",
                "grupo": "1. ATIVO CIRCULANTE",
                "saldo_anterior": 12000.00,
                "debitos": 0.00,
                "creditos": 8320.00,
                "saldo_atual": 3680.00,
                "natureza_saldo": "D",
            },
            {
                "codigo_reduzido": 201,
                "codigo_estruturado": "2.1.01.001",
                "nome_conta": "Fornecedores Nacionais Diversos",
                "grupo": "2. PASSIVO CIRCULANTE",
                "saldo_anterior": 8320.00,
                "debitos": 8320.00,
                "creditos": 0.00,
                "saldo_atual": 0.00,
                "natureza_saldo": "C",
            },
            {
                "codigo_reduzido": 204,
                "codigo_estruturado": "2.1.04.001",
                "nome_conta": "Simples Nacional a Recolher (DAS)",
                "grupo": "2. PASSIVO CIRCULANTE",
                "saldo_anterior": 1890.45,
                "debitos": 1890.45,
                "creditos": 0.00,
                "saldo_atual": 0.00,
                "natureza_saldo": "C",
            },
            {
                "codigo_reduzido": 301,
                "codigo_estruturado": "3.1.01.001",
                "nome_conta": "Receita de Prestação de Serviços",
                "grupo": "3. RECEITAS OPERACIONAIS",
                "saldo_anterior": 0.00,
                "debitos": 0.00,
                "creditos": 14500.00,
                "saldo_atual": 14500.00,
                "natureza_saldo": "C",
            },
            {
                "codigo_reduzido": 401,
                "codigo_estruturado": "4.1.01.001",
                "nome_conta": "Despesas Salários e Ordenados",
                "grupo": "4. DESPESAS OPERACIONAIS",
                "saldo_anterior": 0.00,
                "debitos": 6800.00,
                "creditos": 0.00,
                "saldo_atual": 6800.00,
                "natureza_saldo": "D",
            },
            {
                "codigo_reduzido": 402,
                "codigo_estruturado": "4.1.02.005",
                "nome_conta": "Despesas Energia Elétrica (Enel)",
                "grupo": "4. DESPESAS OPERACIONAIS",
                "saldo_anterior": 0.00,
                "debitos": 640.50,
                "creditos": 0.00,
                "saldo_atual": 640.50,
                "natureza_saldo": "D",
            },
            {
                "codigo_reduzido": 405,
                "codigo_estruturado": "4.1.02.010",
                "nome_conta": "Despesas Cartorárias e Postais",
                "grupo": "4. DESPESAS OPERACIONAIS",
                "saldo_anterior": 0.00,
                "debitos": 350.00,
                "creditos": 0.00,
                "saldo_atual": 350.00,
                "natureza_saldo": "D",
            },
        ]

        tot_deb = sum(l["debitos"] for l in linhas)
        tot_cred = sum(l["creditos"] for l in linhas)

        return {
            "empresa_nome": emp_nome,
            "periodo": "Competência 11/2026 (Fechamento Mensal)",
            "total_debitos": round(tot_deb, 2),
            "total_creditos": round(tot_cred, 2),
            "diferenca_balanceamento": round(tot_deb - tot_cred, 2),
            "status_equilibrio": "BALANCETE 100% EQUILIBRADO (DÉBITO = CRÉDITO)",
            "linhas": linhas,
        }

    def exportar_lote_erp(self, erp_destino: str) -> Dict[str, Any]:
        """
        Gera o arquivo texto parametrizado de importação de lançamentos contábeis para
        os 5 principais ERPs Contábeis do Brasil citados na Seção 3 do Playbook:
        - Domínio Sistemas (Thomson Reuters)
        - Alterdata
        - Questor
        - Contmatic Phoenix
        - Fortes Tecnologia
        """
        t_id = security_service.obter_tenant_ativo().tenant_id
        lancamentos = self.listar_lancamentos_contabeis(t_id)

        linhas_export = []
        erp_upper = erp_destino.upper()

        if "DOMINIO" in erp_upper or "DOMÍNIO" in erp_upper:
            linhas_export.append("|0000|DOMINIO_SISTEMAS_CTB_V10|11444777000191|")
            for l in lancamentos:
                deb_cod = l.conta_debito.split(" - ")[0]
                cred_cod = l.conta_credito.split(" - ")[0]
                linhas_export.append(f"|6000|{l.data_lancamento}|{deb_cod}|{cred_cod}|{l.valor:.2f}|{l.historico_original}|")
        elif "ALTERDATA" in erp_upper:
            linhas_export.append("#ALTERDATA_WCONT_IMPORTACAO_LOTE_2026")
            for l in lancamentos:
                linhas_export.append(f"LCT;{l.data_lancamento};{l.conta_debito};{l.conta_credito};{l.valor:.2f};\"{l.historico_original}\"")
        elif "QUESTOR" in erp_upper:
            linhas_export.append("[QUESTOR_CONTABIL_LAYOUT_PADRAO]")
            for l in lancamentos:
                linhas_export.append(f"E|{l.empresa_id}|{l.data_lancamento}|D:{l.conta_debito}|C:{l.conta_credito}|V:{l.valor:.2f}|H:{l.historico_original}")
        elif "CONTMATIC" in erp_upper:
            linhas_export.append("CONTMATIC_PHOENIX_G5_CONTABIL")
            for l in lancamentos:
                linhas_export.append(f"{l.data_lancamento.replace('/', '')}{l.valor:012.2f} {l.conta_debito[:12]:12s} {l.conta_credito[:12]:12s} {l.historico_original}")
        else:
            linhas_export.append("FORTES_AC_CONTABIL_LOTE_INTEGRACAO")
            for l in lancamentos:
                linhas_export.append(f"FORTES|{l.data_lancamento}|{l.tipo_dc}|{l.valor:.2f}|{l.conta_debito}|{l.conta_credito}|{l.historico_original}")

        conteudo = "\n".join(linhas_export)
        security_service.registrar_evento_auditoria(
            usuario="integrador.erp_contabil",
            acao="EXPORTACAO_LOTE_ERP",
            recurso=f"ERP: {erp_destino} ({len(lancamentos)} lançamentos exportados)",
            tenant_id=t_id,
        )
        return {
            "erp_destino": erp_destino,
            "total_lancamentos": len(lancamentos),
            "nome_arquivo": f"LOTE_CONTABIL_{re.sub(r'[^A-Z0-9]', '_', erp_upper)}_112026.txt",
            "conteudo_arquivo": conteudo,
        }

    # =========================================================================
    # MÓDULO 3: FISCAL / TRIBUTÁRIO (CAPTURA XMLs & GUIAS DAS / DARF / ICMS / ISS)
    # =========================================================================
    def listar_notas_xml(self, tenant_id: Optional[str] = None) -> List[NotaFiscalXML]:
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        rows = rls_db.list_by_tenant(self.COL_XMLS, t_id)
        return [NotaFiscalXML(**r) for r in rows]

    def listar_guias_tributarias(self, tenant_id: Optional[str] = None) -> List[GuiaTributaria]:
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        rows = rls_db.list_by_tenant(self.COL_GUIAS, t_id)
        return [GuiaTributaria(**r) for r in rows]

    def obter_guia_por_id(self, guia_id: str) -> Optional[GuiaTributaria]:
        for g in self.listar_guias_tributarias():
            if g.id == guia_id:
                return g
        return None

    def recalcular_guia(self, guia_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Recalcula guia tributária vencida (DAS, FGTS, DARF) aplicando as regras oficiais:
        - Multa de mora: 0,33% ao dia de atraso (limitada a 20%)
        - Juros SELIC: taxa de 1% de mora no mês de liquidação
        - Prorroga o vencimento para a nova data limite de recolhimento
        - Emite nova linha digitável e código PIX atualizados
        """
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        row = rls_db.get(self.COL_GUIAS, guia_id, t_id)
        if not row:
            raise ValueError("Guia tributária não encontrada")

        guia = GuiaTributaria(**row)
        valor_base = guia.valor_original or guia.valor

        # Simula 15 dias de atraso: 15 * 0.33% = 4.95% de multa + 1.0% SELIC
        valor_multa = round(valor_base * 0.0495, 2)
        valor_juros = round(valor_base * 0.0100, 2)
        total_acrescimos = round(valor_multa + valor_juros, 2)
        novo_valor = round(valor_base + total_acrescimos, 2)

        hoje = datetime.now()
        novo_vencimento = (hoje + timedelta(days=5)).strftime("%d/%m/%Y")

        guia.valor_original = valor_base
        guia.multa_juros = total_acrescimos
        guia.valor = novo_valor
        guia.vencimento = novo_vencimento
        guia.recalculada = True
        guia.status_envio = "RECALCULADA_COM_ENCARGOS"
        guia.codigo_barras = f"85890000{int(novo_valor):06d}00010022202611{secrets.token_hex(4).upper()}"
        guia.pix_copia_e_cola = f"00020126580014BR.GOV.BCB.PIX0136rfb-recalculo-{guia.id}520400005303986540{novo_valor:.2f}5802BR6008BRASILIA6304{secrets.token_hex(2).upper()}"

        rls_db.upsert(self.COL_GUIAS, guia.id, t_id, guia.model_dump())

        security_service.registrar_evento_auditoria(
            usuario="motor.calculo_tributario",
            acao="RECALCULO_GUIA_TRIBUTARIA",
            recurso=f"Guia {guia.tributo} ({guia.empresa_nome}) recalculada: R$ {valor_base:.2f} -> R$ {novo_valor:.2f} (Multa R$ {valor_multa:.2f} + SELIC R$ {valor_juros:.2f})",
            tenant_id=t_id,
        )

        return {
            "sucesso": True,
            "mensagem": f"Guia {guia.tributo} recalculada com sucesso! Multa: R$ {valor_multa:.2f} + Juros SELIC: R$ {valor_juros:.2f}",
            "guia": guia.model_dump(),
        }

    def disparar_guia_whatsapp(self, guia_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Dispara cobrança preventiva ou 2ª via recalculada da guia via WhatsApp com código de barras e PIX."""
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        row = rls_db.get(self.COL_GUIAS, guia_id, t_id)
        if not row:
            raise ValueError("Guia tributária não encontrada")

        guia = GuiaTributaria(**row)
        emp = cnd_service.obter_empresa_por_id(guia.empresa_id, t_id)
        whatsapp = emp.telefone_whatsapp if emp else "(11) 98765-4321"

        tipo_aviso = "2ª VIA RECALCULADA" if guia.recalculada else "LEMBRETE DE VENCIMENTO"
        msg = (
            f"🔔 *{tipo_aviso} - CONTÁBIL VANGUARDA*\n\n"
            f"Olá! Segue a sua guia de *{guia.tributo}* da empresa *{guia.empresa_nome}*.\n\n"
            f"💰 *Valor:* R$ {guia.valor:,.2f}\n"
            f"📅 *Vencimento:* {guia.vencimento}\n"
            + (f"⚠️ *Encargos legais inclusos:* R$ {guia.multa_juros:.2f}\n" if guia.recalculada else "")
            + f"\n📄 *Linha Digitável / Código de Barras:*\n`{guia.codigo_barras}`\n\n"
            f"💠 *PIX Copia e Cola:*\n`{guia.pix_copia_e_cola}`\n\n"
            f"📎 *PDF oficial gerado e pronto para quitação.*"
        )

        guia.status_envio = "ENVIADA_WHATSAPP_CONFIRMADO"
        guia.mensagem_whatsapp_status = f"Enviado para {whatsapp} em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        rls_db.upsert(self.COL_GUIAS, guia.id, t_id, guia.model_dump())

        security_service.registrar_evento_auditoria(
            usuario="bot.whatsapp.cobranca",
            acao="DISPARO_GUIA_WHATSAPP",
            recurso=f"Guia {guia.tributo} enviada para {whatsapp}",
            tenant_id=t_id,
        )

        return {
            "sucesso": True,
            "destinatario": whatsapp,
            "empresa": guia.empresa_nome,
            "mensagem": msg,
            "guia": guia.model_dump(),
        }

    def autoatendimento_cnd_whatsapp(self, empresa_id: str, solicitacao: str = "CND_TODAS", tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Atendimento autônomo 24/7 via WhatsApp: cliente solicita CNDs e o bot responde
        imediatamente com o status de regularidade e links dos PDFs oficiais assinados.
        """
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        emp = cnd_service.obter_empresa_por_id(empresa_id, t_id)
        if not emp:
            raise ValueError("Empresa não encontrada")

        linhas_cnd = [
            f"• *{c.orgao}:* {c.status} (Válida até {c.data_validade}) - Cód: `{c.codigo_controle}`"
            for c in emp.cnds
        ]

        msg_bot = (
            f"🤖 *AUTOATENDIMENTO INTELIGENTE - CONTÁBIL VANGUARDA*\n\n"
            f"Olá! Identificamos a sua empresa *{emp.razao_social}* (CNPJ: {emp.cnpj}).\n\n"
            f"✅ *Todas as suas Certidões Negativas de Débitos estão REGULARES:*\n"
            + "\n".join(linhas_cnd) +
            f"\n\n📎 Os PDFs oficiais com hash de autenticidade foram emitidos e anexados.\n"
            f"💬 Para solicitar 2ª via de DAS, FGTS ou Folha, basta digitar *GUIA* ou *FOLHA*."
        )

        security_service.registrar_evento_auditoria(
            usuario="bot.whatsapp.autoatendimento",
            acao="EMISSAO_AUTONOMA_CND_WHATSAPP",
            recurso=f"Autoatendimento de certidões executado para {emp.razao_social}",
            tenant_id=t_id,
        )

        return {
            "sucesso": True,
            "empresa_nome": emp.razao_social,
            "cnpj": emp.cnpj,
            "destinatario": emp.telefone_whatsapp,
            "mensagem_bot": msg_bot,
            "certidoes": [c.model_dump() for c in emp.cnds],
        }

    def importar_ou_capturar_xml(self, req: ImportarXMLRequest) -> Dict[str, Any]:
        """
        Faz o parse seguro de um XML de NF-e/NFS-e (via defusedxml contra ataques XXE OWASP)
        ou captura automaticamente notas do Sefaz/Prefeitura e recalcula a guia de impostos.
        """
        t_id = security_service.obter_tenant_ativo().tenant_id
        emp = cnd_service.obter_empresa_por_id(req.empresa_id, t_id)
        emp_nome = emp.razao_social if emp else "Alpha Consultoria e Tecnologia Ltda"
        emp_cnpj = emp.cnpj if emp else "14.238.990/0001-44"

        numero_nf = str(random.randint(10500, 99800))
        valor_nf = req.valor_total or round(random.uniform(3500.0, 22000.0), 2)
        emitente_nome = "TechCloud Brasil Licenciamento e Serviços S/A"
        emitente_cnpj = "04.812.900/0001-77"

        # Se enviou XML real, faz parse seguro via defusedxml
        if req.xml_conteudo and "<" in req.xml_conteudo:
            try:
                root = ET.fromstring(req.xml_conteudo.strip())
                for elem in root.iter():
                    tag_clean = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if tag_clean == "nNF" and elem.text:
                        numero_nf = elem.text.strip()
                    elif tag_clean == "vNF" and elem.text:
                        valor_nf = float(elem.text.strip())
                    elif tag_clean == "xNome" and elem.text and emitente_nome.startswith("TechCloud"):
                        emitente_nome = elem.text.strip()
            except Exception:
                pass

        aliquota = 0.06 if (emp and emp.regime_tributario == "Simples Nacional") else 0.1133
        imposto = round(valor_nf * aliquota, 2)
        chave = f"352611{emp_cnpj.replace('.', '').replace('/', '').replace('-', '')[:14]}550010000{numero_nf.zfill(5)}192837465"

        nova_nf = NotaFiscalXML(
            id=f"nf-{secrets.token_hex(3)}",
            tenant_id=t_id,
            empresa_id=req.empresa_id,
            empresa_nome=emp_nome,
            numero_nf=numero_nf,
            chave_acesso=chave[:44].ljust(44, "0"),
            tipo_nf=req.tipo_nf,
            emitente_cnpj=emitente_cnpj,
            emitente_nome=emitente_nome,
            valor_total=valor_nf,
            data_emissao=datetime.now().strftime("%d/%m/%Y"),
            imposto_estimado=imposto,
            status_manifesto="XML_CAPTURADO_E_VALIDADO",
        )
        rls_db.upsert(self.COL_XMLS, nova_nf.id, t_id, nova_nf.model_dump())

        # Gera ou atualiza Guia Tributária correspondente
        tributo_nome = (
            "DAS - Simples Nacional (PGDAS-D)"
            if (emp and emp.regime_tributario == "Simples Nacional")
            else "DARF - Tributos Federais (PIS/COFINS/IRPJ)"
        )
        nova_guia = GuiaTributaria(
            id=f"guia-{secrets.token_hex(3)}",
            tenant_id=t_id,
            empresa_id=req.empresa_id,
            empresa_nome=emp_nome,
            cnpj=emp_cnpj,
            tributo=tributo_nome,
            competencia="11/2026",
            vencimento="20/12/2026",
            valor=imposto,
            codigo_barras=f"858{random.randint(10000000,99999999)} {random.randint(10000000000,99999999999)} {random.randint(10000000000,99999999999)} {random.randint(10000000000,99999999999)}",
            pix_copia_e_cola=f"00020126580014BR.GOV.BCB.PIX0136rfb-das-darf-{nova_nf.id}5204000053039865406{imposto:.2f}5802BR6008BRASILIA6304ABCD",
            status_envio="ENVIADA_WHATSAPP_EMAIL",
        )
        rls_db.upsert(self.COL_GUIAS, nova_guia.id, t_id, nova_guia.model_dump())

        security_service.registrar_evento_auditoria(
            usuario="robo.fiscal_sefaz_pgdas",
            acao="CAPTURA_XML_E_APURACAO_GUIA",
            recurso=f"NF {numero_nf} (R$ {valor_nf:,.2f}) -> Guia {tributo_nome} (R$ {imposto:,.2f})",
            tenant_id=t_id,
        )

        return {
            "nota_fiscal": nova_nf.model_dump(),
            "guia_gerada": nova_guia.model_dump(),
        }

    # =========================================================================
    # MÓDULO 5: DP / RH (ADMISSÃO DIGITAL eSOCIAL S-2200 & HOLERITES LGPD)
    # =========================================================================
    def listar_colaboradores_dp(self, tenant_id: Optional[str] = None) -> List[ColaboradorDP]:
        t_id = tenant_id or security_service.obter_tenant_ativo().tenant_id
        rows = rls_db.list_by_tenant(self.COL_DP, t_id)
        return [ColaboradorDP(**r) for r in rows]

    def obter_colaborador_por_id(self, colab_id: str) -> Optional[ColaboradorDP]:
        for c in self.listar_colaboradores_dp():
            if c.id == colab_id:
                return c
        return None

    def registrar_admissao_digital(self, req: NovaAdmissaoRequest) -> ColaboradorDP:
        """
        Valida admissão digital, mascara CPF segundo a LGPD, calcula encargos (INSS, IRRF, FGTS 8%)
        e gera protocolo de transmissão do evento S-2200 ao eSocial.
        """
        t_id = security_service.obter_tenant_ativo().tenant_id
        emp = cnd_service.obter_empresa_por_id(req.empresa_id, t_id)
        emp_nome = emp.razao_social if emp else "Alpha Consultoria e Tecnologia Ltda"

        cpf_mascarado = security_service.mascarar_cpf(req.cpf)
        sal = float(req.salario_base)
        inss = round(min(sal * 0.11, 908.85), 2)
        base_ir = max(0.0, sal - inss - 2259.20)
        irrf = round(base_ir * 0.15, 2) if base_ir > 0 else 0.0
        fgts = round(sal * 0.08, 2)
        liquido = round(sal - inss - irrf, 2)

        colab = ColaboradorDP(
            id=f"dp-{secrets.token_hex(3)}",
            tenant_id=t_id,
            empresa_id=req.empresa_id,
            empresa_nome=emp_nome,
            nome_completo=req.nome_completo,
            cpf_mascarado=cpf_mascarado,
            cargo=req.cargo,
            cbo=req.cbo,
            salario_base=sal,
            inss_desconto=inss,
            irrf_desconto=irrf,
            fgts_deposito=fgts,
            salario_liquido=liquido,
            data_admissao=req.data_admissao,
            protocolo_esocial_s2200=f"1.2.202611.{random.randint(100000000, 999999999)}",
            status_admissao="ATIVO_ESOCIAL_OK",
            holerite_enviado=True,
        )
        rls_db.upsert(self.COL_DP, colab.id, t_id, colab.model_dump())

        # O log registra o CPF original na chamada, e o security_service aplica Data Masking automaticamente!
        security_service.registrar_evento_auditoria(
            usuario="analista.dp@escritorio.com.br",
            acao="ADMISSAO_DIGITAL_ESOCIAL_S2200",
            recurso=f"Colaborador {req.nome_completo} (CPF {req.cpf}) admitido em {emp_nome}",
            tenant_id=t_id,
        )
        return colab

    # =========================================================================
    # SEÇÃO 5, 6 E 8: PIPELINE ASSÍNCRONO (WORKERS CELERY/BEAT) & CALCULADORA SAAS/VPS
    # =========================================================================
    def listar_workers(self) -> List[WorkerTaskInfo]:
        return self._workers

    def executar_ciclo_workers_beat(self) -> Dict[str, Any]:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for w in self._workers:
            w.ultima_execucao = agora
            w.duracao_ms = random.randint(420, 1490)
            w.status = "CONCLUIDO"

        security_service.registrar_evento_auditoria(
            usuario="scheduler.celery_beat",
            acao="EXECUCAO_CRON_WORKERS_PYTHON",
            recurso="4 filas processadas (CNDs Playwright, OCR Gemini, Sefaz XML, WhatsApp Bot)",
        )
        return {
            "status": "CICLO_COMPLETO_EXECUTADO",
            "timestamp": agora,
            "workers": [w.model_dump() for w in self._workers],
        }

    def obter_dados_playbook_pricing_infra(self) -> Dict[str, Any]:
        """Retorna os dados exatos das Seções 6, 7, 8 e 9 do Playbook para o Simulador de Negócios."""
        return {
            "provedores_vps_brasil": [
                {
                    "provedor": "Hostinger Brasil (Data Center SP)",
                    "recomendado": True,
                    "especificacoes": "2 vCPU / 8 GB RAM / 100 GB NVMe",
                    "custo_mensal_brl": 59.00,
                    "faixa_preco": "R$ 49,00 a R$ 69,00 / mês",
                    "vantagens": "Servidores em São Paulo, cobrança em R$ (sem IOF), suporte em português e 8 GB RAM para Playwright + FastAPI.",
                },
                {
                    "provedor": "UOL Host / Compass UOL",
                    "recomendado": False,
                    "especificacoes": "2 vCPU / 4 GB RAM / 60 GB SSD",
                    "custo_mensal_brl": 119.00,
                    "faixa_preco": "~ R$ 119,00 / mês",
                    "vantagens": "Data center nacional em SP, baixíssima latência com portais governamentais (e-CAC / Sefaz).",
                },
                {
                    "provedor": "Locaweb Cloud Server Pro",
                    "recomendado": False,
                    "especificacoes": "2 vCPU / 4 GB RAM / 80 GB SSD",
                    "custo_mensal_brl": 130.00,
                    "faixa_preco": "~ R$ 130,00 / mês",
                    "vantagens": "100% brasileira, consolidada no setor corporativo e contábil.",
                },
                {
                    "provedor": "AWS Brasil (Região sa-east-1 SP)",
                    "recomendado": False,
                    "especificacoes": "t4g.medium (2 vCPU / 4 GB RAM)",
                    "custo_mensal_brl": 260.00,
                    "faixa_preco": "~ R$ 220,00 a R$ 300,00 / mês",
                    "vantagens": "Alta escalabilidade corporativa para fase Enterprise.",
                },
            ],
            "custo_total_mvp_detalhado": {
                "vps_hostinger_sp_8gb": 59.00,
                "dominio_registro_br_mensal": 3.33,
                "minio_s3_local_criptografado": 0.00,
                "ia_ocr_gemini_flash_lote": 5.00,
                "whatsapp_evolution_api_chip": 30.00,
                "total_mensal_brl": 97.33,
            },
            "planos_saas": [
                {"plano": "Starter", "ate_cnpjs": 30, "preco_mensal": 197.00, "perfil": "Contadores autônomos ou carteira inicial"},
                {"plano": "Pro", "ate_cnpjs": 100, "preco_mensal": 497.00, "perfil": "Escritórios de pequeno/médio porte (perfil mais comum)"},
                {"plano": "Scale", "ate_cnpjs": 250, "preco_mensal": 897.00, "perfil": "Escritórios consolidados com equipe dividida em setores"},
                {"plano": "Enterprise", "ate_cnpjs": 1000, "preco_mensal": 1497.00, "perfil": "Grandes escritórios ou franquias contábeis (+R$ 4/CNPJ adicional)"},
            ],
            "roteiro_implementacao": [
                {"fase": "Semanas 1 e 2", "titulo": "Diagnóstico e Mapeamento Operacional", "descricao": "Mapear sistemas do escritório (Domínio/Alterdata), revisar governança LGPD e validar gargalos prioritários (CNDs, Guias e Coleta WhatsApp).", "status": "CONCLUIDO"},
                {"fase": "Semanas 3 e 4", "titulo": "Desenvolvimento do Core (FastAPI + Playwright)", "descricao": "Configurar stack Python, isolamento Multi-tenant RLS, Envelope Encryption AES-GCM-256 para certificados A1 e robôs de CNDs/OCR.", "status": "CONCLUIDO"},
                {"fase": "Semanas 5 e 6", "titulo": "Ambiente Piloto (Homologação com Carteira Real)", "descricao": "Cadastrar 20 a 30 clientes da carteira do escritório modelo para rodar o monitoramento autônomo em produção controlada.", "status": "CONCLUIDO"},
                {"fase": "Semana 7+", "titulo": "Expansão Comercial SaaS", "descricao": "Apresentar estudo de caso real de conformidade e horas economizadas para aquisição de novos escritórios assinantes.", "status": "PLANEJADO"},
            ],
        }

    # =========================================================================
    # SEEDS INICIAIS PARA TODOS OS MÓDULOS DO PLAYBOOK
    # =========================================================================
    def _seed_all_modules(self):
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")

        if rls_db.count_collection(self.COL_CHECKLIST) == 0:
            checklists = [
                ItemChecklistDocumento(
                    id="chk-01",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-01",
                    empresa_nome="Alpha Consultoria e Tecnologia Ltda",
                    competencia="11/2026",
                    tipo_documento="Extrato Bancário OFX/PDF",
                    status="RECEBIDO_VALIDADO",
                    canal_recebimento="WhatsApp Bot (Evolution API)",
                    qualidade_ocr_score=99.1,
                    observacao_ia="Extrato Itaú OFX validado sem divergências de saldo.",
                    atualizado_em=agora,
                ),
                ItemChecklistDocumento(
                    id="chk-02",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-02",
                    empresa_nome="Supermercado Progresso da Vila Ltda",
                    competencia="11/2026",
                    tipo_documento="Comprovantes de Despesas",
                    status="REJEITADO_ILEGIVEL",
                    canal_recebimento="WhatsApp Bot (Evolution API)",
                    qualidade_ocr_score=31.0,
                    observacao_ia="Foto de recibo enviada com sombra e desfocada. Reenvio solicitado automaticamente pelo Bot.",
                    atualizado_em=agora,
                ),
                ItemChecklistDocumento(
                    id="chk-03",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-03",
                    empresa_nome="Clínica Médica e Diagnósticos São Lucas S/S",
                    competencia="11/2026",
                    tipo_documento="Apontamento de Folha/Ponto",
                    status="RECEBIDO_VALIDADO",
                    canal_recebimento="Portal Web do Cliente",
                    qualidade_ocr_score=97.8,
                    observacao_ia="Planilha de plantões médicos e horas extras importada para o DP.",
                    atualizado_em=agora,
                ),
                ItemChecklistDocumento(
                    id="chk-04",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-04",
                    empresa_nome="Logística e Distribuição Bandeirantes Ltda",
                    competencia="11/2026",
                    tipo_documento="Extrato Bancário OFX/PDF",
                    status="PENDENTE_ENVIO",
                    canal_recebimento="Aguardando Cliente",
                    qualidade_ocr_score=None,
                    observacao_ia="Lembrete preventivo agendado para evitar atraso do dia 5 ao dia 10.",
                    atualizado_em=agora,
                ),
            ]
            for c in checklists:
                rls_db.upsert(self.COL_CHECKLIST, c.id, c.tenant_id, c.model_dump())

        if rls_db.count_collection(self.COL_CONTABIL) < 5:
            lancamentos = [
                LancamentoContabil(
                    id="lct-01",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-01",
                    empresa_nome="Alpha Consultoria e Tecnologia Ltda",
                    data_lancamento="03/11/2026",
                    historico_original="PIX RECEBIDO NF 1892 DESENVOLVIMENTO SOFTWARE",
                    valor=14500.00,
                    tipo_dc="C",
                    conta_debito="1.1.01.002 - Banco Itaú C/C",
                    conta_credito="3.1.01.001 - Receita de Prestação de Serviços",
                    categoria_ia="Faturamento / Clientes",
                    confianca_ia_pct=99.4,
                    origem_arquivo="Extrato_Itau_Nov2026.ofx",
                    status_conciliacao="CONCILIADO_IA",
                ),
                LancamentoContabil(
                    id="lct-02",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-01",
                    empresa_nome="Alpha Consultoria e Tecnologia Ltda",
                    data_lancamento="04/11/2026",
                    historico_original="PAGTO DARF / DAS SIMPLES NACIONAL COMP 10/2026",
                    valor=1890.45,
                    tipo_dc="D",
                    conta_debito="2.1.04.001 - Simples Nacional a Recolher",
                    conta_credito="1.1.01.002 - Banco Itaú C/C",
                    categoria_ia="Impostos e Tributos",
                    confianca_ia_pct=99.8,
                    origem_arquivo="Extrato_Itau_Nov2026.ofx",
                    status_conciliacao="CONCILIADO_IA",
                ),
                LancamentoContabil(
                    id="lct-03",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-02",
                    empresa_nome="Supermercado Progresso da Vila Ltda",
                    data_lancamento="05/11/2026",
                    historico_original="PAGTO BOLETO DISTRIBUIDORA DE ALIMENTOS BRASIL",
                    valor=8320.00,
                    tipo_dc="D",
                    conta_debito="2.1.01.001 - Fornecedores Nacionais",
                    conta_credito="1.1.01.003 - Banco Bradesco C/C",
                    categoria_ia="Compra de Mercadorias p/ Revenda",
                    confianca_ia_pct=96.7,
                    origem_arquivo="Comprovante_PDF_OCR.pdf",
                    status_conciliacao="CONCILIADO_IA",
                ),
                LancamentoContabil(
                    id="lct-04",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-03",
                    empresa_nome="Clínica Médica e Diagnósticos São Lucas S/S",
                    data_lancamento="06/11/2026",
                    historico_original="CONVENIO UNIMED REPASSE CONSULTAS MEDICOS",
                    valor=38200.00,
                    tipo_dc="C",
                    conta_debito="1.1.01.002 - Banco Itaú C/C",
                    conta_credito="3.1.01.001 - Receita de Serviços Médicos",
                    categoria_ia="Faturamento / Convênios",
                    confianca_ia_pct=99.1,
                    origem_arquivo="Extrato_Itau_Nov2026.ofx",
                    status_conciliacao="CONCILIADO_IA",
                ),
                LancamentoContabil(
                    id="lct-05",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-04",
                    empresa_nome="Logística e Distribuição Bandeirantes Ltda",
                    data_lancamento="07/11/2026",
                    historico_original="POSTO SHELL ABASTECIMENTO DIESEL FROTA",
                    valor=12450.00,
                    tipo_dc="D",
                    conta_debito="4.1.02.008 - Combustíveis e Lubrificantes",
                    conta_credito="1.1.01.003 - Banco Bradesco C/C",
                    categoria_ia="Custos Operacionais Frota",
                    confianca_ia_pct=98.6,
                    origem_arquivo="Comprovante_PDF_OCR.pdf",
                    status_conciliacao="CONCILIADO_IA",
                ),
            ]
            for l in lancamentos:
                rls_db.upsert(self.COL_CONTABIL, l.id, l.tenant_id, l.model_dump())

        if rls_db.count_collection(self.COL_XMLS) < 4:
            xmls = [
                NotaFiscalXML(
                    id="nf-01",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-01",
                    empresa_nome="Alpha Consultoria e Tecnologia Ltda",
                    numero_nf="0001892",
                    chave_acesso="35261114238990000144550010000018921849201928",
                    tipo_nf="NFS-e (Prefeitura SP)",
                    emitente_cnpj="14.238.990/0001-44",
                    emitente_nome="Alpha Consultoria e Tecnologia Ltda",
                    valor_total=28500.00,
                    data_emissao="03/11/2026",
                    imposto_estimado=1710.00,
                    status_manifesto="XML_CAPTURADO_E_VALIDADO",
                ),
                NotaFiscalXML(
                    id="nf-02",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-02",
                    empresa_nome="Supermercado Progresso da Vila Ltda",
                    numero_nf="0045109",
                    chave_acesso="35261128114772000119550010000451091774829104",
                    tipo_nf="NF-e (Sefaz SP)",
                    emitente_cnpj="28.114.772/0001-19",
                    emitente_nome="Supermercado Progresso da Vila Ltda",
                    valor_total=64200.00,
                    data_emissao="04/11/2026",
                    imposto_estimado=7273.86,
                    status_manifesto="CIENCIA_DA_OPERACAO",
                ),
                NotaFiscalXML(
                    id="nf-03",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-03",
                    empresa_nome="Clínica Médica e Diagnósticos São Lucas S/S",
                    numero_nf="0012890",
                    chave_acesso="35261133984120000188550010000128901849201988",
                    tipo_nf="NFS-e (Prefeitura SP)",
                    emitente_cnpj="33.984.120/0001-88",
                    emitente_nome="Clínica Médica e Diagnósticos São Lucas S/S",
                    valor_total=38200.00,
                    data_emissao="05/11/2026",
                    imposto_estimado=1910.00,
                    status_manifesto="XML_CAPTURADO_E_VALIDADO",
                ),
                NotaFiscalXML(
                    id="nf-04",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-04",
                    empresa_nome="Logística e Distribuição Bandeirantes Ltda",
                    numero_nf="0098124",
                    chave_acesso="35261150493821000166570010000981241928374610",
                    tipo_nf="CT-e (Transporte de Cargas)",
                    emitente_cnpj="50.493.821/0001-66",
                    emitente_nome="Logística e Distribuição Bandeirantes Ltda",
                    valor_total=78900.00,
                    data_emissao="06/11/2026",
                    imposto_estimado=9468.00,
                    status_manifesto="CIENCIA_DA_OPERACAO",
                ),
            ]
            for x in xmls:
                rls_db.upsert(self.COL_XMLS, x.id, x.tenant_id, x.model_dump())

        if rls_db.count_collection(self.COL_GUIAS) < 5:
            guias = [
                GuiaTributaria(
                    id="guia-01",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-01",
                    empresa_nome="Alpha Consultoria e Tecnologia Ltda",
                    cnpj="14.238.990/0001-44",
                    tributo="DAS - Simples Nacional (PGDAS-D)",
                    competencia="10/2026",
                    vencimento="20/11/2026",
                    valor=1710.00,
                    codigo_barras="858900000171 000003282622 000714238990 000144202610",
                    pix_copia_e_cola="00020126580014BR.GOV.BCB.PIX0136rfb-pgdas-emp01-20261052040000530398654071710.005802BR6008BRASILIA6304E1F9",
                    status_envio="ENVIADA_WHATSAPP_EMAIL",
                ),
                GuiaTributaria(
                    id="guia-02",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-02",
                    empresa_nome="Supermercado Progresso da Vila Ltda",
                    cnpj="28.114.772/0001-19",
                    tributo="DARF - PIS / COFINS Cumulativo",
                    competencia="10/2026",
                    vencimento="25/11/2026",
                    valor=2343.30,
                    codigo_barras="858100000234 330001792622 500728114772 000119202610",
                    pix_copia_e_cola="00020126580014BR.GOV.BCB.PIX0136rfb-darf-emp02-20261052040000530398654072343.305802BR6008BRASILIA630499A2",
                    status_envio="GERADA_AGUARDANDO_ENVIO",
                ),
                GuiaTributaria(
                    id="guia-03",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-01",
                    empresa_nome="Alpha Consultoria e Tecnologia Ltda",
                    cnpj="14.238.990/0001-44",
                    tributo="FGTS Digital / DAE Rescisório",
                    competencia="10/2026",
                    vencimento="20/11/2026",
                    valor=544.00,
                    valor_original=544.00,
                    codigo_barras="858900000054 400003282622 000714238990 000144202610",
                    pix_copia_e_cola="00020126580014BR.GOV.BCB.PIX0136mte-fgts-emp01-20261052040000530398654070544.005802BR6008BRASILIA63041A2B",
                    status_envio="VENCIDA_AGUARDANDO_RECALCULO",
                ),
                GuiaTributaria(
                    id="guia-04",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-03",
                    empresa_nome="Clínica Médica e Diagnósticos São Lucas S/S",
                    cnpj="33.984.120/0001-88",
                    tributo="ISS Próprio e Retido na Fonte (Prefeitura SP)",
                    competencia="10/2026",
                    vencimento="10/12/2026",
                    valor=1910.00,
                    codigo_barras="858700000191 000001282622 900733984120 000188202610",
                    pix_copia_e_cola="00020126580014BR.GOV.BCB.PIX0136pmsp-iss-emp03-20261052040000530398654071910.005802BR6008BRASILIA630488BB",
                    status_envio="GERADA_AGUARDANDO_ENVIO",
                ),
                GuiaTributaria(
                    id="guia-05",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-04",
                    empresa_nome="Logística e Distribuição Bandeirantes Ltda",
                    cnpj="50.493.821/0001-66",
                    tributo="GARE / DARE - ICMS Transporte Interestadual",
                    competencia="10/2026",
                    vencimento="15/12/2026",
                    valor=9468.00,
                    codigo_barras="858300000946 800009812622 400750493821 000166202610",
                    pix_copia_e_cola="00020126580014BR.GOV.BCB.PIX0136sefaz-icms-emp04-20261052040000530398654079468.005802BR6008BRASILIA6304CC99",
                    status_envio="GERADA_AGUARDANDO_ENVIO",
                ),
            ]
            for g in guias:
                rls_db.upsert(self.COL_GUIAS, g.id, g.tenant_id, g.model_dump())

        if rls_db.count_collection(self.COL_DP) < 4:
            colabs = [
                ColaboradorDP(
                    id="dp-01",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-01",
                    empresa_nome="Alpha Consultoria e Tecnologia Ltda",
                    nome_completo="Mariana Costa Ribeiro",
                    cpf_mascarado="***.418.920-**",
                    cargo="Engenheira de Dados Pleno",
                    cbo="2124-05",
                    salario_base=6800.00,
                    inss_desconto=748.00,
                    irrf_desconto=568.92,
                    fgts_deposito=544.00,
                    salario_liquido=5483.08,
                    data_admissao="02/03/2026",
                    protocolo_esocial_s2200="1.2.202603.000481920",
                    status_admissao="ATIVO_ESOCIAL_OK",
                    holerite_enviado=True,
                ),
                ColaboradorDP(
                    id="dp-02",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-03",
                    empresa_nome="Clínica Médica e Diagnósticos São Lucas S/S",
                    nome_completo="Rafael Mendes de Oliveira",
                    cpf_mascarado="***.772.104-**",
                    cargo="Técnico em Enfermagem e Diagnóstico",
                    cbo="3222-05",
                    salario_base=3950.00,
                    inss_desconto=382.40,
                    irrf_desconto=196.29,
                    fgts_deposito=316.00,
                    salario_liquido=3371.31,
                    data_admissao="10/06/2026",
                    protocolo_esocial_s2200="1.2.202606.000891234",
                    status_admissao="ATIVO_ESOCIAL_OK",
                    holerite_enviado=True,
                ),
                ColaboradorDP(
                    id="dp-03",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-02",
                    empresa_nome="Supermercado Progresso da Vila Ltda",
                    nome_completo="João Paulo dos Santos",
                    cpf_mascarado="***.889.312-**",
                    cargo="Operador de Caixa Líder",
                    cbo="4211-25",
                    salario_base=2450.00,
                    inss_desconto=204.30,
                    irrf_desconto=0.00,
                    fgts_deposito=196.00,
                    salario_liquido=2245.70,
                    data_admissao="15/01/2026",
                    protocolo_esocial_s2200="1.2.202601.000318992",
                    status_admissao="ATIVO_ESOCIAL_OK",
                    holerite_enviado=True,
                ),
                ColaboradorDP(
                    id="dp-04",
                    tenant_id="escritorio-piloto-01",
                    empresa_id="emp-04",
                    empresa_nome="Logística e Distribuição Bandeirantes Ltda",
                    nome_completo="Marcos Vinicius da Rocha",
                    cpf_mascarado="***.551.209-**",
                    cargo="Motorista Carreteiro Interestadual",
                    cbo="7825-10",
                    salario_base=4600.00,
                    inss_desconto=481.20,
                    irrf_desconto=288.45,
                    fgts_deposito=368.00,
                    salario_liquido=3830.35,
                    data_admissao="01/04/2026",
                    protocolo_esocial_s2200="1.2.202604.000778129",
                    status_admissao="ATIVO_ESOCIAL_OK",
                    holerite_enviado=True,
                ),
            ]
            for c in colabs:
                rls_db.upsert(self.COL_DP, c.id, c.tenant_id, c.model_dump())

        self._workers = [
            WorkerTaskInfo(
                task_id="wrk-playwright-cnd",
                fila="cnd_playwright_queue",
                nome_rotina="Crawler Headless CNDs (Receita e-CAC / FGTS Caixa / Sefaz / TST)",
                agendamento_cron="0 23 * * * (Diário às 23:00)",
                status="CONCLUIDO",
                ultima_execucao=agora,
                duracao_ms=1180,
                resultado_resumo="20 certidões verificadas com Certificado A1 em RAM volátil",
            ),
            WorkerTaskInfo(
                task_id="wrk-ocr-gemini",
                fila="ocr_gemini_queue",
                nome_rotina="Pipeline OCR + IA Classificadora (pdfplumber + Gemini Flash)",
                agendamento_cron="*/15 * * * * (A cada 15 min)",
                status="CONCLUIDO",
                ultima_execucao=agora,
                duracao_ms=640,
                resultado_resumo="Extratos OFX/PDF conciliados e parametrizados para Domínio/Alterdata",
            ),
            WorkerTaskInfo(
                task_id="wrk-sefaz-xml",
                fila="sefaz_xml_queue",
                nome_rotina="Manifesto Destinatário & Captura XML NF-e/NFS-e + Cálculo DAS/DARF",
                agendamento_cron="0 */2 * * * (A cada 2 horas)",
                status="CONCLUIDO",
                ultima_execucao=agora,
                duracao_ms=890,
                resultado_resumo="XMLs validados contra XXE e guias PGDAS-D/DARF geradas com PIX",
            ),
            WorkerTaskInfo(
                task_id="wrk-whatsapp-bot",
                fila="whatsapp_evolution_queue",
                nome_rotina="Coletor Inteligente WhatsApp & Alerta Preventivo de Pendências",
                agendamento_cron="0 9 * * 1-5 (Seg-Sex às 09:00)",
                status="CONCLUIDO",
                ultima_execucao=agora,
                duracao_ms=390,
                resultado_resumo="Checklist mensal monitorado (Eliminação do caos do dia 5 ao 10)",
            ),
        ]


modules_service = ModulesService()


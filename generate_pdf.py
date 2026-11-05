import os
import sys
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Cabeçalho (a partir da pág 2)
        if self._pageNumber > 1:
            self.drawString(18 * mm, 285 * mm, "AuditContábil AI — Playbook Estratégico & Técnico (Python + ISO 27001)")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(18 * mm, 282 * mm, 192 * mm, 282 * mm)

        # Rodapé (em todas as páginas)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
        self.drawString(18 * mm, 10 * mm, "Confidencial • Soberania de Dados Nacional (LGPD) • Arquitetura DevSecOps")
        page_str = f"Página {self._pageNumber} de {total_pages}"
        self.drawRightString(192 * mm, 10 * mm, page_str)
        self.restoreState()

def build_pdf(filename="d:/contabil/PLAYBOOK_SaaS_Contabil.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    # Cores
    c_primary = colors.HexColor("#0F172A")   # Slate 900
    c_accent = colors.HexColor("#059669")    # Emerald 600
    c_blue = colors.HexColor("#2563EB")      # Blue 600
    c_dark = colors.HexColor("#1E293B")      # Slate 800
    c_muted = colors.HexColor("#64748B")     # Slate 500
    c_border = colors.HexColor("#CBD5E1")    # Slate 300
    c_bg_light = colors.HexColor("#F8FAFC")  # Slate 50
    c_box_green = colors.HexColor("#ECFDF5") # Emerald 50

    # Estilos Customizados
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=c_primary,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_accent,
        spaceAfter=15
    )

    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_muted
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_blue,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=c_dark,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=12,
        bulletIndent=4,
        spaceAfter=4
    )

    box_text_style = ParagraphStyle(
        'BoxText',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#065F46")
    )

    th_style = ParagraphStyle(
        'THStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    td_style = ParagraphStyle(
        'TDStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=c_dark
    )

    story = []

    # CAPA / CABEÇALHO DO DOCUMENTO
    story.append(Paragraph("PLAYBOOK ESTRATÉGICO & TÉCNICO", title_style))
    story.append(Paragraph("Construção e Escala de SaaS para Escritórios Contábeis em Python", subtitle_style))

    badge_table = Table(
        [[
            Paragraph("<b>Stack:</b> Python 3.12 (FastAPI + Playwright)", meta_style),
            Paragraph("<b>Padrão:</b> ISO 27001 • OWASP Top 10", meta_style),
            Paragraph("<b>Legislação:</b> 100% LGPD (Data Center SP)", meta_style),
            Paragraph(f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y')}", meta_style)
        ]],
        colWidths=[45*mm, 45*mm, 45*mm, 39*mm]
    )
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg_light),
        ('BOX', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 10))

    # SEÇÃO 1: VISÃO GERAL
    story.append(Paragraph("1. Visão Geral e Proposta de Valor", h1_style))
    story.append(Paragraph(
        "Os escritórios contábeis brasileiros operam sob forte compressão de margens decorrente de tarefas braçais repetitivas: "
        "atraso no recebimento de documentos dos clientes, digitação manual de extratos, emissão de guias tributárias e consultas "
        "frequentes de Certidões Negativas de Débitos (CNDs).", body_style
    ))

    prop_box = Table(
        [[Paragraph("<b>Proposta de Valor:</b> Reduzir em até 70% o tempo operacional gasto por analistas contábeis na coleta, "
                    "conferência e conformidade fiscal através de robôs autônomos em Python, garantindo nível bancário de segurança da "
                    "informação (ISO 27001 / OWASP), dados 100% hospedados no Brasil e total aderência à LGPD.", box_text_style)]],
        colWidths=[174*mm]
    )
    prop_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_box_green),
        ('BOX', (0,0), (-1,-1), 0.8, c_accent),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(prop_box)
    story.append(Spacer(1, 10))

    # SEÇÃO 2: SEGURANÇA DA INFORMAÇÃO & LGPD
    story.append(Paragraph("2. Framework de Segurança da Informação (ISO 27001 / OWASP / LGPD)", h1_style))
    story.append(Paragraph(
        "Como os escritórios contábeis custodiam os dados mais críticos das empresas (faturamento, sócios, balanços e folhas de pagamento), "
        "o produto implementa <b>Security-by-Design</b> desde a concepção:", body_style
    ))

    story.append(Paragraph("• <b>Envelope Encryption para Certificados A1:</b> Cada arquivo .pfx é cifrado com uma Data Encryption Key (DEK) única em AES-GCM-256. A chave mestra (KEK) é mantida em cofre seguro. A descriptografia ocorre estritamente em memória volátil durante a execução do robô Playwright, com descarte imediato.", bullet_style))
    story.append(Paragraph("• <b>Isolamento Multi-tenant com PostgreSQL RLS:</b> Políticas nativas de <i>Row-Level Security</i> no banco garantem que nenhum escritório acesse registros de outro, mesmo em eventuais falhas na camada da aplicação.", bullet_style))
    story.append(Paragraph("• <b>Autenticação Zero Trust & MFA:</b> Segundo fator obrigatório via TOTP (RFC 6238) e senhas com hash resistente via <code>Argon2</code>.", bullet_style))
    story.append(Paragraph("• <b>Trilha de Auditoria Imutável (SIEM / WORM):</b> Logs estruturados em formato JSON registrando timestamp UTC, operador, ação, IP de origem e hash criptográfico SHA-256, com sanitização (Data Masking) de dados sensíveis.", bullet_style))
    story.append(Paragraph("• <b>DevSecOps & Defesa em Profundidade:</b> Containers Docker sem privilégios de root, análise estática de código com <code>Bandit</code> e <code>pip-audit</code>, firewall UFW, fail2ban e política de backup 3-2-1 com testes periódicos de restauração.", bullet_style))
    story.append(Paragraph("• <b>Soberania e LGPD:</b> Servidores hospedados no Brasil (São Paulo). O SaaS atua como <i>Operador</i> e o escritório como <i>Controlador</i> dos dados pessoais, sob contrato formal (DPA).", bullet_style))
    story.append(Spacer(1, 10))

    # SEÇÃO 3: MAPA DO ECOSSISTEMA EXTERNO
    story.append(Paragraph("3. Mapa do Ecossistema Externo Brasileiro", h1_style))
    story.append(Paragraph(
        "Mapeamento detalhado dos sistemas e portais oficiais com os quais o SaaS interage:", body_style
    ))

    eco_data = [
        [Paragraph("Categoria", th_style), Paragraph("Sistemas / Portais", th_style), Paragraph("Papel no Fluxo do SaaS", th_style)],
        [Paragraph("<b>Governo Federal</b>", td_style), Paragraph("Portal e-CAC (Receita/PGFN)<br/>Simples Nacional (PGDAS)<br/>FGTS Digital / Caixa CRF", td_style), Paragraph("Consulta de débitos fiscais, geração de DAS, certidões negativas conjuntas e regularidade do FGTS.", td_style)],
        [Paragraph("<b>Governo Estadual</b>", td_style), Paragraph("Sefaz Estaduais (ICMS)<br/>Sintegra / CCC", td_style), Paragraph("Consulta de CND Estadual e validação cadastral da Inscrição Estadual das empresas.", td_style)],
        [Paragraph("<b>Governo Municipal</b>", td_style), Paragraph("Prefeituras (NFS-e / ISS)<br/>Portal Nacional NFS-e", td_style), Paragraph("Emissão de CNDs municipais mobiliárias e captura de notas fiscais de serviço.", td_style)],
        [Paragraph("<b>Chaves de Acesso</b>", td_style), Paragraph("Certificado Digital A1 (.pfx)<br/>Procuração Eletrônica RFB", td_style), Paragraph("O certificado A1 do escritório + procuração RFB permite consultar centenas de clientes com 1 credencial.", td_style)],
        [Paragraph("<b>ERPs de Mercado</b>", td_style), Paragraph("Domínio (Thomson Reuters)<br/>Alterdata • Questor • Contmatic", td_style), Paragraph("Sistemas contábeis vigentes no escritório para os quais o SaaS exporta lançamentos e relatórios.", td_style)],
    ]
    t_eco = Table(eco_data, colWidths=[35*mm, 60*mm, 79*mm])
    t_eco.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_eco)
    story.append(Spacer(1, 10))

    # SEÇÃO 4: MATRIZ DE DORES E OPORTUNIDADES
    story.append(Paragraph("4. Matriz de Dores x Módulos do SaaS", h1_style))
    matriz_data = [
        [Paragraph("Área", th_style), Paragraph("Gargalo Operacional", th_style), Paragraph("Solução SaaS (Feature)", th_style), Paragraph("Impacto", th_style)],
        [Paragraph("<b>Atendimento</b>", td_style), Paragraph("Clientes esquecem documentos mensais", td_style), Paragraph("Coletor WhatsApp + Portal com checklist automático", td_style), Paragraph("Zero cobrança manual", td_style)],
        [Paragraph("<b>Contábil</b>", td_style), Paragraph("Conciliação manual de extratos/recibos", td_style), Paragraph("Pipeline OCR + Gemini Flash para classificação contábil", td_style), Paragraph("Fim da digitação de notas", td_style)],
        [Paragraph("<b>Fiscal</b>", td_style), Paragraph("Notas fiscais ausentes e risco de multas", td_style), Paragraph("Captura autônoma de XMLs na Sefaz e disparo de guias", td_style), Paragraph("Prazos cumpridos 100%", td_style)],
        [Paragraph("<b>Conformidade</b>", td_style), Paragraph("Certidões (CNDs) vencendo sem aviso", td_style), Paragraph("Robô Playwright com varredura semanal em órgãos", td_style), Paragraph("Monitoramento 24/7", td_style)],
        [Paragraph("<b>Dep. Pessoal</b>", td_style), Paragraph("Coleta manual de admissões e holerites", td_style), Paragraph("Admissão digital e distribuição segura de contracheques", td_style), Paragraph("Padronização total", td_style)]
    ]
    t_matriz = Table(matriz_data, colWidths=[28*mm, 48*mm, 60*mm, 38*mm])
    t_matriz.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_accent),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_matriz)
    story.append(Spacer(1, 10))

    # SEÇÃO 5: ARQUITETURA PYTHON & CUSTOS DE VPS NACIONAL
    story.append(Paragraph("5. Arquitetura Python & Custos de Infraestrutura Nacional", h1_style))
    story.append(Paragraph(
        "A tecnologia adota <b>Python</b> em todos os componentes vitais. Para total conformidade com a LGPD e soberania de dados, "
        "a hospedagem prioriza <b>data centers no Brasil (São Paulo)</b> com faturamento em reais (sem IOF nem flutuação cambial):", body_style
    ))

    custos_data = [
        [Paragraph("Componente", th_style), Paragraph("Tecnologia / Provedor", th_style), Paragraph("Especificações", th_style), Paragraph("Custo Estimado (BRL)", th_style)],
        [Paragraph("<b>VPS Principal (MVP)</b>", td_style), Paragraph("Hostinger Brasil (Data Center SP)", td_style), Paragraph("2 vCPU / 8 GB RAM / 100 GB NVMe", td_style), Paragraph("R$ 49,00 a R$ 59,00 / mês", td_style)],
        [Paragraph("<b>Domínio Próprio</b>", td_style), Paragraph("Registro.br (.com.br)", td_style), Paragraph("DNS Seguro com DNSSEC", td_style), Paragraph("R$ 40,00 / ano (~ R$ 3,33/mês)", td_style)],
        [Paragraph("<b>Armazenamento Arquivos</b>", td_style), Paragraph("MinIO Local Criptografado", td_style), Paragraph("Compatível com S3 na própria VPS", td_style), Paragraph("R$ 0,00 (incluso)", td_style)],
        [Paragraph("<b>Inteligência Artificial</b>", td_style), Paragraph("Google Gemini Flash API", td_style), Paragraph("OCR e extração de comprovantes", td_style), Paragraph("~ R$ 5,00 / mês (conforme uso)", td_style)],
        [Paragraph("<b>Canal WhatsApp</b>", td_style), Paragraph("Evolution API (Auto-hospedada)", td_style), Paragraph("Instância na própria VPS + Chip pré", td_style), Paragraph("~ R$ 30,00 / mês (chip)", td_style)],
        [Paragraph("<b>TOTAL MVP</b>", th_style), Paragraph("<b>Ambiente Completo no Brasil</b>", th_style), Paragraph("<b>Capacidade para até 50 empresas</b>", th_style), Paragraph("<b>~ R$ 95 a R$ 110 / mês</b>", th_style)]
    ]
    t_custos = Table(custos_data, colWidths=[38*mm, 52*mm, 48*mm, 36*mm])
    t_custos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BACKGROUND', (0,-1), (-1,-1), c_accent),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_custos)
    story.append(Spacer(1, 10))

    # SEÇÃO 6: MODELO DE NEGÓCIO & PRICING
    story.append(Paragraph("6. Modelo de Negócio e Precificação (Pricing B2B)", h1_style))
    story.append(Paragraph(
        "A cobrança é estruturada por <b>volume de empresas ativas atendidas (CNPJs monitorados)</b>, garantindo alto alinhamento "
        "com o crescimento do escritório e margens brutas superiores a 85%:", body_style
    ))

    pricing_data = [
        [Paragraph("Plano", th_style), Paragraph("Capacidade de Monitoramento", th_style), Paragraph("Preço Sugerido", th_style), Paragraph("Público-Alvo", th_style)],
        [Paragraph("<b>Starter</b>", td_style), Paragraph("Até 30 empresas atendidas", td_style), Paragraph("R$ 197,00 / mês", td_style), Paragraph("Contadores autônomos ou em início de carteira", td_style)],
        [Paragraph("<b>Professional</b>", td_style), Paragraph("Até 100 empresas atendidas", td_style), Paragraph("R$ 497,00 / mês", td_style), Paragraph("Escritórios contábeis de pequeno/médio porte", td_style)],
        [Paragraph("<b>Scale</b>", td_style), Paragraph("Até 250 empresas atendidas", td_style), Paragraph("R$ 897,00 / mês", td_style), Paragraph("Escritórios consolidados com múltiplos departamentos", td_style)],
        [Paragraph("<b>Enterprise</b>", td_style), Paragraph("Acima de 250 empresas (ilimitado)", td_style), Paragraph("Sob consulta (R$ 3 a R$ 5 / CNPJ)", td_style), Paragraph("Grandes escritórios ou redes contábeis", td_style)],
    ]
    t_pricing = Table(pricing_data, colWidths=[28*mm, 52*mm, 38*mm, 56*mm])
    t_pricing.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_blue),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_pricing)
    story.append(Spacer(1, 10))

    # SEÇÃO 7: ROTEIRO DE IMPLEMENTAÇÃO
    story.append(Paragraph("7. Roteiro de Implementação do Projeto Piloto", h1_style))
    story.append(Paragraph("• <b>Semana 1 e 2 (Validação Piloto):</b> Apresentação deste playbook e do MVP funcional; alinhamento dos ERPs utilizados e seleção dos clientes do grupo piloto.", bullet_style))
    story.append(Paragraph("• <b>Semana 3 e 4 (Refinamento Técnico):</b> Configuração do ambiente em VPS nacional e testes do robô Playwright para os órgãos prioritários (Receita Federal e FGTS).", bullet_style))
    story.append(Paragraph("• <b>Semana 5 e 6 (Operação em Beta Fechado):</b> Execução diária no escritório contábil para medir as horas reais economizadas e emissão de alertas preventivos.", bullet_style))
    story.append(Paragraph("• <b>Semana 7 em diante (Expansão Comercial):</b> Utilização dos resultados comprovados do piloto como estudo de caso para atrair novos escritórios contábeis.", bullet_style))
    story.append(Spacer(1, 10))

    # SEÇÃO 8: MANUAL OPERACIONAL E JORNADAS DE USO (GUIA DE OPERAÇÃO)
    story.append(Paragraph("8. Manual Operacional e Jornadas de Uso da Solução", h1_style))
    story.append(Paragraph(
        "Detalhamento formal das jornadas de uso dos usuários e governança de acesso multi-tenant na operação cotidiana do SaaS:", body_style
    ))

    story.append(Paragraph("8.1 Topologia de Acesso Multi-Tenant (PostgreSQL RLS & RBAC)", h2_style))
    story.append(Paragraph(
        "A solução adota uma hierarquia estruturada em três níveis com isolamento criptográfico e de dados: "
        "<b>1. Provedor SaaS</b> (gestão de infraestrutura e KMS) ➔ <b>2. Escritórios Contábeis Assinantes (Tenants)</b> "
        "(isolamento nativo via <code>PostgreSQL Row-Level Security</code> com injeção de <code>current_tenant_id</code>) ➔ "
        "<b>3. Empresas Clientes da Carteira</b> (acesso restrito aos dados do seu respectivo CNPJ).", body_style
    ))

    story.append(Paragraph("8.2 Jornada Operacional do Escritório Contábil (Backoffice)", h2_style))
    story.append(Paragraph("• <b>Conformidade Legal & CNDs 24/7:</b> Varredura autônoma via Playwright (Receita/PGFN, FGTS Caixa CRF, Sefaz Estadual, CNDT/TST e Prefeituras) com download de PDF oficial e hash SHA-256.", bullet_style))
    story.append(Paragraph("• <b>Cofre de Certificados A1 (.pfx):</b> Envelope Encryption (AES-GCM-256) com descriptografia volátil em RAM (`bytearray`) e sobrescrita imediata com zeros (0x00) pós-requisição (zero gravação em disco).", bullet_style))
    story.append(Paragraph("• <b>Módulo Contábil & ERPs:</b> Ingestão de extratos OFX/PDF, classificação automática por IA no Plano de Contas e exportação para Domínio Sistemas, Alterdata, Questor, Contmatic e Fortes.", bullet_style))
    story.append(Paragraph("• <b>Módulo Fiscal:</b> Captura de XMLs com proteção anti-XXE (`defusedxml`), apuração automática de PGDAS-D / DARF e emissão de guias com PIX Copia e Cola e código de barras.", bullet_style))
    story.append(Paragraph("• <b>Módulo DP / eSocial:</b> Validação de admissões digitais, cálculo de encargos (INSS/IRRF/FGTS), anonimização LGPD (Data Masking) e evento eSocial S-2200.", bullet_style))
    story.append(Paragraph("• <b>SIEM & Trilha de Auditoria:</b> Histórico imutável de eventos em formato WORM com encadeamento de blocos criptográficos SHA-256.", bullet_style))

    story.append(Paragraph("8.3 Jornada da Empresa Cliente (Experiência Omnichannel Híbrida)", h2_style))
    story.append(Paragraph("• <b>Canal WhatsApp Bot (Interação Passiva / Zero-Friction):</b> O cliente recebe guias com PIX no vencimento e responde com fotos/PDFs de extratos mensais, validados por IA contra fotos desfocadas.", bullet_style))
    story.append(Paragraph("• <b>Portal Web do Cliente (Autoatendimento 24/7):</b> Acesso seguro com perfil <code>CLIENTE_FINAL</code> restrito à própria empresa para download de CNDs, guias tributárias e holerites.", bullet_style))
    story.append(Spacer(1, 6))

    # TABELA DE AMBIENTES DE HOMOLOGAÇÃO
    story.append(Paragraph("8.4 Ambientes de Homologação e Demonstração Disponíveis", h2_style))
    ambientes_data = [
        [Paragraph("Ambiente", th_style), Paragraph("Provedor / Plataforma", th_style), Paragraph("Endereço / URL", th_style), Paragraph("Finalidade", th_style)],
        [Paragraph("<b>Produção Primária</b>", td_style), Paragraph("Vercel (Serverless Edge)", td_style), Paragraph("contabil-lac.vercel.app", td_style), Paragraph("Acesso web HTTPS de alta performance.", td_style)],
        [Paragraph("<b>Produção Secundária</b>", td_style), Paragraph("Render (Container Service)", td_style), Paragraph("contabil-vvxp.onrender.com", td_style), Paragraph("Instância contínua com workers.", td_style)],
        [Paragraph("<b>Documentação API</b>", td_style), Paragraph("Swagger / OpenAPI", td_style), Paragraph("contabil-lac.vercel.app/docs", td_style), Paragraph("Catálogo de endpoints RESTful.", td_style)],
        [Paragraph("<b>Repositório Git</b>", td_style), Paragraph("GitHub (Versionamento)", td_style), Paragraph("github.com/BDantas1983/contabil", td_style), Paragraph("Código-fonte auditável.", td_style)],
    ]
    t_amb = Table(ambientes_data, colWidths=[36*mm, 44*mm, 52*mm, 42*mm])
    t_amb.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_amb)
    story.append(Spacer(1, 10))

    # BUILD
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF gerado com sucesso em: {filename}")

if __name__ == "__main__":
    build_pdf()

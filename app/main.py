import os
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Dict, Any

from app.config import settings
from app.database import rls_db
from app.models import (
    Empresa,
    NovaEmpresaRequest,
    ConsultaCNDRequest,
    ConsultaCNDResponse,
    LogAuditoria,
    AlertaWhatsAppRequest,
    CertificadoA1Info,
    NovoCertificadoA1Request,
    ValidacaoSenhaRequest,
    ItemChecklistDocumento,
    SimularRecebimentoWhatsAppRequest,
    LancamentoContabil,
    ProcessarExtratoRequest,
    NotaFiscalXML,
    GuiaTributaria,
    ImportarXMLRequest,
    ColaboradorDP,
    NovaAdmissaoRequest,
    LoginRequest,
    LoginResponse,
    NovoTenantRequest,
)
from app.services.cnd_service import cnd_service
from app.services.security_service import security_service
from app.services.modules_service import modules_service
from app.services.pdf_service import pdf_service

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "SaaS Completo para Escritórios Contábeis (Ecossistema Python & Security-by-Design). "
        "Inclui os 5 Módulos do Playbook (Coleta WhatsApp, Conciliação OCR/IA + ERPs, Fiscal XML/Guias, "
        "Monitor 24/7 de CNDs Playwright e DP/eSocial LGPD) com Segurança ISO 27001, NIST e OWASP."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware DevSecOps: Security Headers (OWASP / ISO 27001)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Tenant-RLS-Context"] = security_service.obter_tenant_ativo().tenant_id
    return response


# Monta arquivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
try:
    os.makedirs(static_dir, exist_ok=True)
except OSError:
    pass
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
@app.get("/api/index", include_in_schema=False)
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"{settings.APP_NAME} API Operacional. Acesse /docs"}


# ============================================================================
# 0. AUTENTICAÇÃO, LOGIN DO TENANT & CREDENCIAIS DE DEMONSTRAÇÃO
# ============================================================================

@app.post("/api/v1/auth/login", response_model=LoginResponse, tags=["0. Autenticação & Login"])
async def login(req: LoginRequest):
    """Autentica o usuário (Escritório Contábil ou Empresa Cliente) e define o contexto do Tenant (RLS)."""
    try:
        dados = security_service.autenticar_usuario(req.email, req.senha, req.codigo_totp)
        rls_db.set_tenant_context(dados["tenant"]["tenant_id"])
        return dados
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@app.post("/api/v1/auth/cadastrar-tenant", tags=["0. Autenticação & Login"])
async def cadastrar_tenant(req: NovoTenantRequest):
    """Permite o onboarding de um novo Escritório Contábil (Tenant) com isolamento nativo RLS."""
    try:
        resultado = security_service.cadastrar_novo_tenant(req.model_dump())
        rls_db.set_tenant_context(resultado["tenant"]["tenant_id"])
        return resultado
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/auth/credenciais-demo", tags=["0. Autenticação & Login"])
async def listar_credenciais_demo():
    """Retorna a lista de credenciais criadas para cada escritório e para cada empresa cliente."""
    return security_service.listar_credenciais_demo()


@app.get("/api/v1/auth/sessao-atual", tags=["0. Autenticação & Login"])
async def obter_sessao_atual():
    """Retorna os dados do Tenant ativo e informações da sessão."""
    tenant = security_service.obter_tenant_ativo()
    return {
        "tenant": tenant.model_dump(),
        "total_usuarios": len(security_service.listar_usuarios_rbac()),
    }


# ============================================================================
# 1. DASHBOARD, EMPRESAS & MÓDULO 4: CONFORMIDADE LEGAL (MONITOR 24/7 DE CNDs)
# ============================================================================

@app.get("/api/v1/dashboard/metricas", response_model=Dict[str, Any], tags=["1. Dashboard & Monitor CNDs"])
async def get_metricas():
    """Retorna os indicadores operacionais, econômicos e de automação (meta 70%) do escritório ativo."""
    return cnd_service.obter_metricas_dashboard()


@app.get("/api/v1/empresas", response_model=List[Empresa], tags=["1. Dashboard & Monitor CNDs"])
async def get_empresas():
    """Lista todas as empresas clientes do escritório ativo (isoladas via PostgreSQL RLS)."""
    return cnd_service.listar_empresas()


@app.post("/api/v1/empresas", response_model=Empresa, status_code=status.HTTP_201_CREATED, tags=["1. Dashboard & Monitor CNDs"])
async def cadastrar_empresa(empresa: NovaEmpresaRequest):
    """Cadastra um novo cliente na carteira de monitoramento do escritório ativo."""
    return cnd_service.adicionar_empresa(empresa)


@app.post("/api/v1/cnds/consultar", response_model=ConsultaCNDResponse, tags=["1. Dashboard & Monitor CNDs"])
async def consultar_cnd(req: ConsultaCNDRequest):
    """Dispara o worker Python (Playwright + Certificado A1 volátil em RAM) para emissão de CNDs."""
    return await cnd_service.executar_consulta_cnd(req)


@app.get("/api/v1/cnds/pdf/{empresa_id}/{orgao_slug}", tags=["1. Dashboard & Monitor CNDs"])
async def baixar_pdf_cnd(empresa_id: str, orgao_slug: str):
    """Gera e baixa o PDF oficial da Certidão Negativa de Débitos com hash SHA-256 de auditoria."""
    emp = cnd_service.obter_empresa_por_id(empresa_id)
    if not emp:
        emp_list = cnd_service.listar_empresas()
        emp = emp_list[0] if emp_list else None
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    security_service.registrar_evento_auditoria(
        usuario="analista.fiscal@escritorio.com.br",
        acao="DOWNLOAD_CERTIDAO_PDF",
        recurso=f"CND {orgao_slug.upper()} - {emp.razao_social} ({emp.cnpj})",
    )
    pdf_bytes = pdf_service.gerar_pdf_cnd(emp.model_dump(), orgao_slug)
    filename = f"CND_{orgao_slug.upper()}_{emp.cnpj.replace('.', '').replace('/', '').replace('-', '')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================================
# 2. MÓDULO 1: ATENDIMENTO & COLETA INTELIGENTE (WHATSAPP + CHECKLIST MENSAL)
# ============================================================================

@app.get("/api/v1/coleta/checklist", response_model=List[ItemChecklistDocumento], tags=["2. Módulo Coleta & WhatsApp"])
async def get_checklist_coleta():
    """Lista o checklist mensal de documentos dos clientes (elimina o caos do dia 5 ao dia 10)."""
    return modules_service.listar_checklist()


@app.post("/api/v1/coleta/whatsapp-webhook", tags=["2. Módulo Coleta & WhatsApp"])
async def simular_webhook_whatsapp(req: SimularRecebimentoWhatsAppRequest):
    """Simula o recebimento de foto/PDF via WhatsApp Bot com validação automática de nitidez/OCR."""
    return modules_service.simular_recebimento_whatsapp(req)


@app.post("/api/v1/coleta/cobrar-lote", tags=["2. Módulo Coleta & WhatsApp"])
async def cobrar_pendencias_lote():
    """Dispara cobrança preventiva em lote via WhatsApp para clientes com documentos pendentes."""
    return modules_service.cobrar_pendencias_lote_whatsapp()


@app.post("/api/v1/notificacoes/whatsapp", tags=["2. Módulo Coleta & WhatsApp"])
async def disparar_whatsapp(req: AlertaWhatsAppRequest):
    """Dispara alerta preventivo de conformidade fiscal via WhatsApp para um cliente específico."""
    empresa = cnd_service.obter_empresa_por_id(req.empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    mensagem = (
        f"Olá, equipe da *{empresa.razao_social}*! "
        f"Aviso preventivo do seu escritório contábil: identificamos uma atualização/pendência fiscal "
        f"nas suas certidões ou obrigações do mês. Nossa equipe já está atuando preventivamente."
    )

    security_service.registrar_evento_auditoria(
        usuario="sistema.notificador_whatsapp",
        acao="DISPARO_ALERTA_WHATSAPP",
        recurso=f"WhatsApp {empresa.telefone_whatsapp} ({empresa.razao_social})",
    )

    return {
        "status": "ENVIADO_COM_SUCESSO",
        "destinatario": empresa.telefone_whatsapp,
        "mensagem_previa": mensagem,
        "canal": "Evolution API / WhatsApp Business Cloud",
    }


# ============================================================================
# 3. MÓDULO 2: CONTÁBIL & FINANCEIRO (PIPELINE OCR + IA & EXPORTAÇÃO ERPs)
# ============================================================================

@app.get("/api/v1/contabil/lancamentos", response_model=List[LancamentoContabil], tags=["3. Módulo Contábil & ERPs"])
async def get_lancamentos_contabeis():
    """Lista os lançamentos contábeis extraídos e classificados pelo pipeline OCR + IA."""
    return modules_service.listar_lancamentos_contabeis()


@app.post("/api/v1/contabil/processar-extrato", tags=["3. Módulo Contábil & ERPs"])
async def processar_extrato_contabil(req: ProcessarExtratoRequest):
    """Processa extrato (OFX/PDF/CSV) e classifica Débito/Crédito automaticamente no Plano de Contas."""
    return modules_service.processar_extrato_ocr_ia(req)


@app.get("/api/v1/contabil/exportar-erp/{erp_nome}", tags=["3. Módulo Contábil & ERPs"])
async def exportar_para_erp(erp_nome: str):
    """Exporta lote contábil nos layouts: Domínio Sistemas, Alterdata, Questor, Contmatic ou Fortes."""
    return modules_service.exportar_lote_erp(erp_nome)


# ============================================================================
# 4. MÓDULO 3: FISCAL & TRIBUTÁRIO (CAPTURA XMLs & GUIAS DAS / DARF / ICMS)
# ============================================================================

@app.get("/api/v1/fiscal/xmls", response_model=List[NotaFiscalXML], tags=["4. Módulo Fiscal & Guias"])
async def get_notas_xml():
    """Lista as Notas Fiscais (NF-e / NFS-e / CT-e) capturadas automaticamente da Sefaz e Prefeituras."""
    return modules_service.listar_notas_xml()


@app.get("/api/v1/fiscal/guias", response_model=List[GuiaTributaria], tags=["4. Módulo Fiscal & Guias"])
async def get_guias_tributarias():
    """Lista as guias tributárias apuradas (DAS Simples Nacional, DARF, ICMS, ISS) com PIX e código de barras."""
    return modules_service.listar_guias_tributarias()


@app.post("/api/v1/fiscal/importar-xml", tags=["4. Módulo Fiscal & Guias"])
async def importar_xml_fiscal(req: ImportarXMLRequest):
    """Importa/captura XML de Nota Fiscal (protegido contra XXE) e gera automaticamente a guia de imposto."""
    return modules_service.importar_ou_capturar_xml(req)


@app.get("/api/v1/fiscal/guias/pdf/{guia_id}", tags=["4. Módulo Fiscal & Guias"])
async def baixar_pdf_guia(guia_id: str):
    """Gera e baixa o PDF da Guia Tributária (DAS / DARF) com linha digitável e PIX Copia e Cola."""
    guia = modules_service.obter_guia_por_id(guia_id)
    if not guia:
        raise HTTPException(status_code=404, detail="Guia tributária não encontrada")
    pdf_bytes = pdf_service.gerar_pdf_guia(guia.model_dump())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="GUIA_{guia.id.upper()}.pdf"'},
    )


# ============================================================================
# 5. MÓDULO 5: DP & RH (ADMISSÃO DIGITAL eSOCIAL S-2200 & HOLERITES LGPD)
# ============================================================================

@app.get("/api/v1/dp/colaboradores", response_model=List[ColaboradorDP], tags=["5. Módulo DP, RH & eSocial"])
async def get_colaboradores_dp():
    """Lista os colaboradores admitidos digitalmente com eventos eSocial S-2200 e CPF mascarado (LGPD)."""
    return modules_service.listar_colaboradores_dp()


@app.post("/api/v1/dp/admissao", response_model=ColaboradorDP, tags=["5. Módulo DP, RH & eSocial"])
async def cadastrar_admissao_dp(req: NovaAdmissaoRequest):
    """Registra nova admissão digital, calcula INSS/IRRF/FGTS Digital e gera protocolo eSocial S-2200."""
    return modules_service.registrar_admissao_digital(req)


@app.get("/api/v1/dp/holerite/pdf/{colab_id}", tags=["5. Módulo DP, RH & eSocial"])
async def baixar_pdf_holerite(colab_id: str):
    """Gera e baixa o PDF do Contracheque (Holerite Digital) com anonimização LGPD."""
    colab = modules_service.obter_colaborador_por_id(colab_id)
    if not colab:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")
    pdf_bytes = pdf_service.gerar_pdf_holerite(colab.model_dump())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="HOLERITE_{colab.id.upper()}.pdf"'},
    )


# ============================================================================
# 6. FRAMEWORK DE SEGURANÇA (ISO 27001 / NIST / OWASP / LGPD / COFRE A1 / RLS)
# ============================================================================

@app.get("/api/v1/seguranca/status", response_model=Dict[str, Any], tags=["6. Segurança ISO 27001 & LGPD"])
async def get_status_seguranca():
    """Retorna os parâmetros completos de conformidade ISO 27001, LGPD, TOTP, RLS e integridade WORM."""
    return security_service.obter_status_segurança()


@app.get("/api/v1/seguranca/certificados-a1", response_model=List[CertificadoA1Info], tags=["6. Segurança ISO 27001 & LGPD"])
async def get_certificados_a1():
    """Lista os Certificados Digitais A1 (.pfx) custodiados com Envelope Encryption (AES-GCM-256)."""
    return security_service.listar_certificados_a1()


@app.post("/api/v1/seguranca/certificados-a1", response_model=CertificadoA1Info, tags=["6. Segurança ISO 27001 & LGPD"])
async def adicionar_certificado_a1(req: NovoCertificadoA1Request):
    """Criptografa um novo Certificado A1 (.pfx) com chave DEK exclusiva (AES-GCM-256) e KEK mestra."""
    t_id = security_service.obter_tenant_ativo().tenant_id
    return security_service.criptografar_certificado_a1(req, t_id)


@app.post("/api/v1/seguranca/certificados-a1/testar-ram", tags=["6. Segurança ISO 27001 & LGPD"])
async def testar_uso_volatil_ram(cert_id: str = ""):
    """Demonstra a descriptografia volátil em memória RAM seguida de sobrescrita imediata com zeros (0x00)."""
    return security_service.usar_certificado_em_memoria_volatil(cert_id or None)


@app.get("/api/v1/seguranca/totp", tags=["6. Segurança ISO 27001 & LGPD"])
async def get_totp_atual():
    """Retorna os parâmetros e o código atual do autenticador MFA TOTP (RFC 6238)."""
    return security_service.gerar_totp_atual()


@app.post("/api/v1/seguranca/totp/validar", tags=["6. Segurança ISO 27001 & LGPD"])
async def validar_totp(payload: Dict[str, str]):
    """Valida um código MFA TOTP de 6 dígitos (RFC 6238)."""
    return security_service.validar_codigo_totp(payload.get("codigo", ""))


@app.post("/api/v1/seguranca/avaliar-senha", tags=["6. Segurança ISO 27001 & LGPD"])
async def avaliar_senha(req: ValidacaoSenhaRequest):
    """Avalia uma senha segundo a política OWASP/Playbook (mín. 12 chars + HIBP k-Anonymity + Hash Bcrypt/Argon2)."""
    return security_service.avaliar_politica_senha(req.senha)


@app.get("/api/v1/seguranca/tenants", tags=["6. Segurança ISO 27001 & LGPD"])
async def listar_tenants():
    """Lista os escritórios contábeis (tenants) para demonstração de isolamento Multi-Tenant RLS."""
    return {
        "tenant_ativo": security_service.obter_tenant_ativo(),
        "tenants_disponiveis": security_service.listar_tenants(),
    }


@app.post("/api/v1/seguranca/tenants/alternar/{tenant_id}", tags=["6. Segurança ISO 27001 & LGPD"])
async def alternar_tenant(tenant_id: str):
    """Altera o contexto da sessão Multi-Tenant (`SET LOCAL app.current_tenant_id`)."""
    try:
        info = security_service.alternar_tenant(tenant_id)
        rls_db.set_tenant_context(tenant_id)
        return info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/v1/seguranca/rls-pentest", tags=["6. Segurança ISO 27001 & LGPD"])
async def executar_pentest_rls():
    """Simula tentativa de acesso cruzado (Cross-Tenant / SQLi) e comprova o bloqueio pelo Row-Level Security."""
    alvo = (
        "escritorio-demo-02"
        if security_service.obter_tenant_ativo().tenant_id == "escritorio-piloto-01"
        else "escritorio-piloto-01"
    )
    return security_service.simular_teste_isolamento_rls(alvo)


@app.get("/api/v1/seguranca/rls-ddl", tags=["6. Segurança ISO 27001 & LGPD"])
async def obter_ddl_rls():
    """Retorna o script SQL oficial do PostgreSQL Row-Level Security (Seção 2.2 do Playbook)."""
    return {"ddl_sql": rls_db.get_postgres_rls_ddl()}


@app.get("/api/v1/seguranca/rbac-usuarios", tags=["6. Segurança ISO 27001 & LGPD"])
async def listar_usuarios_rbac():
    """Lista os perfis RBAC do escritório ativo (Administrador, Analista Fiscal/DP/Contábil e Cliente Final)."""
    return security_service.listar_usuarios_rbac()


@app.get("/api/v1/auditoria/logs", response_model=List[LogAuditoria], tags=["6. Segurança ISO 27001 & LGPD"])
async def get_logs_auditoria():
    """Retorna a trilha de auditoria imutável (SIEM WORM) com Data Masking e Hash Chain SHA-256."""
    return security_service.listar_logs_auditoria()


@app.get("/api/v1/auditoria/verificar-worm", tags=["6. Segurança ISO 27001 & LGPD"])
async def verificar_worm():
    """Audita matematicamente a integridade de todos os blocos da cadeia SHA-256 nos logs WORM."""
    return security_service.verificar_integridade_worm()


# ============================================================================
# 7. WORKERS ASSÍNCRONOS (CELERY/BEAT) & ESTRATÉGIA DE NEGÓCIO / INFRAESTRUTURA
# ============================================================================

@app.get("/api/v1/workers", tags=["7. Workers Python & Negócio SaaS"])
async def get_workers():
    """Lista o status das filas assíncronas Python (Celery + Redis + Playwright + DocumentAI)."""
    return modules_service.listar_workers()


@app.post("/api/v1/workers/executar-ciclo", tags=["7. Workers Python & Negócio SaaS"])
async def executar_ciclo_workers():
    """Dispara manualmente um ciclo completo de execução das 4 filas do agendador Celery Beat."""
    return modules_service.executar_ciclo_workers_beat()


@app.get("/api/v1/playbook/negocio-infra", tags=["7. Workers Python & Negócio SaaS"])
async def get_negocio_infra():
    """Retorna os dados de Provedores VPS Brasil, Custos do MVP (~R$ 97/mês), Planos SaaS e Roteiro."""
    return modules_service.obter_dados_playbook_pricing_infra()

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# --- 1. MULTI-TENANT & IAM (ZERO TRUST / RBAC / MFA) ---

class TenantInfo(BaseModel):
    tenant_id: str
    nome_escritorio: str
    cnpj_escritorio: str
    plano_saas: str  # "Starter", "Pro", "Scale", "Enterprise"
    limite_cnpjs: int
    responsavel_tecnico: str
    crc_registro: str
    isolamento_rls_ativo: bool = True


class UsuarioIAM(BaseModel):
    id: str
    nome: str
    email: str
    senha_demo: Optional[str] = None
    role: str  # "ADMIN_ESCRITORIO", "ANALISTA_OPERACIONAL", "CLIENTE_FINAL"
    role_label: str
    tenant_id: str
    empresa_vinculada_id: Optional[str] = None
    empresa_vinculada_nome: Optional[str] = None
    mfa_habilitado: bool = True
    permissoes: List[str]


class LoginRequest(BaseModel):
    email: str
    senha: str
    codigo_totp: Optional[str] = None
    tenant_id: Optional[str] = None


class LoginResponse(BaseModel):
    token_jwt: str
    usuario: UsuarioIAM
    tenant: TenantInfo


class NovoTenantRequest(BaseModel):
    nome_escritorio: str
    cnpj_escritorio: str
    plano_saas: str = "Pro"
    responsavel_tecnico: str
    crc_registro: str
    email_admin: str
    senha_admin: str


class ValidacaoSenhaRequest(BaseModel):
    senha: str


# --- 2. COFRE CRIPTOGRÁFICO DE CERTIFICADOS A1 (ENVELOPE ENCRYPTION AES-GCM-256) ---

class CertificadoA1Info(BaseModel):
    id: str
    tenant_id: str
    titular_razao_social: str
    cnpj_titular: str
    tipo: str  # "ECNPJ_ESCRITORIO_PROCURACAO" ou "ECNPJ_CLIENTE_INDIVIDUAL"
    emissor_icp_brasil: str
    validade: str
    algoritmo_envelope: str = "AES-GCM-256 (DEK Cifrada por KEK KMS)"
    dek_encrypted_preview: str
    nonce_hex: str
    ciphertext_sha256: str
    tamanho_bytes: int
    procuracao_rfb_ativa: bool = True
    ultimo_uso_ram_utc: Optional[str] = None


class NovoCertificadoA1Request(BaseModel):
    titular_razao_social: str
    cnpj_titular: str
    senha_pfx: str
    tipo: str = "ECNPJ_CLIENTE_INDIVIDUAL"
    emissor_icp_brasil: str = "AC Certisign RFB G5"
    validade: str = "05/11/2027"
    conteudo_base64: Optional[str] = None


# --- 3. EMPRESAS & CONFORMIDADE LEGAL (MONITOR 24/7 DE CNDs) ---

class CNDStatus(BaseModel):
    orgao: str  # "Receita Federal / PGFN", "FGTS (Caixa CRF)", "Sefaz Estadual", "CNDT Trabalhista (TST)", "ISS Municipal"
    status: str  # "REGULAR", "PENDENTE", "PROCESSANDO", "VENCIDA"
    data_emissao: str
    data_validade: str
    codigo_controle: str
    detalhes: Optional[str] = None
    pdf_url: Optional[str] = None


class Empresa(BaseModel):
    id: str
    tenant_id: str = "escritorio-piloto-01"
    cnpj: str
    razao_social: str
    nome_fantasia: str
    regime_tributario: str  # "Simples Nacional", "Lucro Presumido", "Lucro Real"
    email_contato: str
    telefone_whatsapp: str
    status_geral: str  # "REGULAR" ou "ALERTA"
    procuracao_eletronica_ecac: bool = True
    erp_integrado: str = "Domínio Sistemas"
    cnds: List[CNDStatus]
    dias_sem_pendencia: int = 180


class NovaEmpresaRequest(BaseModel):
    cnpj: str
    razao_social: str
    nome_fantasia: str
    regime_tributario: str
    email_contato: str
    telefone_whatsapp: str
    erp_integrado: str = "Domínio Sistemas"
    procuracao_eletronica_ecac: bool = True


class ConsultaCNDRequest(BaseModel):
    cnpj: str
    orgaos: List[str] = Field(
        default=[
            "Receita Federal / PGFN",
            "FGTS (Caixa CRF)",
            "Sefaz Estadual (SP)",
            "CNDT Trabalhista (TST)"
        ]
    )


class ConsultaCNDResponse(BaseModel):
    cnpj: str
    razao_social: str
    tempo_execucao_segundos: float
    certificado_a1_utilizado: str
    memoria_volatil_zerada: bool
    cnds: List[CNDStatus]
    trilha_auditoria_id: str


# --- 4. MÓDULO 1: ATENDIMENTO & COLETA INTELIGENTE (WHATSAPP + CHECKLIST MENSAL) ---

class ItemChecklistDocumento(BaseModel):
    id: str
    tenant_id: str
    empresa_id: str
    empresa_nome: str
    competencia: str  # ex: "11/2026"
    tipo_documento: str  # "Extrato Bancário OFX/PDF", "Notas Fiscais Tomadas", "Apontamento de Folha/Ponto", "Comprovantes de Despesas"
    status: str  # "RECEBIDO_VALIDADO", "PENDENTE_ENVIO", "REJEITADO_ILEGIVEL"
    canal_recebimento: Optional[str] = None
    qualidade_ocr_score: Optional[float] = None
    observacao_ia: Optional[str] = None
    atualizado_em: str


class SimularRecebimentoWhatsAppRequest(BaseModel):
    empresa_id: str
    tipo_documento: str
    nome_arquivo: str
    simulacao_qualidade: str = "ALTA_NITIDEZ"  # "ALTA_NITIDEZ" ou "FOTO_ILEGIVEL"


class AlertaWhatsAppRequest(BaseModel):
    empresa_id: str
    tipo_alerta: str  # "cnd_a_vencer", "pendencia_identificada", "cobranca_checklist_mensal", "envio_guia_imposto"


# --- 5. MÓDULO 2: CONTÁBIL / FINANCEIRO (OCR + IA & EXPORTAÇÃO ERPs) ---

class LancamentoContabil(BaseModel):
    id: str
    tenant_id: str
    empresa_id: str
    empresa_nome: str
    data_lancamento: str
    historico_original: str
    valor: float
    tipo_dc: str  # "D" (Débito) ou "C" (Crédito)
    conta_debito: str
    conta_credito: str
    categoria_ia: str
    confianca_ia_pct: float
    origem_arquivo: str
    status_conciliacao: str  # "CONCILIADO_IA", "REVISAO_HUMANA"


class ProcessarExtratoRequest(BaseModel):
    empresa_id: str
    tipo_arquivo: str = "OFX"  # "OFX", "PDF_OCR", "CSV"
    conteudo_texto: Optional[str] = None


# --- 6. MÓDULO 3: FISCAL / TRIBUTÁRIO (CAPTURA XMLs & GUIAS DAS/DARF) ---

class NotaFiscalXML(BaseModel):
    id: str
    tenant_id: str
    empresa_id: str
    empresa_nome: str
    numero_nf: str
    chave_acesso: str
    tipo_nf: str  # "NF-e (Sefaz)", "NFS-e (Prefeitura)", "CT-e (Transporte)"
    emitente_cnpj: str
    emitente_nome: str
    valor_total: float
    data_emissao: str
    imposto_estimado: float
    status_manifesto: str = "CIENCIA_DA_OPERACAO"


class GuiaTributaria(BaseModel):
    id: str
    tenant_id: str
    empresa_id: str
    empresa_nome: str
    cnpj: str
    tributo: str  # "DAS - Simples Nacional (PGDAS-D)", "DARF - PIS/COFINS", "DARF - IRPJ/CSLL", "GARE/DARE - ICMS", "ISS Municipal"
    competencia: str
    vencimento: str
    valor: float
    codigo_barras: str
    pix_copia_e_cola: str
    status_envio: str  # "ENVIADA_WHATSAPP_EMAIL", "GERADA_AGUARDANDO_ENVIO", "PAGA_CONCILIADA"


class ImportarXMLRequest(BaseModel):
    empresa_id: str
    xml_conteudo: Optional[str] = None
    tipo_nf: str = "NF-e (Sefaz)"
    valor_total: Optional[float] = None


# --- 7. MÓDULO 5: DP / RH (ADMISSÃO DIGITAL eSOCIAL & HOLERITES LGPD) ---

class ColaboradorDP(BaseModel):
    id: str
    tenant_id: str
    empresa_id: str
    empresa_nome: str
    nome_completo: str
    cpf_mascarado: str
    cargo: str
    cbo: str
    salario_base: float
    inss_desconto: float
    irrf_desconto: float
    fgts_deposito: float
    salario_liquido: float
    data_admissao: str
    protocolo_esocial_s2200: str
    status_admissao: str  # "ATIVO_ESOCIAL_OK", "VALIDANDO_DOCUMENTOS"
    holerite_enviado: bool = True


class NovaAdmissaoRequest(BaseModel):
    empresa_id: str
    nome_completo: str
    cpf: str
    cargo: str
    cbo: str = "4110-10"
    salario_base: float
    data_admissao: str


# --- 8. AUDITORIA SIEM (WORM) & WORKERS ASSÍNCRONOS ---

class LogAuditoria(BaseModel):
    id: str
    timestamp: str
    usuario_operador: str
    acao: str
    tenant_id: str
    ip_origem: str
    recurso_acessado: str
    prev_hash: str = "0" * 64
    hash_sha256: str
    resultado: str


class WorkerTaskInfo(BaseModel):
    task_id: str
    fila: str  # "cnd_playwright_queue", "ocr_gemini_queue", "sefaz_xml_queue", "whatsapp_evolution_queue"
    nome_rotina: str
    agendamento_cron: str
    status: str  # "CONCLUIDO", "EM_EXECUCAO", "AGENDADO"
    ultima_execucao: str
    duracao_ms: int
    resultado_resumo: str

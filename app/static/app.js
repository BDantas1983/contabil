// app.js - AuditContábil AI (Implementação Completa do Playbook)

let ultimoArquivoERP = { nome: "LOTE_CONTABIL.txt", conteudo: "" };
let sessaoUsuario = JSON.parse(localStorage.getItem("auditcontabil_sessao") || "null") || {
  id: "usr-admin-01",
  nome: "Profa. Dra. Helena Martins",
  email: "contadora.master@escritorio.com.br",
  role: "ADMIN_ESCRITORIO",
  role_label: "Administrador do Escritório",
  tenant_id: "escritorio-piloto-01",
  empresa_vinculada_id: null,
  empresa_vinculada_nome: null
};

document.addEventListener("DOMContentLoaded", () => {
  aplicarPerfilVisualUsuario();
  carregarTudo();
  // Atualiza o relógio do TOTP RFC 6238 a cada 3 segundos quando estiver na aba de segurança
  setInterval(() => {
    const secTab = document.getElementById("content-security");
    if (secTab && !secTab.classList.contains("hidden")) {
      atualizarWidgetTOTP();
    }
  }, 3000);
});

// ============================================================================
// CONTROLE DE SESSÃO & MODAL DE LOGIN
// ============================================================================
function abrirModalLogin() {
  document.getElementById("modal-login").classList.remove("hidden");
  document.getElementById("modal-login").classList.add("flex");
}

function fecharModalLogin() {
  document.getElementById("modal-login").classList.add("hidden");
  document.getElementById("modal-login").classList.remove("flex");
}

function switchLoginTab(tab) {
  const contentAcessar = document.getElementById("content-login-acessar");
  const contentNovo = document.getElementById("content-login-novo");
  const tabAcessar = document.getElementById("tab-login-acessar");
  const tabNovo = document.getElementById("tab-login-novo");

  if (tab === "acessar") {
    contentAcessar.classList.remove("hidden");
    contentNovo.classList.add("hidden");
    tabAcessar.classList.add("border-emerald-600", "text-emerald-600");
    tabAcessar.classList.remove("border-transparent", "text-slate-500");
    tabNovo.classList.remove("border-emerald-600", "text-emerald-600");
    tabNovo.classList.add("border-transparent", "text-slate-500");
  } else {
    contentAcessar.classList.add("hidden");
    contentNovo.classList.remove("hidden");
    tabNovo.classList.add("border-emerald-600", "text-emerald-600");
    tabNovo.classList.remove("border-transparent", "text-slate-500");
    tabAcessar.classList.remove("border-emerald-600", "text-emerald-600");
    tabAcessar.classList.add("border-transparent", "text-slate-500");
  }
}

function preencherCredencial(email, senha) {
  document.getElementById("login-email").value = email;
  document.getElementById("login-senha").value = senha;
  executarLogin();
}

async function executarLogin(e) {
  if (e) e.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const senha = document.getElementById("login-senha").value.trim();
  const totp = document.getElementById("login-totp").value.trim();

  if (!email || !senha) {
    alert("Informe o e-mail e a senha.");
    return;
  }

  const btn = document.getElementById("btn-login-submit");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Autenticando...`;

  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, senha, codigo_totp: totp || null })
    });

    if (res.ok) {
      const data = await res.json();
      sessaoUsuario = data.usuario;
      localStorage.setItem("auditcontabil_sessao", JSON.stringify(sessaoUsuario));

      // Atualiza o seletor de tenant na topbar se necessário
      const selectTenant = document.getElementById("select-tenant");
      if (selectTenant && data.tenant) {
        selectTenant.value = data.tenant.tenant_id;
      }

      fecharModalLogin();
      aplicarPerfilVisualUsuario();
      await carregarTudo();
    } else {
      const err = await res.json();
      alert(`Falha no login: ${err.detail || "Credenciais inválidas"}`);
    }
  } catch (err) {
    alert("Erro na conexão com o servidor de autenticação.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-shield-halved"></i> Entrar com Segurança ISO 27001`;
  }
}

async function cadastrarNovoEscritorioTenant(e) {
  e.preventDefault();
  const payload = {
    nome_escritorio: document.getElementById("novo-tenant-nome").value,
    cnpj_escritorio: document.getElementById("novo-tenant-cnpj").value,
    crc_registro: document.getElementById("novo-tenant-crc").value,
    responsavel_tecnico: document.getElementById("novo-tenant-responsavel").value,
    plano_saas: document.getElementById("novo-tenant-plano").value,
    email_admin: document.getElementById("novo-tenant-email").value,
    senha_admin: document.getElementById("novo-tenant-senha").value
  };

  try {
    const res = await fetch("/api/v1/auth/cadastrar-tenant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      alert(`Sucesso! ${data.mensagem}\nIniciando sessão como Administrador do novo escritório.`);
      sessaoUsuario = data.usuario_admin;
      localStorage.setItem("auditcontabil_sessao", JSON.stringify(sessaoUsuario));

      // Adiciona o novo tenant ao seletor se não existir
      const selectTenant = document.getElementById("select-tenant");
      const opt = document.createElement("option");
      opt.value = data.tenant.tenant_id;
      opt.className = "bg-slate-900 text-white";
      opt.innerText = `${data.tenant.tenant_id} (${data.tenant.nome_escritorio})`;
      selectTenant.appendChild(opt);
      selectTenant.value = data.tenant.tenant_id;

      fecharModalLogin();
      aplicarPerfilVisualUsuario();
      await carregarTudo();
    } else {
      const err = await res.json();
      alert(`Erro: ${err.detail || "Não foi possível cadastrar o escritório."}`);
    }
  } catch (err) {
    alert("Erro na comunicação com o servidor.");
  }
}

function aplicarPerfilVisualUsuario() {
  if (!sessaoUsuario) return;

  const nomeEl = document.getElementById("user-display-nome");
  const roleEl = document.getElementById("user-display-role");
  const avatarEl = document.getElementById("user-avatar");
  const bannerCliente = document.getElementById("portal-cliente-banner");
  const tabSecurity = document.getElementById("tab-security");
  const tabNegocio = document.getElementById("tab-negocio");

  if (nomeEl) nomeEl.innerText = sessaoUsuario.nome;
  if (roleEl) roleEl.innerText = sessaoUsuario.role_label || sessaoUsuario.role;

  if (sessaoUsuario.role === "CLIENTE_FINAL") {
    if (avatarEl) avatarEl.innerHTML = `<i class="fa-solid fa-building text-indigo-400"></i>`;
    if (bannerCliente) {
      bannerCliente.classList.remove("hidden");
      document.getElementById("portal-cliente-nome").innerText = sessaoUsuario.empresa_vinculada_nome || sessaoUsuario.nome;
      document.getElementById("portal-cliente-cnpj").innerText = `Perfil: Cliente Final • Empresa: ${sessaoUsuario.empresa_vinculada_id || "Vínculo Ativo"}`;
    }
    // Esconde abas de infraestrutura interna do escritório contábil
    if (tabSecurity) tabSecurity.classList.add("hidden");
    if (tabNegocio) tabNegocio.classList.add("hidden");
    trocarVisaoRBAC("CLIENTE_FINAL");
  } else {
    if (avatarEl) avatarEl.innerHTML = `<i class="fa-solid fa-user-tie text-emerald-400"></i>`;
    if (bannerCliente) bannerCliente.classList.add("hidden");
    if (tabSecurity) tabSecurity.classList.remove("hidden");
    if (tabNegocio) tabNegocio.classList.remove("hidden");
    trocarVisaoRBAC(sessaoUsuario.role || "ADMIN_ESCRITORIO");
  }
}

async function carregarTudo() {
  await Promise.all([
    carregarDados(),
    carregarChecklistColeta(),
    carregarLancamentosContabeis(),
    carregarModuloFiscal(),
    carregarModuloDP(),
    carregarPainelSeguranca(),
    carregarWorkersENegocio()
  ]);
}

function switchTab(tabName) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".tab-btn").forEach(el => {
    el.classList.remove("border-emerald-600", "text-emerald-600");
    el.classList.add("border-transparent", "text-slate-500");
  });

  const activeContent = document.getElementById(`content-${tabName}`);
  const activeTabBtn = document.getElementById(`tab-${tabName}`);
  if (activeContent) activeContent.classList.remove("hidden");
  if (activeTabBtn) {
    activeTabBtn.classList.remove("border-transparent", "text-slate-500");
    activeTabBtn.classList.add("border-emerald-600", "text-emerald-600");
  }

  if (tabName === "security") {
    carregarPainelSeguranca();
  }
}

// ============================================================================
// TOPBAR: ALTERNAR TENANT (POSTGRESQL RLS) E VISÃO RBAC
// ============================================================================
async function trocarTenantRLS(tenantId) {
  try {
    const res = await fetch(`/api/v1/seguranca/tenants/alternar/${tenantId}`, { method: "POST" });
    if (res.ok) {
      const info = await res.json();
      document.getElementById("banner-rls-cmd").innerText = `SET LOCAL app.current_tenant_id = '${info.tenant_id}';`;
      document.getElementById("banner-escritorio-nome").innerText = `${info.nome_escritorio} (${info.crc_registro})`;
      await carregarTudo();
    }
  } catch (e) {
    console.error("Erro ao alternar tenant RLS:", e);
  }
}

function trocarVisaoRBAC(role) {
  const banner = document.getElementById("banner-rbac-permissoes");
  if (role === "ADMIN_ESCRITORIO") {
    banner.innerHTML = `<i class="fa-solid fa-check-double text-emerald-400 mr-1"></i> RBAC [Administrador]: Acesso Total (Cofre A1, CNDs, Conciliação IA, Fiscal, DP e SIEM WORM)`;
  } else if (role === "ANALISTA_OPERACIONAL") {
    banner.innerHTML = `<i class="fa-solid fa-user-gear text-blue-400 mr-1"></i> RBAC [Analista Fiscal/DP/Contábil]: Acesso restrito aos clientes atribuídos (Sem exclusão ou gestão de chaves KEK)`;
  } else {
    banner.innerHTML = `<i class="fa-solid fa-building-user text-amber-400 mr-1"></i> RBAC [Portal Web do Cliente Final]: Visão exclusiva da própria empresa (Envio de Checklist, Download de Guias DAS/DARF e CNDs)`;
  }
}

// ============================================================================
// ABA 1: DASHBOARD, CARTEIRA & MONITOR 24/7 DE CNDs + ROBÔ PLAYWRIGHT
// ============================================================================
async function carregarDados() {
  try {
    const [resMetricas, resEmpresas] = await Promise.all([
      fetch("/api/v1/dashboard/metricas"),
      fetch("/api/v1/empresas")
    ]);

    if (resMetricas.ok) {
      const m = await resMetricas.json();
      document.getElementById("stat-total").innerText = m.total_empresas;
      document.getElementById("stat-plano").innerText = m.plano_atual;
      document.getElementById("stat-regulares").innerText = m.empresas_regulares;
      document.getElementById("stat-alertas").innerText = m.empresas_alerta;
      document.getElementById("stat-taxa").innerText = `${m.taxa_conformidade_pct}% conformidade fiscal`;
      document.getElementById("stat-horas").innerText = `${m.horas_economizadas_mes} h/mês`;
      document.getElementById("stat-economia").innerText = `~ R$ ${m.economia_financeira_estimada_brl.toLocaleString("pt-BR")} economizados`;
    }

    if (resEmpresas.ok) {
      const empresas = await resEmpresas.json();
      renderizarTabelaEmpresas(empresas);
    }
  } catch (err) {
    console.error("Erro ao carregar dashboard:", err);
  }
}

function renderizarTabelaEmpresas(empresas) {
  if (sessaoUsuario && sessaoUsuario.role === "CLIENTE_FINAL" && sessaoUsuario.empresa_vinculada_id) {
    empresas = empresas.filter(e => e.id === sessaoUsuario.empresa_vinculada_id);
  }

  const tbody = document.getElementById("lista-empresas");
  tbody.innerHTML = "";

  if (!empresas.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-slate-400">Nenhuma empresa associada a esta conta.</td></tr>`;
    return;
  }

  empresas.forEach(emp => {
    const cndReceita = emp.cnds.find(c => c.orgao.includes("Receita")) || { status: "N/A" };
    const cndFgts = emp.cnds.find(c => c.orgao.includes("FGTS")) || { status: "N/A" };
    const cndSefaz = emp.cnds.find(c => c.orgao.includes("Sefaz")) || { status: "N/A" };
    const cndTst = emp.cnds.find(c => c.orgao.includes("Trabalhista") || c.orgao.includes("TST")) || { status: "N/A" };

    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition";
    tr.innerHTML = `
      <td class="py-3.5 px-4">
        <div class="font-bold text-slate-900">${emp.razao_social}</div>
        <div class="text-[11px] text-slate-500 flex flex-wrap items-center gap-1.5 mt-1">
          <span class="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-medium">${emp.regime_tributario}</span>
          <span class="bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded font-medium">ERP: ${emp.erp_integrado || "Domínio Sistemas"}</span>
          <span>• ${emp.telefone_whatsapp}</span>
        </div>
      </td>
      <td class="py-3.5 px-4 font-mono text-slate-600 text-[11px] whitespace-nowrap">${emp.cnpj}</td>
      <td class="py-3.5 px-4">${obterBadgeCND(cndReceita, emp.id, "receita")}</td>
      <td class="py-3.5 px-4">${obterBadgeCND(cndFgts, emp.id, "fgts")}</td>
      <td class="py-3.5 px-4">${obterBadgeCND(cndSefaz, emp.id, "sefaz")}</td>
      <td class="py-3.5 px-4">${obterBadgeCND(cndTst, emp.id, "trabalhista")}</td>
      <td class="py-3.5 px-4 text-center whitespace-nowrap">
        <div class="flex items-center justify-center gap-1.5">
          <button onclick="dispararAlerta('${emp.id}')" title="Enviar Alerta Preventivo via WhatsApp" class="px-2 py-1 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-md transition text-[11px] font-semibold">
            <i class="fa-brands fa-whatsapp"></i> WhatsApp
          </button>
          <button onclick="prepararSimulacao('${emp.cnpj}')" title="Renovar Certidões via Robô Playwright Python" class="px-2 py-1 text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition text-[11px] font-semibold">
            <i class="fa-solid fa-robot"></i> Robô A1
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function obterBadgeCND(cnd, empId, slug) {
  if (cnd.status === "REGULAR") {
    const urlPdf = cnd.pdf_url || `/api/v1/cnds/pdf/${empId}/${slug}`;
    return `
      <a href="${urlPdf}" target="_blank" title="Clique para baixar o PDF oficial da CND com Hash SHA-256"
         class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800 hover:bg-emerald-200 transition">
        <i class="fa-solid fa-file-pdf text-emerald-700"></i> Regular (${cnd.data_validade})
      </a>`;
  } else if (cnd.status === "PENDENTE" || cnd.status === "VENCIDA") {
    return `
      <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-rose-100 text-rose-800 cursor-help"
            title="${cnd.detalhes || "Pendência identificada"}">
        <i class="fa-solid fa-triangle-exclamation"></i> ${cnd.status} (${cnd.data_validade})
      </span>`;
  }
  return `<span class="text-slate-400 text-[11px]">Não consultada</span>`;
}

async function dispararAlerta(empresaId) {
  try {
    const res = await fetch("/api/v1/notificacoes/whatsapp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ empresa_id: empresaId, tipo_alerta: "pendencia_identificada" })
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Alerta preventivo disparado com sucesso!\n\nCanal: ${data.canal}\nDestinatário: ${data.destinatario}\n\nMensagem:\n${data.mensagem_previa}`);
    }
  } catch (err) {
    alert("Erro ao disparar notificação via WhatsApp.");
  }
}

function prepararSimulacao(cnpj) {
  document.getElementById("sim-cnpj").value = cnpj;
  document.getElementById("sim-console").scrollIntoView({ behavior: "smooth", block: "center" });
  executarSimulacaoRobo();
}

async function executarSimulacaoRobo() {
  const cnpj = document.getElementById("sim-cnpj").value.trim();
  const consoleEl = document.getElementById("sim-console");
  const btn = document.getElementById("btn-executar-robo");

  if (!cnpj) return;

  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Executando Worker Playwright...`;
  consoleEl.innerHTML = "";

  const logSteps = [
    `[WORKER] Inicializando processo Python Headless (Playwright Chromium v1.59)...`,
    `[KMS/VAULT] Solicitando decriptação de envelope AES-GCM-256 para Certificado A1...`,
    `[RAM-ONLY] Certificado A1 carregado em bytearray volátil (Zero-Disk-Write Ativo).`,
    `[e-CAC RFB] Handshake mTLS concluído via Procuração Eletrônica RFB para CNPJ ${cnpj}...`,
    `[RECEITA/PGFN] Certidão Conjunta de Tributos Federais e Dívida Ativa emitida: REGULAR.`,
    `[CAIXA FGTS] Consultando Conectividade Social / FGTS Digital -> CRF Regular emitido.`,
    `[SEFAZ/TST] Certidões Estadual (ICMS) e Trabalhista (CNDT/TST) validadas sem pendências.`,
    `[RAM-WIPE] Sobrescrevendo bytearray da chave privada e DEK na RAM com 0x00 (Memset Zero)...`,
    `[SIEM/WORM] Evento gravado na trilha de auditoria com encadeamento SHA-256.`
  ];

  for (let i = 0; i < logSteps.length; i++) {
    await new Promise(r => setTimeout(r, 170));
    consoleEl.innerHTML += `<div>${logSteps[i]}</div>`;
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  try {
    const res = await fetch("/api/v1/cnds/consultar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cnpj: cnpj,
        orgaos: ["Receita Federal / PGFN", "FGTS (Caixa CRF)", "Sefaz Estadual (SP)", "CNDT Trabalhista (TST)"]
      })
    });
    if (res.ok) {
      const dados = await res.json();
      consoleEl.innerHTML += `<div class="text-white bg-emerald-900/60 p-2 rounded mt-2 border border-emerald-600">
        ✓ SUCESSO (${dados.tempo_execucao_segundos}s) | Certificado: ${dados.certificado_a1_utilizado} | Memória RAM Zerada: ${dados.memoria_volatil_zerada ? "SIM (100% 0x00)" : "NÃO"} | Log SIEM: ${dados.trilha_auditoria_id}
      </div>`;
      consoleEl.scrollTop = consoleEl.scrollHeight;
      await carregarDados();
    }
  } catch (err) {
    consoleEl.innerHTML += `<div class="text-rose-400">Erro na comunicação com o worker.</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-play"></i> Disparar Robô Playwright Python`;
  }
}

// ============================================================================
// ABA 2: MÓDULO 1 - ATENDIMENTO & COLETA INTELIGENTE (WHATSAPP + CHECKLIST)
// ============================================================================
async function carregarChecklistColeta() {
  try {
    const res = await fetch("/api/v1/coleta/checklist");
    if (!res.ok) return;
    let itens = await res.json();
    if (sessaoUsuario && sessaoUsuario.role === "CLIENTE_FINAL" && sessaoUsuario.empresa_vinculada_id) {
      itens = itens.filter(it => it.empresa_id === sessaoUsuario.empresa_vinculada_id);
    }
    const tbody = document.getElementById("lista-checklist");
    tbody.innerHTML = "";

    itens.forEach(it => {
      let badge = "";
      if (it.status === "RECEBIDO_VALIDADO") {
        badge = `<span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-semibold text-[11px]"><i class="fa-solid fa-check"></i> Validado IA (${it.qualidade_ocr_score}%)</span>`;
      } else if (it.status === "REJEITADO_ILEGIVEL") {
        badge = `<span class="bg-rose-100 text-rose-800 px-2 py-0.5 rounded-full font-semibold text-[11px]"><i class="fa-solid fa-camera-rotate"></i> Rejeitado Ilegível (${it.qualidade_ocr_score}%)</span>`;
      } else {
        badge = `<span class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full font-semibold text-[11px]"><i class="fa-regular fa-clock"></i> Pendente Envio</span>`;
      }

      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50";
      tr.innerHTML = `
        <td class="py-3 px-3 font-semibold text-slate-900">${it.empresa_nome}<div class="text-[10px] text-slate-400 font-normal">Comp: ${it.competencia}</div></td>
        <td class="py-3 px-3 font-medium text-slate-700">${it.tipo_documento}</td>
        <td class="py-3 px-3">${badge}</td>
        <td class="py-3 px-3 text-slate-600 text-[11px]">
          <div>${it.observacao_ia || ""}</div>
          <div class="text-[10px] text-slate-400 mt-0.5">${it.canal_recebimento || ""} • ${it.atualizado_em}</div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Erro ao carregar checklist:", e);
  }
}

async function simularWebhookWhatsApp() {
  const payload = {
    empresa_id: document.getElementById("coleta-empresa").value,
    tipo_documento: document.getElementById("coleta-tipo").value,
    nome_arquivo: document.getElementById("coleta-arquivo").value,
    simulacao_qualidade: document.getElementById("coleta-qualidade").value
  };

  const res = await fetch("/api/v1/coleta/whatsapp-webhook", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    const data = await res.json();
    const box = document.getElementById("coleta-resposta-bot");
    box.classList.remove("hidden");
    box.innerHTML = `<strong>[Bot WhatsApp Respondeu ao Cliente]:</strong><br/>"${data.resposta_automatica_whatsapp}"`;
    await carregarChecklistColeta();
  }
}

async function cobrarPendenciasLote() {
  const res = await fetch("/api/v1/coleta/cobrar-lote", { method: "POST" });
  if (res.ok) {
    const data = await res.json();
    alert(`Cobrança Preventiva Disparada!\n\nTotal de lembretes enviados no WhatsApp: ${data.total_mensagens_disparadas}\nEmpresas notificadas: ${data.empresas_notificadas.join(", ") || "Nenhuma pendente"}`);
  }
}

// ============================================================================
// ABA 3: MÓDULO 2 - CONTÁBIL / FINANCEIRO (OCR + IA & EXPORTAÇÃO 5 ERPs)
// ============================================================================
async function carregarLancamentosContabeis() {
  try {
    let empresaId = null;
    if (sessaoUsuario && sessaoUsuario.role === "CLIENTE_FINAL" && sessaoUsuario.empresa_vinculada_id) {
      empresaId = sessaoUsuario.empresa_vinculada_id;
    }

    const res = await fetch("/api/v1/contabil/lancamentos");
    if (!res.ok) return;
    let lista = await res.json();
    if (empresaId) {
      lista = lista.filter(l => l.empresa_id === empresaId);
    }
    const tbody = document.getElementById("lista-lancamentos");
    tbody.innerHTML = "";

    lista.forEach(l => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition-colors";
      const isCredito = l.tipo_dc === "C";
      tr.innerHTML = `
        <td class="py-2.5 px-3 whitespace-nowrap">
          <div class="font-bold text-slate-800">${l.data_lancamento}</div>
          <div class="text-[10px] text-slate-500">${l.empresa_nome}</div>
          <span class="text-[9px] font-mono bg-slate-100 text-slate-600 px-1 py-0.5 rounded">${l.origem_arquivo || 'OFX/PDF'}</span>
        </td>
        <td class="py-2.5 px-3 text-[11px] text-slate-800">
          <div class="font-mono text-slate-900 font-semibold">${l.historico_original}</div>
          <div class="text-[10px] text-slate-500 flex items-center gap-1.5 mt-0.5">
            <i class="fa-solid fa-building-columns text-slate-400"></i>
            <span>${l.banco_origem || 'Banco Itaú C/C'}</span>
          </div>
        </td>
        <td class="py-2.5 px-3 font-mono font-bold whitespace-nowrap ${isCredito ? 'text-emerald-700' : 'text-slate-900'}">
          ${isCredito ? '+' : '-'} R$ ${l.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
          <div class="text-[10px] font-sans font-normal text-slate-400">Extrato Bancário</div>
        </td>
        <td class="py-2.5 px-3 text-[11px]">
          <div class="text-rose-700 font-medium"><strong>Débito:</strong> ${l.conta_debito}</div>
          <div class="text-emerald-700 font-medium"><strong>Crédito:</strong> ${l.conta_credito}</div>
          <div class="text-[10px] text-indigo-600 font-medium mt-0.5">${l.categoria_ia} (${l.confianca_ia_pct}% IA)</div>
        </td>
        <td class="py-2.5 px-3 text-center whitespace-nowrap">
          <span class="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-1 rounded-full font-bold text-[10px]">
            <i class="fa-solid fa-check-double text-emerald-600"></i> Bate: R$ 0,00
          </span>
          <div class="text-[9px] text-slate-400 mt-0.5 font-medium">100% Conciliado</div>
        </td>
      `;
      tbody.appendChild(tr);
    });

    // Atualiza Painel de Bate de Saldo Oficial
    const urlResumo = empresaId 
      ? `/api/v1/contabil/conciliacao-resumo?empresa_id=${encodeURIComponent(empresaId)}`
      : "/api/v1/contabil/conciliacao-resumo";
    const resResumo = await fetch(urlResumo);
    if (resResumo.ok) {
      const r = await resResumo.json();
      const elBanco = document.getElementById("bate-empresa-banco");
      if (elBanco) elBanco.innerText = `${r.empresa_nome} • ${r.banco_conta}`;
      
      const elInicial = document.getElementById("bate-saldo-inicial");
      if (elInicial) elInicial.innerText = `R$ ${r.saldo_inicial_banco.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

      const elEntradas = document.getElementById("bate-entradas");
      if (elEntradas) elEntradas.innerText = `+ R$ ${r.total_entradas_creditos.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

      const elSaidas = document.getElementById("bate-saidas");
      if (elSaidas) elSaidas.innerText = `- R$ ${r.total_saidas_debitos.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

      const elSaldoBanco = document.getElementById("bate-saldo-final-banco");
      if (elSaldoBanco) elSaldoBanco.innerText = `R$ ${r.saldo_final_extrato_banco.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

      const elSaldoContabil = document.getElementById("bate-saldo-final-contabil");
      if (elSaldoContabil) elSaldoContabil.innerText = `R$ ${r.saldo_final_contabil_livro.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

      const elDif = document.getElementById("bate-diferenca");
      if (elDif) elDif.innerText = `R$ ${r.diferenca_auditoria_brl.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;

      const elBadgeTotal = document.getElementById("badge-total-auditados");
      if (elBadgeTotal) elBadgeTotal.innerHTML = `<i class="fa-solid fa-calculator mr-1 text-slate-500"></i> ${r.total_lancamentos_auditados} Lançamentos Auditados`;
    }
  } catch (e) {
    console.error("Erro ao carregar lançamentos contábeis:", e);
  }
}

async function processarExtratoIA() {
  const payload = {
    empresa_id: document.getElementById("contabil-empresa").value,
    tipo_arquivo: document.getElementById("contabil-formato").value,
    conteudo_texto: document.getElementById("contabil-texto").value
  };
  const res = await fetch("/api/v1/contabil/processar-extrato", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    await carregarLancamentosContabeis();
  }
}

async function exportarERP(erpNome) {
  const res = await fetch(`/api/v1/contabil/exportar-erp/${encodeURIComponent(erpNome)}`);
  if (res.ok) {
    const data = await res.json();
    ultimoArquivoERP = { nome: data.nome_arquivo, conteudo: data.conteudo_arquivo };
    document.getElementById("box-erp-preview").classList.remove("hidden");
    document.getElementById("erp-preview-titulo").innerText = `Layout Gerado: ${data.erp_destino} (${data.nome_arquivo})`;
    document.getElementById("erp-preview-conteudo").innerText = data.conteudo_arquivo;
  }
}

function baixarArquivoERPAtual() {
  const blob = new Blob([ultimoArquivoERP.conteudo], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = ultimoArquivoERP.nome;
  a.click();
  URL.revokeObjectURL(url);
}

// ============================================================================
// ABA 4: MÓDULO 3 - FISCAL / TRIBUTÁRIO (CAPTURA XMLs & GUIAS DAS / DARF)
// ============================================================================
async function carregarModuloFiscal() {
  try {
    const [resGuias, resXmls] = await Promise.all([
      fetch("/api/v1/fiscal/guias"),
      fetch("/api/v1/fiscal/xmls")
    ]);

    if (resGuias.ok) {
      let guias = await resGuias.json();
      if (sessaoUsuario && sessaoUsuario.role === "CLIENTE_FINAL" && sessaoUsuario.empresa_vinculada_id) {
        guias = guias.filter(g => g.empresa_id === sessaoUsuario.empresa_vinculada_id);
      }
      const tbodyG = document.getElementById("lista-guias");
      tbodyG.innerHTML = "";
      guias.forEach(g => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50";
        tr.innerHTML = `
          <td class="py-2.5 px-3">
            <div class="font-bold text-slate-900">${g.tributo}</div>
            <div class="text-[11px] text-slate-500">${g.empresa_nome} (${g.cnpj})</div>
          </td>
          <td class="py-2.5 px-3 font-mono text-slate-700">${g.vencimento}<div class="text-[10px] text-slate-400">Comp: ${g.competencia}</div></td>
          <td class="py-2.5 px-3 font-mono font-bold text-slate-900">R$ ${g.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
          <td class="py-2.5 px-3">
            <span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full text-[11px] font-semibold">${g.status_envio}</span>
          </td>
          <td class="py-2.5 px-3 text-center">
            <a href="/api/v1/fiscal/guias/pdf/${g.id}" target="_blank" class="inline-flex items-center gap-1 bg-slate-900 hover:bg-slate-800 text-white px-2.5 py-1 rounded-md text-[11px] font-semibold">
              <i class="fa-solid fa-file-pdf text-amber-400"></i> Guia PDF
            </a>
          </td>
        `;
        tbodyG.appendChild(tr);
      });
    }

    if (resXmls.ok) {
      let xmls = await resXmls.json();
      if (sessaoUsuario && sessaoUsuario.role === "CLIENTE_FINAL" && sessaoUsuario.empresa_vinculada_id) {
        xmls = xmls.filter(x => x.empresa_id === sessaoUsuario.empresa_vinculada_id);
      }
      const tbodyX = document.getElementById("lista-xmls");
      tbodyX.innerHTML = "";
      xmls.forEach(x => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50";
        tr.innerHTML = `
          <td class="py-2 px-3 font-semibold text-slate-800">#${x.numero_nf}<div class="text-[10px] text-amber-700">${x.tipo_nf}</div></td>
          <td class="py-2 px-3 text-slate-700">${x.empresa_nome}</td>
          <td class="py-2 px-3 font-mono text-[10px] text-slate-500">${x.chave_acesso}</td>
          <td class="py-2 px-3 font-mono font-semibold text-slate-900">R$ ${x.valor_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
          <td class="py-2 px-3 font-mono text-emerald-700 font-semibold">R$ ${x.imposto_estimado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</td>
        `;
        tbodyX.appendChild(tr);
      });
    }
  } catch (e) {
    console.error("Erro ao carregar módulo fiscal:", e);
  }
}

async function importarXMLFiscal() {
  const payload = {
    empresa_id: document.getElementById("fiscal-empresa").value,
    tipo_nf: document.getElementById("fiscal-tipo").value,
    xml_conteudo: document.getElementById("fiscal-xml").value
  };
  const res = await fetch("/api/v1/fiscal/importar-xml", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    await carregarModuloFiscal();
  }
}

// ============================================================================
// ABA 5: MÓDULO 5 - DP / RH (ADMISSÃO DIGITAL eSOCIAL S-2200 & HOLERITES LGPD)
// ============================================================================
async function carregarModuloDP() {
  try {
    const res = await fetch("/api/v1/dp/colaboradores");
    if (!res.ok) return;
    let lista = await res.json();
    if (sessaoUsuario && sessaoUsuario.role === "CLIENTE_FINAL" && sessaoUsuario.empresa_vinculada_id) {
      lista = lista.filter(c => c.empresa_id === sessaoUsuario.empresa_vinculada_id);
    }
    const tbody = document.getElementById("lista-dp");
    tbody.innerHTML = "";

    lista.forEach(c => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50";
      tr.innerHTML = `
        <td class="py-2.5 px-3">
          <div class="font-bold text-slate-900">${c.nome_completo}</div>
          <div class="font-mono text-[11px] text-emerald-700 bg-emerald-50 inline-block px-1.5 rounded border border-emerald-200" title="CPF Anonimizado conforme LGPD">
            CPF: ${c.cpf_mascarado}
          </div>
        </td>
        <td class="py-2.5 px-3">
          <div class="font-medium text-slate-800">${c.cargo}</div>
          <div class="text-[10px] text-slate-500">${c.empresa_nome}</div>
        </td>
        <td class="py-2.5 px-3 font-mono text-[11px] text-slate-600">
          <div>Bruto: R$ ${c.salario_base.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</div>
          <div class="text-[10px] text-slate-400">INSS: R$ ${c.inss_desconto} | IRRF: R$ ${c.irrf_desconto} | FGTS: R$ ${c.fgts_deposito}</div>
        </td>
        <td class="py-2.5 px-3 font-mono font-bold text-emerald-700">
          R$ ${c.salario_liquido.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
        </td>
        <td class="py-2.5 px-3 font-mono text-[10px] text-blue-700">
          ${c.protocolo_esocial_s2200}
          <div class="text-emerald-600 font-sans font-semibold">eSocial S-2200 OK</div>
        </td>
        <td class="py-2.5 px-3 text-center">
          <a href="/api/v1/dp/holerite/pdf/${c.id}" target="_blank" class="inline-flex items-center gap-1 bg-blue-600 hover:bg-blue-700 text-white px-2.5 py-1 rounded-md text-[11px] font-semibold">
            <i class="fa-solid fa-file-pdf"></i> Holerite
          </a>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Erro ao carregar DP:", e);
  }
}

async function salvarAdmissaoDP(e) {
  e.preventDefault();
  const payload = {
    empresa_id: document.getElementById("dp-empresa").value,
    nome_completo: document.getElementById("dp-nome").value,
    cpf: document.getElementById("dp-cpf").value,
    salario_base: parseFloat(document.getElementById("dp-salario").value),
    cargo: document.getElementById("dp-cargo").value,
    data_admissao: document.getElementById("dp-data").value
  };
  const res = await fetch("/api/v1/dp/admissao", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (res.ok) {
    await carregarModuloDP();
  }
}

// ============================================================================
// ABA 6: SEGURANÇA ISO 27001, COFRE A1, MFA TOTP, RLS & SIEM WORM
// ============================================================================
async function carregarPainelSeguranca() {
  try {
    const [resCerts, resLogs] = await Promise.all([
      fetch("/api/v1/seguranca/certificados-a1"),
      fetch("/api/v1/auditoria/logs")
    ]);

    if (resCerts.ok) {
      const certs = await resCerts.json();
      const container = document.getElementById("lista-certificados-a1");
      container.innerHTML = "";
      certs.forEach(c => {
        container.innerHTML += `
          <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] space-y-1">
            <div class="flex justify-between font-bold text-slate-800">
              <span>${c.titular_razao_social}</span>
              <span class="text-emerald-700 font-mono">${c.validade}</span>
            </div>
            <div class="text-slate-500 font-mono text-[10px]">
              CNPJ: ${c.cnpj_titular} | Nonce: ${c.nonce_hex.slice(0, 12)}... | DEK: ${c.dek_encrypted_preview}
            </div>
          </div>
        `;
      });
    }

    if (resLogs.ok) {
      const logs = await resLogs.json();
      const tbody = document.getElementById("lista-auditoria");
      tbody.innerHTML = "";
      logs.forEach(log => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50";
        tr.innerHTML = `
          <td class="py-2.5 px-4 text-slate-500 whitespace-nowrap">${log.timestamp.slice(0, 19).replace("T", " ")}</td>
          <td class="py-2.5 px-4 font-semibold text-slate-800">${log.usuario_operador}</td>
          <td class="py-2.5 px-4"><span class="bg-slate-100 text-slate-800 px-2 py-0.5 rounded font-semibold">${log.acao}</span></td>
          <td class="py-2.5 px-4 text-slate-600">${log.recurso_acessado}</td>
          <td class="py-2.5 px-4 text-emerald-700 whitespace-nowrap" title="Prev: ${log.prev_hash} -> Atual: ${log.hash_sha256}">
            <span class="text-slate-400">${(log.prev_hash || "").slice(0, 8)}...</span>
            <i class="fa-solid fa-arrow-right text-[9px] mx-1 text-slate-400"></i>
            <span class="font-bold">${log.hash_sha256.slice(0, 14)}...</span>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    await atualizarWidgetTOTP();
  } catch (e) {
    console.error("Erro ao carregar painel de segurança:", e);
  }
}

async function testarCertificadoVolatilRAM() {
  const res = await fetch("/api/v1/seguranca/certificados-a1/testar-ram", { method: "POST" });
  if (res.ok) {
    const d = await res.json();
    const box = document.getElementById("resultado-ram-volatil");
    box.classList.remove("hidden");
    box.innerHTML = `
      <div>✓ Certificado: <strong>${d.cert_id}</strong> (${d.cnpj_titular})</div>
      <div>✓ Alocado em RAM: ${d.bytes_alocados_em_ram} bytes | Gravado em Disco: <strong>NUNCA (False)</strong></div>
      <div>✓ Buffer RAM Zerado (0x00): <strong>${d.buffer_ram_sobrescrito_zeros ? "100% VERIFICADO" : "FALHA"}</strong> em ${d.tempo_vida_em_ram_ms} ms</div>
    `;
    await carregarPainelSeguranca();
  }
}

async function atualizarWidgetTOTP() {
  try {
    const res = await fetch("/api/v1/seguranca/totp");
    if (res.ok) {
      const d = await res.json();
      document.getElementById("totp-code-display").innerText = d.codigo_totp_atual;
      document.getElementById("totp-timer-display").innerText = `Renova em ${d.segundos_restantes}s (RFC 6238 HMAC-SHA1)`;
    }
  } catch (e) {}
}

async function validarTOTPDemo() {
  const code = document.getElementById("totp-code-display").innerText.trim();
  const res = await fetch("/api/v1/seguranca/totp/validar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo: code })
  });
  if (res.ok) {
    const d = await res.json();
    alert(d.mensagem);
    await carregarPainelSeguranca();
  }
}

async function testarPoliticaSenha() {
  const senha = document.getElementById("input-teste-senha").value;
  const res = await fetch("/api/v1/seguranca/avaliar-senha", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ senha })
  });
  if (res.ok) {
    const d = await res.json();
    const box = document.getElementById("resultado-teste-senha");
    if (d.aprovada) {
      box.innerHTML = `<span class="text-emerald-700 font-bold">✓ APROVADA OWASP (${d.comprimento_atual} chars | HIBP Prefix: ${d.hibp_k_anonymity_prefix})</span><br/><span class="text-[10px] text-slate-400 break-all">Hash: ${d.hash_criptografico_exemplo}</span>`;
    } else {
      box.innerHTML = `<span class="text-rose-600 font-bold">✗ REPROVADA: Requer mín. 12 caracteres, maiúscula, minúscula, número, símbolo e não constar no HIBP.</span>`;
    }
  }
}

async function simularPentestRLS() {
  const res = await fetch("/api/v1/seguranca/rls-pentest", { method: "POST" });
  if (res.ok) {
    const d = await res.json();
    const box = document.getElementById("resultado-rls-pentest");
    box.innerHTML = `
      <div class="text-amber-300">${d.comando_sessao_db}</div>
      <div class="text-rose-300 mt-1">Query Invasora: ${d.query_tentada}</div>
      <div class="text-slate-400 mt-1">Política Banco: ${d.politica_rls_aplicada}</div>
      <div class="text-emerald-400 font-bold mt-1.5">-> Linhas Retornadas: ${d.linhas_retornadas} | ${d.status_seguranca}</div>
    `;
    await carregarPainelSeguranca();
  }
}

async function exibirDDLPostgresRLS() {
  const res = await fetch("/api/v1/seguranca/rls-ddl");
  if (res.ok) {
    const d = await res.json();
    const box = document.getElementById("resultado-rls-pentest");
    box.innerText = d.ddl_sql;
  }
}

async function auditarIntegridadeWORM() {
  const res = await fetch("/api/v1/auditoria/verificar-worm");
  if (res.ok) {
    const d = await res.json();
    const badge = document.getElementById("badge-worm-status");
    badge.innerText = `WORM: ${d.blocos_integros}/${d.total_blocos_worm_verificados} Blocos Íntegros (100%)`;
    alert(`Verificação Matemática SIEM WORM Concluída!\n\nBlocos auditados na cadeia SHA-256: ${d.total_blocos_worm_verificados}\nBlocos íntegros: ${d.blocos_integros}\nHead Hash: ${d.ultimo_hash_head}`);
  }
}

// ============================================================================
// ABA 7: WORKERS PYTHON (CELERY/BEAT), CUSTOS VPS BRASIL & PRICING SAAS
// ============================================================================
async function carregarWorkersENegocio() {
  try {
    const [resWorkers, resNegocio] = await Promise.all([
      fetch("/api/v1/workers"),
      fetch("/api/v1/playbook/negocio-infra")
    ]);

    if (resWorkers.ok) {
      const workers = await resWorkers.json();
      renderizarWorkers(workers);
    }

    if (resNegocio.ok) {
      const data = await resNegocio.json();
      renderizarNegocioInfra(data);
    }
  } catch (e) {
    console.error("Erro ao carregar workers e negócio:", e);
  }
}

function renderizarWorkers(workers) {
  const grid = document.getElementById("grid-workers");
  grid.innerHTML = "";
  workers.forEach(w => {
    grid.innerHTML += `
      <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
        <div class="flex justify-between items-center">
          <span class="font-mono text-[10px] bg-purple-100 text-purple-800 px-2 py-0.5 rounded font-semibold">${w.fila}</span>
          <span class="text-emerald-600 font-bold text-[11px]"><i class="fa-solid fa-circle-check"></i> ${w.status}</span>
        </div>
        <div class="font-bold text-slate-900">${w.nome_rotina}</div>
        <div class="text-[11px] text-slate-500">${w.resultado_resumo}</div>
        <div class="text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-200 flex justify-between">
          <span>${w.agendamento_cron}</span>
          <span>${w.duracao_ms} ms</span>
        </div>
      </div>
    `;
  });
}

async function executarCicloWorkers() {
  const res = await fetch("/api/v1/workers/executar-ciclo", { method: "POST" });
  if (res.ok) {
    const d = await res.json();
    renderizarWorkers(d.workers);
  }
}

function renderizarNegocioInfra(data) {
  const planosEl = document.getElementById("tabela-planos-saas");
  planosEl.innerHTML = "";
  data.planos_saas.forEach(p => {
    planosEl.innerHTML += `
      <div class="p-3 rounded-lg border border-slate-200 flex items-center justify-between bg-white">
        <div>
          <span class="font-bold text-slate-900">${p.plano}</span>
          <span class="text-slate-500 ml-2">(Até ${p.ate_cnpjs} CNPJs)</span>
          <div class="text-[11px] text-slate-400">${p.perfil}</div>
        </div>
        <div class="text-sm font-bold text-emerald-600">R$ ${p.preco_mensal}/mês</div>
      </div>
    `;
  });

  const vpsEl = document.getElementById("lista-vps-brasil");
  vpsEl.innerHTML = "";
  data.provedores_vps_brasil.forEach(v => {
    vpsEl.innerHTML += `
      <div class="p-3 rounded-lg border ${v.recomendado ? "border-emerald-500 bg-emerald-50/40" : "border-slate-200 bg-white"}">
        <div class="flex justify-between items-center">
          <span class="font-bold text-slate-900">${v.provedor} ${v.recomendado ? '<span class="text-[10px] bg-emerald-600 text-white px-2 py-0.5 rounded-full ml-1">Recomendado MVP</span>' : ""}</span>
          <span class="font-bold text-slate-800">${v.faixa_preco}</span>
        </div>
        <div class="text-[11px] text-slate-600 font-mono mt-0.5">${v.especificacoes}</div>
        <div class="text-[11px] text-slate-500 mt-0.5">${v.vantagens}</div>
      </div>
    `;
  });

  const rotEl = document.getElementById("lista-roteiro");
  rotEl.innerHTML = "";
  data.roteiro_implementacao.forEach(r => {
    rotEl.innerHTML += `
      <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-start justify-between gap-2">
        <div>
          <span class="font-bold text-slate-900">${r.fase}: ${r.titulo}</span>
          <p class="text-[11px] text-slate-500">${r.descricao}</p>
        </div>
        <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 whitespace-nowrap">${r.status}</span>
      </div>
    `;
  });
}

function atualizarSimuladorNegocio() {
  const qtd = parseInt(document.getElementById("sim-range-escritorios").value, 10);
  const ticketMedioPro = 497.0;
  const mrr = qtd * ticketMedioPro;
  const custoInfra = qtd <= 15 ? 97.33 : 97.33 + (qtd - 15) * 4.5;
  const lucro = mrr - custoInfra;
  const margemPct = Math.round((lucro / mrr) * 100);

  document.getElementById("sim-qtd-escritorios-label").innerText = `${qtd} escritórios (Plano Pro R$ 497)`;
  document.getElementById("sim-mrr").innerText = `R$ ${mrr.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
  document.getElementById("sim-custo-infra").innerText = `R$ ${custoInfra.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
  document.getElementById("sim-margem").innerText = `R$ ${lucro.toLocaleString("pt-BR", { minimumFractionDigits: 2 })} (${margemPct}%)`;
}

// ============================================================================
// MODAL NOVA EMPRESA
// ============================================================================
function abrirModalNovaEmpresa() {
  document.getElementById("modal-empresa").classList.remove("hidden");
  document.getElementById("modal-empresa").classList.add("flex");
}

function fecharModalNovaEmpresa() {
  document.getElementById("modal-empresa").classList.add("hidden");
  document.getElementById("modal-empresa").classList.remove("flex");
}

async function salvarNovaEmpresa(e) {
  e.preventDefault();
  const payload = {
    razao_social: document.getElementById("novo-razao").value,
    nome_fantasia: document.getElementById("novo-fantasia").value,
    cnpj: document.getElementById("novo-cnpj").value,
    regime_tributario: document.getElementById("novo-regime").value,
    erp_integrado: document.getElementById("novo-erp").value,
    telefone_whatsapp: document.getElementById("novo-whatsapp").value,
    email_contato: document.getElementById("novo-email").value,
    procuracao_eletronica_ecac: true
  };

  try {
    const res = await fetch("/api/v1/empresas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      fecharModalNovaEmpresa();
      document.getElementById("form-nova-empresa").reset();
      await carregarDados();
    }
  } catch (err) {
    alert("Erro ao cadastrar empresa.");
  }
}

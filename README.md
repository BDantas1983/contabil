# 🏛️ AuditContábil AI - Plataforma SaaS de Automação & Auditoria Contábil

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Vercel Deployment](https://img.shields.io/badge/Deploy-Vercel-black?logo=vercel)](https://contabil-lac.vercel.app)
[![Render Deployment](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render)](https://contabil-vvxp.onrender.com)
[![Segurança](https://img.shields.io/badge/Security-ISO%2027001%20%7C%20OWASP%20%7C%20NIST-green)](https://owasp.org)
[![Licença](https://img.shields.io/badge/License-MIT-purple)](#)

Plataforma SaaS multi-tenant desenvolvida para escritórios de contabilidade no Brasil, construída em **Python (FastAPI)** com arquitetura **Security-by-Design** (ISO 27001, NIST CSF e OWASP Top 10), garantindo isolamento total de dados de clientes (**PostgreSQL Row-Level Security - RLS**) e criptografia de ponta a ponta (**Envelope Encryption AES-GCM-256**) para certificados digitais A1.

---

## 🌐 Acessos e Demonstração Online

A aplicação está disponível e homologada em dois ambientes de nuvem pública:

* **🚀 Produção na Vercel:** [https://contabil-lac.vercel.app](https://contabil-lac.vercel.app)
* **☁️ Produção no Render:** [https://contabil-vvxp.onrender.com](https://contabil-vvxp.onrender.com)
* **📖 Documentação Interativa da API (Swagger/OpenAPI):** [/docs](https://contabil-lac.vercel.app/docs)
* **🐙 Repositório GitHub:** [https://github.com/BDantas1983/contabil](https://github.com/BDantas1983/contabil)

---

## 🔐 Credenciais de Acesso para Demonstração

O sistema possui controle de acesso por Tenant e perfis (RBAC - Role-Based Access Control):

| Perfil / Função | E-mail de Login | Senha | Nível de Acesso |
| :--- | :--- | :--- | :--- |
| **Escritório Contábil (Admin)** | `contadora.master@escritorio.com.br` | `SenhaForte@2026` | Acesso global a todas as empresas da carteira, relatórios e auditoria |
| **Cliente: Alpha Tecnologia** | `contato@alphatech.com.br` | `Alpha@2026!` | Portal do Cliente: extratos, balancete e guias da Alpha Consultoria |
| **Cliente: Supermercado** | `financeiro@superprogresso.com.br` | `Progresso@2026!` | Portal do Cliente: documentos e certidões do Supermercado Progresso |
| **Cliente: Clínica Médica** | `gestao@clinicasaolucas.med.br` | `Clinica@2026!` | Portal do Cliente: certidões e checklist da Clínica São Lucas |
| **Cliente: Logística Bandeirantes** | `fiscal@logisticabandeirantes.com.br` | `Bandeirantes@2026!` | Portal do Cliente: CNDs e rotinas trabalhistas da Transportadora |

---

## 🧩 Os 5 Módulos Operacionais da Plataforma

A plataforma integra os 5 pilares fundamentais da rotina de um escritório contábil moderno:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AUDITCONTÁBIL AI - SAAS PLATFORM                      │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────────┤
│   MÓDULO 1   │   MÓDULO 2   │   MÓDULO 3   │   MÓDULO 4   │    MÓDULO 5     │
│  Atendimento │  Contábil &  │   Fiscal &   │  Monitor de  │   DP / eSocial  │
│  & Coleta    │  Financeiro  │  Tributário  │  CNDs 24/7   │   LGPD          │
├──────────────┼──────────────┼──────────────┼──────────────┼─────────────────┤
│ • Bot Whats  │ • OCR/OFX/PDF│ • Guarda XML │ • Robôs CND  │ • Admissão Web  │
│ • Checklist  │ • Bate R$ 0  │ • DAS/DARF   │ • RFB, FGTS, │ • Alerta Férias │
│ • Validação  │ • Balancete  │ • Faturamento│   Sefaz, Pref│ • Cripto A1     │
│   Documental │ • 5 ERPs Lote│ • Código Bar.│ • Trilha Log │ • RLS Isolation │
└──────────────┴──────────────┴──────────────┴──────────────┴─────────────────┘
```

### 1. Módulo de Atendimento & Coleta Inteligente (WhatsApp + Checklist)
* **Autoatendimento 24/7 via WhatsApp:** O empresário pode solicitar suas Certidões Negativas (Receita Federal, FGTS, Sefaz e Municipal) ou 2ª via de guias a qualquer hora pelo WhatsApp. O robô emite o documento em tempo real e devolve os PDFs com chave de autenticidade instantaneamente.
* **Checklist Mensal Automatizado:** Acompanhamento do recebimento de extratos bancários, notas fiscais de tomada de serviços, comprovantes de despesas e apontamentos de folha.
* **Simulador de Recebimento via WhatsApp:** Ingestão de arquivos enviados pelo cliente com pré-validação instantânea de integridade e legibilidade.
* **Cobrança Ativa Preventiva:** Mensagens automatizadas com alerta de prazos de fechamento contábil e lembretes de vencimento.

### 2. Módulo Contábil & Financeiro (OCR/IA, Bate de Saldo & ERPs)
* **Ingestão Multi-Formato:** Leitura e extração de lançamentos a partir de arquivos bancários **OFX**, planilhas **CSV** e extratos/recibos em **PDF via OCR** (`pdfplumber` + IA).
* **Classificação por Partidas Dobradas:** Sugestão automatizada de conta Débito e Crédito conforme a categoria da transação com nível de confiança algorítmica.
* **Painel Executivo de Bate de Saldo Oficial (Diferença R$ 0,00):**
  $$\text{Saldo Inicial} + \text{Entradas (Créditos)} - \text{Saídas (Débitos)} = \text{Saldo Final Extrato} == \text{Saldo Razão Contábil}$$
  Conferência matemática centavo a centavo com selo de **100% Conciliado e Auditado**.
* **Cruzamento Lado a Lado (De-Para de Auditoria):** Apresentação visual da linha original do extrato bancário contra a escrituração contábil gerada.
* **Balancete de Verificação & Razão Contábil Oficial:**
  - Plano de Contas estruturado com **Códigos Reduzidos** (ex: `101 - Caixa`, `102 - Banco Itaú`, `103 - Bradesco`, `201 - Fornecedores`, `301 - Receita`).
  - Totalização oficial comprovando rigorosamente que $\sum \text{Débitos} = \sum \text{Créditos}$ com **Diferença R$ 0,00**.
* **Exportação Parametrizada de Lote para os 5 Principais ERPs Contábeis do Brasil:**
  - **Domínio Sistemas** (Thomson Reuters)
  - **Alterdata Software**
  - **Questor Sistemas**
  - **Contmatic Phoenix**
  - **Fortes Tecnologia**

### 3. Módulo Fiscal & Tributário
* **Guarda e Processamento de XMLs:** Ingestão e validação de documentos fiscais (NF-e, NFS-e e NFC-e).
* **Apuração de Faturamento Acumulado:** Cálculo em tempo real da base de cálculo para tributação.
* **Gestão e Monitoramento de Guias Tributárias:** Controle de vencimentos, valores e linha digitável/código de barras para **DAS (Simples Nacional)**, **DARF (DCTFWeb/Previdenciário)** e **FGTS Digital**.
* **Motor de Recálculo Automático de Guias Vencidas:** Aplicação imediata das regras oficiais de encargos tributários (multa moratória de 0,33%/dia limitada a 20% + taxa SELIC acumulada), gerando novo vencimento e novo código de barras/PIX para pagamento bancário.
* **Disparo de Guias e Lembretes no WhatsApp:** Envio automatizado de avisos prévios no dia do vencimento e emissão imediata da 2ª via recalculada diretamente no WhatsApp do cliente com código de barras clicável.

### 4. Módulo de Monitoramento 24/7 de CNDs & Dívida Ativa
* **Robô de Consulta Autônoma (Playwright Headless):** Varredura contínua de regularidade fiscal nos portais oficiais:
  - **Receita Federal / PGFN** (Certidão Conjunta Federal e Dívida Ativa da União)
  - **Caixa Econômica Federal** (Certidão de Regularidade do FGTS - CRF)
  - **Sefaz Estadual** (ICMS / Débitos Fiscais Estaduais)
  - **Prefeituras Municipais** (ISS e Taxas Mobiliárias)
* **Alertas Preventivos:** Notificação ao contador com 30 dias de antecedência antes do vencimento de qualquer certidão.

### 5. Módulo de DP / eSocial & Segurança LGPD
* **Admissão Digital Autônoma:** Cadastro simplificado de novos colaboradores pelo próprio cliente, com upload seguro de documentos e redução de erros de digitação.
* **Controle Preventivo de Férias:** Cálculo automático de período aquisitivo e concessivo, emitindo avisos de férias a vencer para evitar passivos trabalhistas (pagamento em dobro).
* **Controle de Afastamentos:** Monitoramento de atestados e afastamentos médicos superiores a 15 dias para encaminhamento previdenciário (INSS).

---

## 🛡️ Arquitetura de Segurança da Informação (Security-by-Design)

O sistema foi concebido sob as diretrizes das normas **ISO/IEC 27001**, **NIST Cybersecurity Framework** e recomendações do **OWASP Top 10**:

1. **Isolamento de Dados Multi-Tenant (PostgreSQL RLS):**
   - Uso de *Row-Level Security* nativo com variáveis de sessão `SET LOCAL app.current_tenant_id`. Nenhuma empresa cliente ou escritório consegue visualizar dados de outros clientes, mesmo em caso de falha de filtro na camada de aplicação.
2. **Criptografia de Certificados Digitais A1 (Envelope Encryption):**
   - Os certificados digitais `.pfx` / `.p12` são protegidos por criptografia simétrica **AES-GCM-256**. As chaves de dados (DEK) são envelopadas por uma chave mestra (KEK) com rotação periódica.
3. **Trilha de Auditoria Imutável (SIEM / Audit Trail):**
   - Todas as operações (login, alteração cadastral, upload, exclusão e conciliação) geram eventos de auditoria com carimbo de tempo UTC e **hash criptográfico SHA-256** do estado do registro para garantia de não-repúdio.
4. **Proteção de Cabeçalhos HTTP (OWASP):**
   - Middleware ativo injetando cabeçalhos de defesa: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Strict-Transport-Security (HSTS)` e `X-XSS-Protection`.

---

## 💻 Como Executar Localmente

### Pré-requisitos
* Python 3.10 ou superior instalado.
* Git.

### Instalação e Execução

```bash
# 1. Clone o repositório
git clone https://github.com/BDantas1983/contabil.git
cd contabil

# 2. Crie e ative um ambiente virtual (recomendado)
python -m venv venv
# No Windows:
.\venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie o servidor FastAPI
uvicorn app.main:app --reload --port 8000
```

Abra no seu navegador:
* **Interface Web:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Documentação Swagger:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📁 Estrutura de Diretórios do Projeto

```
d:\contabil
├── api/
│   └── index.py               # Handler Serverless compatível com Vercel (ASGI adapter)
├── app/
│   ├── config.py              # Configurações de ambiente, KEK e diretórios seguros
│   ├── database.py            # Simulador de PostgreSQL com Row-Level Security (RLS)
│   ├── main.py                # Ponto de entrada FastAPI, Middlewares OWASP e Rotas REST
│   ├── models.py              # Modelos Pydantic v2 (Validação estrita e tipagem)
│   ├── services/
│   │   ├── cnd_service.py     # Lógica de CNDs, empresas e simulador Playwright
│   │   ├── modules_service.py # Lógica dos 5 módulos (OCR, Balancete, ERPs, Fiscal, DP)
│   │   ├── pdf_service.py     # Gerador de relatórios executivos em PDF
│   │   └── security_service.py# Criptografia AES-GCM-256, IAM, TOTP e Auditoria SHA-256
│   └── static/
│       ├── app.js             # Lógica do front-end SPA e chamadas assíncronas à API
│       └── index.html         # Painel administrativo responsivo (TailwindCSS + FontAwesome)
├── requirements.txt           # Dependências de produção
├── vercel.json                # Configuração de build e rotas para Vercel Serverless
└── README.md                  # Este documento
```

---

## 👥 Autoria & Licença

* **Desenvolvido por:** Brisa Kalene (`kalenebrisa@gmail.com`)
* **Repositório:** [https://github.com/BDantas1983/contabil](https://github.com/BDantas1983/contabil)
* **Licença:** Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para obter mais detalhes.

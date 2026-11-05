# AuditContábil AI - MVP (SaaS de Automação Contábil)

Este repositório contém a versão **MVP funcional** do SaaS para automação contábil, construído em **Python (FastAPI)** com foco em monitoramento autônomo de Certidões Negativas de Débitos (CNDs), soberania de dados (LGPD) e segurança da informação baseada nos padrões **ISO 27001 e OWASP**.

---

## 🎯 O Que Este MVP Demonstra para a sua Professora:

1. **Dashboard Operacional do Escritório Contábil:**
   - Métricas de carteira (total de empresas, taxa de conformidade, certidões regulares vs. em alerta).
   - Cálculo automático de **horas economizadas** pela equipe operacional no mês.
2. **Monitoramento Integrado de CNDs:**
   - Acompanhamento em tempo real das certidões: **Receita Federal / PGFN**, **FGTS (Caixa CRF)** e **Sefaz Estadual**.
   - Cadastro ágil de novos clientes da carteira com validação de regime tributário.
3. **Simulador de Execução do Robô Python (Playwright):**
   - Terminal interativo com logs em tempo real demonstrando a consulta headless aos portais oficiais com certificado A1.
4. **Painel de Segurança & LGPD (ISO 27001 / OWASP):**
   - Demonstração de **Envelope Encryption** (AES-GCM-256) para certificados A1.
   - Demonstração de isolamento multi-tenant via **PostgreSQL Row-Level Security (RLS)**.
   - Trilha de auditoria imutável (SIEM) com **hashing SHA-256** para cada ação executada.
5. **Comunicação Ativa com o Cliente:**
   - Disparo simulado de notificações preventivas via WhatsApp.
6. **API REST Documentada:**
   - Swagger OpenAPI interativo em `/docs`.

---

## 🚀 Como Executar Localmente (em 1 minuto):

Como você já tem o Python instalado no seu computador, basta executar:

```bash
# Na pasta d:\contabil
uvicorn app.main:app --reload --port 8000
```

Abra o navegador no endereço:
* **Dashboard Visual:** [http://localhost:8000](http://localhost:8000)
* **Documentação Swagger da API:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ☁️ Como Publicar na Nuvem Gratuitamente (GitHub + Render):

Você pode colocar este projeto no ar com link público HTTPS para apresentar para a sua professora sem gastar nada:

### Passo 1: Criar Repositório no GitHub
1. Acesse [github.com](https://github.com) e crie um novo repositório (pode ser público ou privado), por exemplo `auditcontabil-mvp`.
2. No terminal da pasta `d:\contabil`:
   ```bash
   git init
   git add .
   # (Lembre-se de configurar seu nome e email antes do commit)
   git commit -m "feat: MVP inicial AuditContabil AI"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/auditcontabil-mvp.git
   git push -u origin main
   ```

### Passo 2: Deploy no Render (100% Grátis)
1. Acesse [render.com](https://render.com) e faça login com seu GitHub.
2. Clique em **New +** e selecione **Web Service**.
3. Escolha o repositório `auditcontabil-mvp`.
4. Preencha as configurações:
   - **Name:** `auditcontabil-ai`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
5. Clique em **Create Web Service**. Em cerca de 2 minutos, você terá um link público HTTPS (ex: `https://auditcontabil-ai.onrender.com`) pronto para apresentar no celular ou notebook!

---

## 🗄️ Banco de Dados Gratuito na Nuvem (Opcional):

Caso queira conectar um PostgreSQL real gerenciado na nuvem:
* Crie uma conta gratuita no [Supabase](https://supabase.com) ou [Neon.tech](https://neon.tech) (500 MB grátis com suporte nativo a RLS).
* Adicione a variável `DATABASE_URL` nas configurações do Render.

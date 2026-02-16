# Manutenção Industrial IA (Streamlit)

Aplicação Streamlit para diagnóstico de manutenção industrial com três abas principais: `Dashboard`, `Novo Diagnóstico` e `Histórico`.

**Objetivo**
- Permitir o registro de um problema em uma máquina.
- Gerar um diagnóstico simulado (mock) com explicação técnica fictícia.
- Manter um histórico local (em memória) dos diagnósticos feitos na sessão.

## Como executar
1. Crie e ative um ambiente virtual (opcional, mas recomendado).
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute o app:
   ```bash
   streamlit run app.py
   ```

## Estrutura do projeto
- `app.py`: aplicação Streamlit com navegação por abas, formulário e histórico.
- `requirements.txt`: dependências necessárias.
- `README.md`: documentação e decisões de design.

## Decisões de design
- **Navegação por abas**: usei `st.tabs` para deixar claro o fluxo principal sem distrações.
- **Formulário simples e direto**: campos essenciais (`nome da máquina` e `descrição do problema`) para reduzir atrito no input.
- **Mock de diagnóstico**: resposta simulada para ilustrar o fluxo sem depender de modelos ou APIs externas.
- **Persistência local**: SQLite (`diagnostics.db`) armazena diagnósticos entre sessões, mantendo o protótipo simples e útil.
- **Dashboard com contexto**: KPIs simples e um resumo do último diagnóstico para orientar o operador.

## Experiência de uso deste agente
- O agente estruturou a aplicação em torno do objetivo principal (diagnóstico rápido e histórico).
- Priorizou simplicidade e clareza: fluxo de navegação evidente e mensagens objetivas.
- Optou por dependências mínimas e código legível para facilitar evolução futura.

## Próximos passos sugeridos
- Integração com modelos de linguagem para diagnóstico real.
- Cadastro de ativos e ordens de serviço.

# Validação da refatoração

- Python 3.11 no Windows: testes de calendário, membros, ausências, grades e mapas.
- Gerados nove mapas do arquivo real `CFSv2.prate.202404.ENSMEAN.fcst.nc`, com primeiro
  mês-alvo abril/2024 e unidade mm/s, em `output/cfsv2/`.
- Maio usa 31 dias, fevereiro considera anos bissextos e dezembro avança o ano.
- Instalação editável do pacote e verificação Ruff executadas.

O usuário informa o mês-alvo e a unidade: não se deduz o mês de inicialização como
validade. Calendários não gregorianos não são convertidos automaticamente.
Anomalias de temperatura em K têm a mesma magnitude numérica em °C.
Arquivos de previsão absoluta não devem ser usados como arquivos de anomalia.


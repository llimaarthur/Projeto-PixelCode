# Design: Validar horário financeiro pela API

O formulário continuará convertendo a data/hora informada para o fuso da
barbearia e enviando o timestamp no payload existente. A comparação prévia com
`datetime.now()` será removida para evitar decisões divergentes entre o
processo Reflex e o Xano.

Os endpoints POST e PATCH continuam aplicando a regra de negócio. Em caso de
data futura, a interface apresentará a mensagem amigável retornada pela API e
não indicará sucesso.

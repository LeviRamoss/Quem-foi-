# Regras do Quem Foi?

Versão oficial das regras, combinada pelo grupo Mentalistas em 14/11/2026.

De 1 a 3 jogadores, no mesmo computador, são detetives numa mansão. Vence quem descobrir **quem foi, com que arma e em que cômodo**.

## O caso

- Cada caso tem **5 suspeitos** e **5 armas**, sorteados da base, e os **6 cômodos** da mansão.
- O crime pode ter acontecido em qualquer um dos 6 cômodos: são 5 × 5 × 6 = **150 combinações**.
- O culpado é sempre um dos personagens do caso, nunca um jogador.
- A IA gera um caso novo a cada partida, e o validador garante que as pistas levam a uma única solução.

## Jogadores e vez

- De 1 a 3 jogadores, no mesmo computador e sem internet.
- Cada jogador é um detetive com um peão: **vermelho**, **azul** ou **verde**. O nome de cada um é digitado no começo.
- Todos jogam o dado no início, e quem tirar o maior número começa. A vez segue em ordem: 1, 2, 3 e volta ao 1.
- No começo de cada vez aparece a tela "Vez de [nome] — clique para começar", para os outros não verem o caderno dele.

## Tabuleiro

O tabuleiro tem **11 × 9 casas**. Os 6 cômodos ocupam 3 × 3 casas cada, com uma porta virada para o corredor do meio. Os detetives começam juntos no **Saguão**, no centro.

```
 B B B · E E E · A A A      B = Biblioteca     E = Escritório
 B B B · E E E · A A A      A = Adega          C = Cozinha
 B B B · E E E · A A A      S = Sala de Estar  J = Jardim
 · ▲ · · · ▲ · · · ▲ ·      ▲ ▼ = porta do cômodo
 · · · ◆ SAGUÃO ◆ · · ·     · = casa de corredor
 · ▼ · · · ▼ · · · ▼ ·      ◆ = saídas do Saguão
 C C C · S S S · J J J
 C C C · S S S · J J J
 C C C · S S S · J J J
```

| Trajeto | Casas | Vezes de jogar, em média |
| --- | --- | --- |
| Saguão até o cômodo mais perto | 4 | 1,6 |
| Cômodo vizinho em cima ou embaixo | 4 | 1,6 |
| Cômodo vizinho ao lado | 6 | 2,2 |
| Canto a canto (o mais longo) | 12 | 3,9 |

Não há passagens secretas.

## Dado e movimento

1. Na sua vez, o jogador joga **1 dado de 6 faces**, com animação do dado caindo.
2. Ele anda **até** o número que saiu: com 6, pode andar de 1 a 6 casas. O jogo acende as casas aonde ele consegue chegar.
3. Só anda para cima, para baixo ou para os lados, nunca na diagonal.
4. Não passa por casa ocupada por outro detetive.
5. **Entrar num cômodo é opcional.** Ele pode entrar mesmo sobrando casas (o movimento acaba ali) ou seguir andando.
6. Cômodo não é atalho: entra e sai pela porta.
7. **Só cabe 1 detetive por cômodo.** Cômodo ocupado fica fechado para os outros.
8. Quem está num cômodo **é obrigado a sair** na vez seguinte. Ninguém passa duas vezes seguidas no mesmo cômodo.

## Dentro do cômodo

Ao entrar num cômodo, na mesma vez, o jogador pode:

1. **Ver as pistas** daquele cômodo. Só ele vê o que encontrou.
2. **Fazer 1 pergunta a 1 suspeito**, à sua escolha. O jogo sorteia 3 perguntas do banco de 10, e ele escolhe uma. A mesma pergunta ao mesmo suspeito tem sempre a mesma resposta.
3. **Fazer 1 palpite** sobre aquele cômodo.

Inocentes sempre falam a verdade. O culpado mente, mas cada mentira dele é contradita por alguma pista.

## Palpite

- Só pode ser feito dentro de um cômodo, e sempre sobre ele: "foi [suspeito], com [arma], aqui na [cômodo]".
- O suspeito e a arma do palpite aparecem no cômodo.
- O jogo mostra, **só para quem palpitou**, o que está certo e o que está errado, item por item. Exemplo: "Sala: certo. Pedro: errado. Cutelo: errado." O caderno marca tudo sozinho.
- Algum item errado: o jogador perde **1 vida**.
- Os três itens certos: aparece **"Parabéns! Caso resolvido"**, todos veem a solução e começa um caso novo.

## Cartada Final

- Pode ser feita de **qualquer lugar**, na sua vez, uma vez por caso.
- O jogador diz quem foi, com que arma e em que cômodo, tudo de uma vez.
- Acertou: vence o caso. Errou: está **eliminado**, mesmo que ainda tenha vidas.

## Vidas, eliminação e fim do caso

1. Cada jogador começa o caso com **5 vidas**.
2. Fica sem vidas ou erra a Cartada Final: está eliminado. Os outros continuam.
3. O caso termina quando alguém acerta (palpite ou Cartada Final) ou quando todos são eliminados.
4. A tela "Caso encerrado" revela a solução e as pistas que levavam a ela.
5. O próximo caso já está pronto e começa na hora.

## Pontuação

| Situação | Pontos |
| --- | --- |
| Caso resolvido | 100 |
| Cada vida restante | +20 |
| Vitória pela Cartada Final | +50 |

Só quem resolve o caso ganha os pontos. Os pontos de cada jogador somam de um caso para o outro.

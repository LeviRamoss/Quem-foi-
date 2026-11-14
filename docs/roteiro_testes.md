# Roteiro de testes (QA)

Para quem testa o jogo: Ana Luiza e Alisson. Marquem cada item e anotem o que der errado (o que fez, o que esperava, o que aconteceu e, se der, um print).

## Como abrir o jogo

```bash
pip install pygame-ce
python jogo/main.py
```

Para rodar os testes automáticos das regras: `python -m unittest discover testes`

## Checklist

### Início
- [ ] Dá para escolher 1, 2 ou 3 jogadores.
- [ ] Dá para clicar num nome e digitar outro, com acento.
- [ ] A tela "Quem começa?" mostra os dados de cada um e a ordem certa (maior número primeiro).

### Vez do jogador
- [ ] A tela "Vez de [nome]" aparece antes de cada vez e esconde o caderno dos outros.
- [ ] A vez segue a ordem 1, 2, 3 e volta ao 1.
- [ ] O dado gira e cai num número de 1 a 6.
- [ ] As casas acesas são só as que dá para alcançar com o número do dado.
- [ ] O peão não anda na diagonal nem passa por cima de outro peão.
- [ ] Todos os 6 cômodos ficam a 5 passos do Saguão.

### Cômodos
- [ ] Entrar num cômodo é opcional: dá para passar reto.
- [ ] Ao entrar, aparecem as 2 pistas daquele cômodo.
- [ ] Cômodo com outro detetive dentro não acende.
- [ ] Na vez seguinte, quem está no cômodo é obrigado a sair (o mesmo cômodo não acende).
- [ ] Interrogatório: 3 perguntas sorteadas, só 1 pergunta por vez, a qualquer suspeito.

### Palpite e Cartada Final
- [ ] O palpite só aparece dentro de um cômodo e usa aquele cômodo.
- [ ] O resultado mostra item por item o que está certo e errado.
- [ ] Palpite errado tira 1 vida (coração vazio no topo).
- [ ] Com 0 vidas, o jogador é eliminado e some do tabuleiro.
- [ ] Palpite certo mostra "Parabéns! Caso resolvido".
- [ ] A Cartada Final funciona de qualquer lugar; errada elimina.
- [ ] Se todos forem eliminados, aparece "Caso encerrado" com a solução.

### Caso de exemplo
- [ ] Solução: Otávio Brandão, com Veneno, na Biblioteca.
- [ ] O caso dá para resolver só com as pistas dos 6 cômodos.

## Onde anotar os problemas

Abram uma issue no GitHub (aba Issues) com o título começando por `[QA]`.

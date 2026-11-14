---
id: g02
tipo: guia
titulo: Guia para escrever pistas
ficticio: true
---

# Guia para escrever pistas

O caso tem 12 pistas, 2 em cada um dos 6 cômodos. Só as pistas, juntas, precisam levar a uma única solução entre as 150 combinações.

## Tipos de fato

- `nao_e`: um item não é a resposta. Ex.: "A faca está limpa e no lugar" → a faca não é a arma.
- `estava_em`: um suspeito estava num cômodo na hora do crime. Se esse cômodo não é o do crime, ele não é o culpado.
- `nao_esteve_em`: um suspeito não esteve num cômodo na hora do crime.
- Pista de clima, sem fato: ajuda a imaginar a cena, mas não prova nada (ex.: o copo com cheiro amargo).

## Como montar as eliminações

- Elimine os 5 cômodos que não são o do crime, as 4 armas erradas e os 4 suspeitos inocentes.
- Um jeito simples: cada cômodo errado tem uma pista `nao_e` sobre ele mesmo; as armas erradas aparecem intactas no lugar delas; e cada inocente tem um álibi (`estava_em`) num cômodo que não é o do crime.
- Cada pista fica no cômodo onde faz sentido encontrá-la: a faca na cozinha, o revólver no escritório.
- No cômodo do crime, pelo menos uma pista liga o culpado ao local (`estava_em`), sem dizer que ele é o culpado.

## Depoimentos

- Os inocentes só dizem a verdade. Quando a resposta for um álibi, use o mesmo fato da pista.
- O culpado mente pelo menos uma vez, e cada mentira tem um fato que uma pista contradiz. Ex.: ele diz que estava no jardim (`estava_em` jardim), e a pista da biblioteca mostra que ele estava lá (`estava_em` biblioteca).
- Respostas de opinião ("De quem você desconfia?") podem ter `fato: null`. Um inocente pode desconfiar da pessoa errada.

## Proibido

- Citar personagem, arma ou cômodo fora da lista do caso.
- Pista que entregue a resposta inteira, como "foi o médico".
- Contradição entre duas pistas.

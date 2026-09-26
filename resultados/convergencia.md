* A reconvergência tem duas etapas: detectar a falha e encontrar a alternativa. Os dois tipos de teste separam essas etapas.

* Cabo puxado (detecção instantânea): só o RIP demorou. Os três souberam da falha na hora, porque a interface caiu. A diferença está no que cada um tinha guardado:

    * O OSPF tem o mapa completo da rede; recalculou o caminho na hora.
    * O BGP guarda as rotas recebidas de todos os vizinhos, inclusive as não usadas; o R3 já tinha a rota via R4 e só trocou.
    * O RIP guarda só a melhor rota. Quando ela sumiu, o R3 ficou sem alternativa e teve que esperar a próxima atualização periódica do R4, que levou 28 s. É uma limitação típica dos protocolos de vetor de distância.

* Falha silenciosa (detecção por temporizador): a ordem segue os temporizadores. Sem aviso de interface, cada protocolo só percebe quando para de ouvir o vizinho: o OSPF em 40 s, o BGP e o RIP em 180 s. Os resultados medidos seguem exatamente essa ordem. O RIP ainda soma a espera por uma atualização do R4 depois de descartar a rota, por isso ficou por último.

* O OSPF foi o mais rápido nos dois cenários, o que explica por que ele é o protocolo interno mais usado em redes corporativas. Já o BGP foi desenhado para a internet, onde estabilidade importa mais que velocidade: um temporizador longo evita que uma oscilação momentânea gere uma onda de atualizações entre milhares de ASs.

* Um ponto para a apresentação: esses tempos são os padrões, e todos são ajustáveis. Na prática, redes reais reduzem os temporizadores ou usam um protocolo auxiliar chamado BFD, que detecta falhas silenciosas em menos de um segundo e avisa o OSPF ou o BGP. Mencionar isso mostra que você entende que o resultado depende da configuração, não só do protocolo.

Tráfego de controle durante a falha

Comparando com o regime normal da métrica 3 (proporcional ao mesmo tempo de janela):

	Normal (35 s)	Durante a falha de link (35 s)
    OSPF	~42 pacotes, ~2,9 KB	80 pacotes, 7,2 KB
    RIP	~15 pacotes, ~3,5 KB	28 pacotes, 5,1 KB
    BGP	~10 pacotes, ~0,7 KB	30 pacotes, 2,0 KB

* Os três geraram uma rajada de mensagens para anunciar a mudança, mas o BGP continuou sendo o que menos trafegou em bytes, mesmo reagindo à falha.

* Uma limitação honesta: cada teste foi rodado uma vez. Na falha silenciosa, o tempo exato depende de em que momento do ciclo de hellos ou keepalives a falha aconteceu (por isso as faixas previstas são intervalos). Se sobrar tempo no domingo, rodar mais uma ou duas vezes e fazer a média deixa o resultado mais sólido; se não, basta mencionar isso na apresentação.
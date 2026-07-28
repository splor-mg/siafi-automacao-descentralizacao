import time


def aprovacao(em, data_row):
    ## Verifica se é anulação ou aprovação e preencche 03-1 para aprovação e 04-1 para anulação
    # Movimentação de tela
    em.fill_field(21, 19, '01', 2)
    em.fill_field(21, 41, '1', 1)
    em.send_enter()
    em.wait_for_field()

    while True:        
        ## Verifica se é global ou amarrado e preenche os campos correspondentes
        if data_row['tipo'] == 'Global':
            #Aprovação/Anulação GLOBAL
            em.fill_field(10, 53, 'x', 1) # global
            em.fill_field(12, 53, data_row['unidade_orcamentaria'], 4) ## digitar a UO
            em.fill_field(13, 53, data_row['iag'], 1) # IAG
            em.fill_field(13, 63, f"{data_row['fonte']}{data_row['procedencia']}", 3) # fonte e procendencia
            em.fill_field(14, 53, 'n', 1) # digita um não para DEA 
            em.fill_field(15, 53, data_row['ue'], 7) # UE beneficiada
            em.fill_field(17, 46, data_row['acao'], 4) # acao
            em.fill_field(17, 51, '0001', 4)
            em.fill_field(18, 46, data_row['categoria'], 1) # categoria
            em.fill_field(18, 48, data_row['grupo'], 1) # grupo
            em.fill_field(18, 50, data_row['modalidade'], 2) # modalidade
            em.fill_field(18, 53, data_row['elemento'], 2) # elemento
            if data_row['procedencia'] == '2':
                em.fill_field(20, 46, data_row['uo_financiadora'], 4) # uo_financiadora
            em.send_enter()
            em.wait_for_field()
        elif data_row['tipo'] == 'Amarrado':
            #Aprovação/Anulação AMARRADO
            em.fill_field(11, 53, 'x', 1) # global
            em.fill_field(12, 53, data_row['unidade_orcamentaria'], 4) ## digitar a UO
            em.fill_field(13, 53, data_row['iag'], 1) # IAG
            em.fill_field(13, 63, f"{data_row['fonte']}{data_row['procedencia']}", 3) # fonte e procendencia
            em.fill_field(14, 53, 'n', 1) # digita um não para DEA 
            em.fill_field(15, 53, data_row['ue'], 7) # UE beneficiada
            em.fill_field(17, 46, data_row['acao'], 4) # acao
            em.fill_field(17, 51, '0001', 4)
            em.fill_field(18, 46, data_row['categoria'], 1) # categoria
            em.fill_field(18, 48, data_row['grupo'], 1) # grupo
            em.fill_field(18, 50, data_row['modalidade'], 2) # modalidade
            em.fill_field(18, 53, data_row['elemento'], 2) # elemento
            em.fill_field(19, 46, data_row['item'], 2) # item
            if data_row['procedencia'] == '2':
                em.fill_field(20, 46, data_row['uo_financiadora'], 4) # uo_financiadora
            em.send_enter()
            em.wait_for_field()
        
        retorno = em.string_get(1, 1, 80).strip()

        if (
            retorno.startswith("E90 - SALDO ZERADO NA CONTA")
            or retorno == "0139- PROJ/ATIV OU FONTE/PROC./IAG INEXISTENTE PARA UO"
            or retorno == "0101- NATUREZA DESPESA INEXISTENTE(S)."
            or retorno == "0101- GRUPO DESPESA INEXISTENTE(S)."
            or retorno == "0139- PROGRAMA DE TRABALHO NAO ENCONTRADO PARA GM/FP."
            or retorno == "0109-INFORME NATUREZA DE DESPESA COMPLETA."
            ):
                ##interrompe o fluxo e segue para a proxima etapa, para evitar erros de preenchimento
                break

        #digitar as informações das ações e valores...
        time.sleep(1)  # garante teclado liberado antes de escrever (evita "Keyboard locked")
        em.fill_field(17, 63, str(data_row['valor']), 15) # valor
        time.sleep(1)
        em.send_enter()
        em.wait_for_field()
        retorno = em.string_get(1, 1, 80).strip()
        if retorno in (
            "0139- VALOR A APROVAR MAIOR QUE SALDO DISPONIVEL NO PROJ/ATIV.",
            "0139- PROJ/ATIV OU FONTE/PROC./IAG INEXISTENTE PARA UO", 
            "SALDO DE CREDITO ORCAMENTARIO A APROVAR POR PROJ/ATIV ZERADO.",
            "0139- VALOR A DESCENTRALIZAR MAIOR QUE SALDO APROVADO.",
        ):
            ##interrompe o fluxo e segue para a proxima etapa, para evitar erros de preenchimento
            break
        else:
            time.sleep(1)
            em.fill_field(11, 11, 'Remanejamento realizado conforme solicitado', 60) # ação
            em.send_enter()
            em.wait_for_field()
            em.send_pf(5)  # envia F5
            em.wait_for_field()
            em.send_pf(5)  # envia F5
            em.wait_for_field()
            time.sleep(1)
            retorno = em.string_get(1, 1, 80).strip()
            break

    print(f"SIAFI retornou: {retorno}")
    em.send_pf(3)  # envia F3
    em.wait_for_field()

    return retorno
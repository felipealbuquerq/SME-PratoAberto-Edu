# -*- coding: utf-8 -*-
import io
import json
import pprint
from datetime import date

from celery.utils.log import get_task_logger

import api_client as api

logger = get_task_logger(__name__)

# carrega workflows
with io.open('conf/workflowsconfig.json', 'r', encoding='utf-8') as f:
    workflows = json.load(f)
    # constroi dicionario com a mensagem como chave
    fluxos, mensagens = workflows['fluxos'], workflows['mensagens']
    # menu principal de botoes
    menu_principal = [a for (a, b) in sorted([x for x in fluxos.items() if x[1]['menu']],
                                             key=lambda x: x[1].get('ordem'))]
    # menu principal de botoes para subscritos
    menu_subscritos = menu_principal[:]
    menu_subscritos[-1] = 'Cancelar notificações'


def _format(text, args=list()):
    return '\n\n'.join(text).format(*args)


# processadores
# @params: chat, db (Opcional)
# @return: resposta, botoes
def process_cardapio(chat, db=None):
    # o que é chat? um json grande talvez? um payload?
    # quando essa vergonha é chamada?
    escola, idade, data = chat['valores']
    # busca cardapio
    try:
        logger.debug('chat: {}\n chat valores {}\n data demon {}'.format(chat, chat['valores'], data))
        cardapio = api.get_cardapio(escola['_id'], idade, data)
    except:
        # erro na API
        return _format(mensagens['erro_api']['texto']), menu_principal

    # processa resposta
    if len(cardapio) > 0:
        cardapio = cardapio.pop()
        cardapio_str = ['{}:\n{}'.format(k, ', '.join(v)) for (k, v) in sorted(cardapio['cardapio'].items())]
    else:
        cardapio_str = ['Ops! Não encontramos nenhuma informação de cardápio para este dia.']

    resposta = fluxos[chat['fluxo']]['resposta']
    args = (escola['nome'], idade, _format(cardapio_str))
    return _format(resposta, args), None

def process_notificacao(chat, db=None):
    # configura subscricao
    db.users.update_one(
        { '_id': chat['chat_id'] },
        { '$set': { 'subscription': chat['valores'] } }
    )
    return None, menu_subscritos

def process_cancelar_notificacao(chat, db=None):
    # apaga subscricao
    db.users.update_one(
        { '_id': chat['chat_id'] },
        { '$unset': { 'subscription': True  } }
    )
    return None, menu_principal


# construtores de argumentos
# @params: chat, texto da mensagem
# @return: chat
def process_arguments(chat, texto):
    logger.debug('in:process_arguments: {}'.format(texto))
    logger.debug(pprint.pformat(chat))

    _arg_corrente = chat['arg_corrente']

    msg = mensagens.get(_arg_corrente, dict())
    chat.update({
        'resposta': _format(msg.get('texto')),
        'botoes': msg.get('opcoes')
    })

    try:
        _fn = getters[_arg_corrente]
        logger.debug('dispatching to: {}'.format(_fn))
        chat = _fn(chat, texto)
    except KeyError:
        if texto:
            chat = _update_arg(chat, texto)

    logger.debug('out:process_arguments')
    logger.debug(pprint.pformat(chat))
    return chat

def _update_arg(chat, texto):
    # atualiza argumentos
    arg_corrente = chat['arg_corrente']
    logger.debug('updating arg: {} to {}'.format(arg_corrente, texto))

    args = chat['argumentos']
    valores = chat['valores']
    valores[args.index(arg_corrente)] = texto
    # define proximo argumento
    chat.update({
            # 'valores': valores,
            'arg_corrente': args[valores.index(None)],
            'resposta': None,
            'sub_status': None
        })
    # quando nao houver mais argumentos a ser preenchidos,
    # args[valores.index(None)] lancara ValueError
    return chat

def _get_escola(chat, texto):
    # procura pela escola
    _arg_status = chat.get('sub_status', 0)
    if not _arg_status or texto == 'Nenhuma das opções':
        chat['sub_status'] = 1
    else:
        resposta, botoes = None, None
        try:
            escolas = api.find_escolas(texto)
        except:
            # erro na API
            chat.update({
                'resposta': _format(mensagens['erro_api']['texto']),
                'botoes': menu_principal,
                'status': 'erro'
            })
            return chat

        if len(escolas) == 0:
            msg = mensagens['escola_invalida']
            chat['resposta'] = _format(msg['texto'])
        else:
            botoes = [c['nome'] for c in escolas]
            if texto in botoes:
                escola = escolas[botoes.index(texto)]
                chat = _update_arg(chat, escola)
                # obtem dados da escola para uso futuro
                try:
                    escola = api.get_escola(escola['_id'])
                    chat['escola'] = escola
                except:
                    # erro na API
                    chat.update({
                        'resposta': _format(mensagens['erro_api']['texto']),
                        'botoes': menu_principal,
                        'status': 'erro'
                    })
                    return chat
            else:
                msg = mensagens['escola_confirm']
                chat.update({
                    'resposta': _format(msg['texto']),
                    'botoes': sorted(botoes) + ['Nenhuma das opções']
                })

    return chat

def _get_idade(chat, texto):
    if texto:
        chat = _update_arg(chat, texto)
    else:
        escola = chat['escola']
        botoes = sorted([c for c in escola['idades']])
        if len(botoes) == 1:
            chat = _update_arg(chat, botoes[0])
        else:
            chat['botoes'] = botoes

    return chat

def _get_data(chat, texto):
    if texto:
        _hoje = date.today().strftime('%Y%m%d')
        data = int(_hoje) + 1*(texto=='Amanhã') - 1*(texto=='Ontem')
        chat = _update_arg(chat, data)
    return chat

def _get_data_cardapio(chat, texto):
    return _get_data(chat, texto)

def _get_data_avaliacao(chat, texto):
    return _get_data(chat, texto)

def _get_refeicao_preferida(chat, texto):
    if texto:
        chat = _update_arg(chat, texto)
    else:
        escola = chat['escola']
        chat['botoes'] = sorted([c for c in escola['refeicoes']])

    return chat

def _get_comentario_confirm(chat, texto):
    _arg_status = chat.get('sub_status', 0)
    if not _arg_status:
        chat['sub_status'] = 1
    elif texto == 'Sim':
        msg = mensagens['comentario']
        chat.update({
            'resposta': _format(msg['texto']),
            'botoes': None
        })
    else:
        chat = _update_arg(chat, texto)
    return chat


processors = {
    name.replace('process_', ''): fn
    for name, fn in locals().items()
    if name.startswith('process_')
}

getters = {
    name.replace('_get_', ''): fn
    for name, fn in locals().items()
    if name.startswith('_get_')
}

if __name__ == '__main__':
    # essa maluquice poderia ter sido resolvida com getattr
    print(processors)
    print(getters)

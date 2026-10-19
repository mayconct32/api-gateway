"""Camada de acesso a dados.

Cada repositório é uma faixa fina sobre a Session do SQLAlchemy.
Não há interface abstrata aqui de propósito: só existe uma
implementação concreta (SQLAlchemy). A separação por Protocol existe
apenas onde há implementações reais alternativas — os gateways de
pagamento em app/payment_providers. Se um dia a persistência mudar,
a interface dos repositórios é a própria assinatura destes métodos.
"""

"""Camada de acesso a dados.

Cada repositório é uma faixa fina sobre a Session do SQLAlchemy. Os
contratos das operações ficam declarados em interfaces estruturais
(Protocol) em repositories/interfaces.py — e os serviços dependem
apenas da interface, nunca da implementação concreta. Hoje só existe
uma implementação por contrato (SQLAlchemy); os Protocol permitem
alternar a persistência ou injetar fakes em testes sem tocar nos
serviços.
"""

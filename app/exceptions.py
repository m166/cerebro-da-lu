"""Erros de domínio.

Os services levantam essas exceções; os routers traduzem pra HTTP e a
camada de IA traduz pra `{"erro": ...}` (formato que o modelo entende).
"""


class ErroDeDominio(Exception):
    """Base de todos os erros de negócio previsíveis."""


class ProdutoNaoEncontrado(ErroDeDominio):
    def __init__(self, produto_id: int):
        super().__init__(f"Produto {produto_id} não encontrado.")


class PedidoNaoEncontrado(ErroDeDominio):
    def __init__(self, pedido_id: int):
        super().__init__(f"Pedido {pedido_id} não encontrado.")


class EstoqueInsuficiente(ErroDeDominio):
    def __init__(self, nome: str, disponivel: int):
        super().__init__(f"Estoque insuficiente pra {nome} (disponível: {disponivel}).")


class ComparacaoInvalida(ErroDeDominio):
    def __init__(self):
        super().__init__("Preciso de pelo menos 2 produtos válidos pra comparar.")


class SemProdutosDisponiveis(ErroDeDominio):
    def __init__(self):
        super().__init__("Nenhum produto disponível pra esses critérios.")

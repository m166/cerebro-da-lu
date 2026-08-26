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


class CampoDePerfilInvalido(ErroDeDominio):
    def __init__(self, campo: str, aceitos):
        super().__init__(
            f"Não sei guardar '{campo}'. Campos aceitos: {', '.join(aceitos)}."
        )


class CampoDeMemoriaInvalido(ErroDeDominio):
    def __init__(self, campo: str, aceitos):
        super().__init__(
            f"Não sei anotar '{campo}'. Campos aceitos: {', '.join(aceitos)}."
        )


class CupomAindaNaoCabe(ErroDeDominio):
    """Ainda não é hora de oferecer desconto.

    Não é erro do sistema nem do cliente: é a regra de negócio dizendo que a
    conversa não chegou no ponto. A mensagem carrega o motivo pra que o
    modelo entenda que deve continuar vendendo em vez de insistir no cupom.
    """

    def __init__(self, motivo: str):
        super().__init__(f"Cupom não liberado: {motivo}.")


class CupomInvalido(ErroDeDominio):
    def __init__(self, motivo: str):
        super().__init__(f"Cupom inválido: {motivo}.")


class NotaInvalida(ErroDeDominio):
    def __init__(self, nota, minimo, maximo):
        super().__init__(f"Nota {nota} fora da escala de {minimo} a {maximo}.")


class SemProdutosDisponiveis(ErroDeDominio):
    def __init__(self):
        super().__init__("Nenhum produto disponível pra esses critérios.")

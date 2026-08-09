"""Formatação do relatório de avaliação."""

from dataclasses import dataclass

LARGURA = 78


@dataclass
class Metrica:
    nome: str
    valor: float
    total: int
    minimo: float
    e_media: bool = False

    @property
    def taxa(self) -> float:
        return self.valor / self.total if self.total else 0.0

    @property
    def passou(self) -> bool:
        return self.taxa >= self.minimo

    def formatar(self) -> str:
        marca = "ok  " if self.passou else "FALHA"
        if self.e_media:
            medida = f"{self.taxa:.3f}"
        else:
            medida = f"{int(self.valor):>3}/{self.total:<3} ({self.taxa:5.1%})"
        return f"  [{marca}] {self.nome:<26} {medida}   mínimo {self.minimo:.0%}"


def secao(titulo: str, subtitulo: str = "") -> None:
    print()
    print("=" * LARGURA)
    print(titulo + (f"  ({subtitulo})" if subtitulo else ""))
    print("=" * LARGURA)


def linha_erro(entrada: str, esperado: str, obtido: str) -> str:
    return f"  - {entrada[:52]!r}\n      esperado: {esperado}\n      obtido:   {obtido}"


def imprimir_erros(erros) -> None:
    if not erros:
        return
    print(f"\n  {len(erros)} caso(s) fora do esperado:")
    for erro in erros:
        print(erro)


def imprimir_resumo(metricas) -> bool:
    secao("RESUMO")
    for metrica in metricas:
        print(metrica.formatar())

    falhas = [m for m in metricas if not m.passou]
    print()
    if falhas:
        print(f"  {len(falhas)} métrica(s) abaixo do mínimo: " + ", ".join(m.nome for m in falhas))
    else:
        print("  todas as métricas dentro do mínimo")
    return not falhas

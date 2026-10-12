from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from sqlalchemy.sql import func

from app.database import Base


class Venda(Base):

    __tablename__ = "vendas"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    cliente_id = Column(
        Integer,
        ForeignKey(
            "clientes.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )


    usuario_id = Column(
        Integer,
        ForeignKey(
            "usuarios.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )


    desconto_percentual = Column(
        Float,
        nullable=False,
        default=0.0
    )


    total_bruto = Column(
        Float,
        nullable=False,
        default=0.0
    )


    total_liquido = Column(
        Float,
        nullable=False,
        default=0.0
    )


    observacao = Column(
        String(255),
        nullable=True
    )


    criado_em = Column(
        DateTime,
        server_default=func.now()
    )


    cliente = relationship(
        "Cliente",
        back_populates="vendas"
    )


    usuario = relationship(
        "Usuario",
        backref="vendas"
    )


    itens = relationship(
        "ItemVenda",
        back_populates="venda",
        cascade="all, delete-orphan"
    )


    pagamentos = relationship(
        "Pagamento",
        back_populates="venda",
        cascade="all, delete-orphan"
    )


    @property
    def desconto_valor(self):

        return (
            self.total_bruto
            -
            self.total_liquido
        )


    def __repr__(self):

        return (
            f"<Venda "
            f"id={self.id} "
            f"total={self.total_liquido}>"
        )


class ItemVenda(Base):

    __tablename__ = "itens_venda"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    venda_id = Column(
        Integer,
        ForeignKey(
            "vendas.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )


    produto_id = Column(
        Integer,
        ForeignKey(
            "produtos.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )


    produto_nome = Column(
        String(150),
        nullable=False
    )


    quantidade = Column(
        Integer,
        nullable=False
    )


    preco_unitario = Column(
        Float,
        nullable=False
    )


    venda = relationship(
        "Venda",
        back_populates="itens"
    )


    produto = relationship(
        "Produto",
        backref="itens_venda"
    )


    @property
    def subtotal(self):

        return (
            self.quantidade
            *
            self.preco_unitario
        )
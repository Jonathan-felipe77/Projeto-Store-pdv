from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True
    )

    venda_id = Column(
        Integer,
        ForeignKey("vendas.id", ondelete="CASCADE"),
        nullable=False
    )

    forma_pagamento = Column(
        String(30),
        nullable=False
    )

    valor = Column(
        Float,
        nullable=False,
        default=0.0
    )

    venda = relationship(
        "Venda",
        backref="pagamentos"
    )

    def __repr__(self):
        return (
            f"<Pagamento id={self.id} "
            f"venda_id={self.venda_id} "
            f"forma={self.forma_pagamento} "
            f"valor={self.valor}>"
        )
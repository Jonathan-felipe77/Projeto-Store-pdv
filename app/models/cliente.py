from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Cliente(Base):

    __tablename__ = "clientes"

    # ============================================================
    # ID
    # ============================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # ============================================================
    # NOME
    # ============================================================

    nome = Column(
        String(150),
        nullable=False
    )

    # ============================================================
    # MATRÍCULA
    # ============================================================

    matricula = Column(
        String(100),
        unique=True,
        nullable=True
    )

    # ============================================================
    # TELEFONE
    # ============================================================

    telefone = Column(
        String(30),
        nullable=True
    )

    # ============================================================
    # ASSOCIADO
    # ============================================================

    is_associado = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # ============================================================
    # ATIVO
    # ============================================================

    ativo = Column(
        Boolean,
        default=True,
        nullable=False
    )

    # ============================================================
    # DESCONTO INDIVIDUAL
    # ============================================================
    #
    # 0    = sem desconto
    # 5    = 5%
    # 10   = 10%
    # 15   = 15%
    # 20   = 20%
    #
    # ============================================================

    desconto_percentual = Column(
        Float,
        default=0.0,
        nullable=False
    )

    # ============================================================
    # DATA DE CRIAÇÃO
    # ============================================================

    criado_em = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    # ============================================================
    # RELACIONAMENTO
    # ============================================================

    vendas = relationship(
        "Venda",
        back_populates="cliente"
    )
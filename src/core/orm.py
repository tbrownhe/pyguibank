from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class AccountTypes(Base):
    __tablename__ = "AccountTypes"
    AccountTypeID = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    AccountType = Column(String, unique=True, nullable=True)
    AssetType = Column(String, nullable=True)

    accounts = relationship("Account", back_populates="account_type")


class Accounts(Base):
    __tablename__ = "Accounts"
    AccountID = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    AccountName = Column(String, nullable=False, unique=True)
    AccountTypeID = Column(Integer, ForeignKey("AccountTypes.AccountTypeID"))
    Company = Column(String)
    Description = Column(Text)

    account_type = relationship("AccountType", back_populates="accounts")
    account_numbers = relationship("AccountNumber", back_populates="account")
    statements = relationship("Statement", back_populates="account")
    transactions = relationship("Transaction", back_populates="account")


class AccountNumbers(Base):
    __tablename__ = "AccountNumbers"
    AccountNumberID = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    AccountID = Column(Integer, ForeignKey("Accounts.AccountID"))
    AccountNumber = Column(String, unique=True)

    account = relationship("Account", back_populates="account_numbers")


class StatementTypes(Base):
    __tablename__ = "StatementTypes"
    StatementTypeID = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    AccountTypeID = Column(Integer, ForeignKey("AccountTypes.AccountTypeID"))
    Company = Column(String)
    Description = Column(Text)
    Extension = Column(String)
    SearchString = Column(String, nullable=False)
    Parser = Column(String, nullable=False)
    EntryPoint = Column(String, nullable=False)

    account_type = relationship("AccountType", back_populates="statement_types")


class Statements(Base):
    __tablename__ = "Statements"
    StatementID = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    StatementTypeID = Column(Integer, ForeignKey("StatementTypes.StatementTypeID"))
    AccountID = Column(Integer, ForeignKey("Accounts.AccountID"))
    ImportDate = Column(DateTime)
    StartDate = Column(DateTime)
    EndDate = Column(DateTime)
    StartBalance = Column(Numeric)
    EndBalance = Column(Numeric)
    TransactionCount = Column(Integer)
    Filename = Column(String)
    MD5 = Column(String)

    account = relationship("Account", back_populates="statements")
    statement_type = relationship("StatementType")
    transactions = relationship("Transaction", back_populates="statement")


class Transactions(Base):
    __tablename__ = "Transactions"
    TransactionID = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    StatementID = Column(Integer, ForeignKey("Statements.StatementID"))
    AccountID = Column(Integer, ForeignKey("Accounts.AccountID"))
    Date = Column(DateTime)
    Amount = Column(Float)
    Balance = Column(Float)
    Description = Column(String)
    MD5 = Column(String, unique=True)
    Category = Column(String, default="Uncategorized")
    Verified = Column(Integer, default=0)
    ConfidenceScore = Column(Numeric)

    statement = relationship("Statement", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")


class CardNumbers(Base):
    __tablename__ = "CardNumbers"
    CardID = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    AccountID = Column(Integer, ForeignKey("Accounts.AccountID"))
    CardNumber = Column(String)
    LastFour = Column(String, unique=True)

    account = relationship("Account")


class Shoppings(Base):
    __tablename__ = "Shopping"
    ItemID = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    AccountID = Column(Integer, ForeignKey("Accounts.AccountID"))
    StatementID = Column(Integer, ForeignKey("Statements.StatementID"))
    CardID = Column(Integer, ForeignKey("CardNumbers.CardID"))
    OrderID = Column(String)
    Date = Column(DateTime)
    Amount = Column(Float)
    Description = Column(String)
    MD5 = Column(String, unique=True)

    account = relationship("Account")
    statement = relationship("Statement")
    card = relationship("CardNumber")


# Create Engine and Session
def create_database(db_path: Path) -> sessionmaker:
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

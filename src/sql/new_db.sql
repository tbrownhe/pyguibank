--SQLite
CREATE TABLE "AccountTypes" (
	"AccountTypeID"	INTEGER NOT NULL UNIQUE,
	"AccountType"	TEXT UNIQUE,
	"AssetType"	TEXT,
	PRIMARY KEY("AccountTypeID" AUTOINCREMENT)
);

CREATE TABLE "Accounts" (
	"AccountID"	INTEGER UNIQUE,
	"AccountName"	TEXT NOT NULL UNIQUE,
	"AccountTypeID"	INTEGER,
	"Company"	TEXT,
	"Description"	TEXT,
	PRIMARY KEY("AccountID" AUTOINCREMENT),
	FOREIGN KEY("AccountTypeID") REFERENCES "AccountTypes"("AccountTypeID")
);

CREATE TABLE "AccountNumbers" (
	"AccountNumberID"	INTEGER UNIQUE,
	"AccountID"	INTEGER,
	"AccountNumber"	TEXT UNIQUE,
	PRIMARY KEY("AccountNumberID" AUTOINCREMENT),
	FOREIGN KEY("AccountID") REFERENCES "Accounts"("AccountID")
);

CREATE TABLE "StatementTypes" (
	"StatementTypeID"	INTEGER UNIQUE,
	"AccountTypeID"	INTEGER,
	"Company"	TEXT,
	"Description"	TEXT,
	"Extension"	TEXT,
	"SearchString"	TEXT,
	"Parser"	INTEGER,
	PRIMARY KEY("StatementTypeID" AUTOINCREMENT),
	FOREIGN KEY("AccountTypeID") REFERENCES "AccountTypes"("AccountTypeID")
);

CREATE TABLE "Statements" (
	"StatementID"	INTEGER UNIQUE,
	"StatementTypeID"	INTEGER,
	"AccountID"	INTEGER,
	"StartDate"	TEXT,
	"EndDate"	TEXT,
	"ImportDate"	TEXT,
	"Filename"	TEXT,
	"MD5"	TEXT UNIQUE,
	PRIMARY KEY("StatementID" AUTOINCREMENT),
	FOREIGN KEY("StatementTypeID") REFERENCES "StatementTypes"("StatementTypeID"),
	FOREIGN KEY("AccountID") REFERENCES "Accounts"("AccountID")
);

CREATE TABLE "Transactions" (
	"TransactionID"	INTEGER,
	"StatementID"	INTEGER,
	"AccountID"	INTEGER,
	"Date"	TEXT,
	"Amount"	REAL,
	"Balance"	REAL,
	"Description"	TEXT,
	"MD5"	TEXT UNIQUE,
	"Category"	TEXT DEFAULT 'Uncategorized',
	"Verified"	INTEGER DEFAULT 0,
	PRIMARY KEY("TransactionID" AUTOINCREMENT),
	FOREIGN KEY("StatementID") REFERENCES "Statements"("StatementID"),
	FOREIGN KEY("AccountID") REFERENCES "Accounts"("AccountID")
);

CREATE TABLE "CardNumbers" (
	"CardID"	INTEGER UNIQUE,
	"AccountID"	INTEGER,
	"CardNumber"	TEXT,
	"LastFour"	TEXT UNIQUE,
	PRIMARY KEY("CardID" AUTOINCREMENT),
	FOREIGN KEY("AccountID") REFERENCES "Accounts"("AccountID")
);

CREATE TABLE "Shopping" (
	"ItemID"	INTEGER UNIQUE,
	"AccountID"	INTEGER,
	"StatementID"	INTEGER,
	"CardID"	INTEGER,
	"OrderID"	TEXT,
	"Date"	TEXT,
	"Amount"	REAL,
	"Description"	TEXT,
	"MD5"	TEXT UNIQUE,
	PRIMARY KEY("ItemID" AUTOINCREMENT),
	FOREIGN KEY("AccountID") REFERENCES "Accounts"("AccountID"),
	FOREIGN KEY("CardID") REFERENCES "CardNumbers"("CardID"),
	FOREIGN KEY("StatementID") REFERENCES "Statements"("StatementID")
);

CREATE INDEX "idx_transactions_accountid " ON "Transactions" (
	"AccountID"
);
CREATE INDEX "idx_transactions_date" ON "Transactions" (
	"Date"
);
CREATE INDEX "idx_transactions_transactionid" ON "Transactions" (
	"TransactionID"
);

-- Prepopulate AccountTypes
INSERT INTO "AccountTypes" ("AccountType", "AssetType")
VALUES
	('Checking', 'Asset'),
	('Savings', 'Asset'),
	('Credit Card', 'Debt'),
	('401k', 'Asset'),
	('HSA', 'Asset'),
	('Loan', 'Debt'),
	('Shopping', 'Spending');

-- Prepopulate StatementTypes with statement recognition values
INSERT INTO "StatementTypes" ("Company", "AccountTypeID", "Description", "Extension", "SearchString", "Parser") 
VALUES 
	('Oregon Community Credit Union', '1', 'Personal', '.pdf', 'oregon community credit union&&member number', 'occubank'),
	('Oregon Community Credit Union', '3', 'OCCU', '.pdf', 'www.myoccu.org&&card services', 'occucc'),
	('Oregon Community Credit Union', '6', 'Auto', '.csv', '254779', 'occuauto'),
	('Wells Fargo', '1', 'Personal', '.pdf', 'wells fargo everyday checking', 'wfper'),
	('Wells Fargo', '2', 'Personal', '.pdf', 'wells fargo&&way2save&&savings', 'wfper'),
	('Wells Fargo', '1', 'Business', '.pdf', 'wells fargo&&initiate business checking', 'wfbus'),
	('Wells Fargo', '2', 'Business', '.pdf', 'wells fargo&&business market rate savings', 'wfbus'),
	('Wells Fargo', '6', 'Personal', '.pdf', 'wells fargo&&personal loan statement', 'wfploan'),
	('Citibank', '3', '', '.pdf', 'www.citicards.com', 'citi'),
	('US Bank', '3', '', '.pdf', 'u.s. bank&&reivisa.com', 'usbank'),
	('US Bank', '3', '', '.pdf', 'u.s. bank&&reimastercard.com', 'usbank'),
	('Fidelity', '4', 'Intel', '.pdf', 'intel 401(k)&&fidelity', 'fidelity401k'),
	('Fidelity', '5', '', '.pdf', 'fidelity health savings account', 'fidelityhsa'),
	('Health Equity', '5', '', '.pdf', 'healthequity&&health savings account', 'hehsa'),
	('Transamerica', '4', '', '.pdf', 'transamerica&&retirement account statement', 'transamerica'),
	('Fedloan Servicing', '6', 'Student', '.xlsx', 'fedloan servicing', 'fedloan'),
	('Amazon', '7', 'Personal', '.csv', 'amazon&&unspsc code&&asin/isbn', 'amazonper'),
	('Amazon', '7', 'Business', '.csv', 'amazon&&account group&&po number', 'amazonbus'),
	('Vanguard', '4', '', '.pdf', 'vanguard.com&&account summary', 'vanguard');



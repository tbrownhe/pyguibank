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
	"StatementTypeID"	INTEGER NOT NULL UNIQUE,
	"AccountTypeID"	INTEGER,
	"Company"	TEXT,
	"Description"	TEXT,
	"Extension"	TEXT,
	"SearchString"	TEXT NOT NULL,
	"Parser"	TEXT NOT NULL,
	"EntryPoint"	TEXT NOT NULL,
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

-- Prepopulate StatementTypes with statement recognition values and entry points
INSERT INTO "StatementTypes" ("AccountTypeID", "Company", "Description", "Extension", "SearchString", "Parser", "EntryPoint") 
VALUES 
	(1, 'Oregon Community Credit Union', 'Personal', '.pdf', 'oregon community credit union&&member number', 'occubank', 'parsepdf.occubank:parse'),
	(3, 'Oregon Community Credit Union', 'OCCU', '.pdf', 'www.myoccu.org&&card services', 'occucc', 'parsepdf.occucc:parse'),
	(6, 'Oregon Community Credit Union', 'Auto', '.csv', '254779', 'occuauto', 'parsecsv.occuauto:parse'),
	(1, 'Wells Fargo', 'Personal', '.pdf', 'wells fargo everyday checking', 'wfper', 'parsepdf.wfper:parse'),
	(2, 'Wells Fargo', 'Personal', '.pdf', 'wells fargo way2save savings', 'wfper', 'parsepdf.wfper:parse'),
	(1, 'Wells Fargo', 'Business', '.pdf', 'wells fargo&&initiate business checking', 'wfbus', 'parsepdf.wfbus:parse'),
	(2, 'Wells Fargo', 'Business', '.pdf', 'wells fargo&&business market rate savings', 'wfbus', 'parsepdf.wfbus:parse'),
	(6, 'Wells Fargo', 'Personal', '.pdf', 'wells fargo&&personal loan statement', 'wfploan', 'parsepdf.wfploan:parse'),
	(3, 'Citibank', '', '.pdf', 'www.citicards.com', 'citi', 'parsepdf.citi:parse'),
	(3, 'US Bank', '', '.pdf', 'u.s. bank&&reivisa.com', 'usbank', 'parsepdf.usbank:parse'),
	(3, 'US Bank', '', '.pdf', 'u.s. bank&&reimastercard.com', 'usbank', 'parsepdf.usbank:parse'),
	(4, 'Fidelity', 'Intel', '.pdf', 'intel 401(k)&&fidelity', 'fidelity401k', 'parsepdf.fidelity401k:parse'),
	(5, 'Fidelity', '', '.pdf', 'fidelity health savings account', 'fidelityhsa', 'parsepdf.fidelityhsa:parse'),
	(5, 'Health Equity', '', '.pdf', 'healthequity&&health savings account', 'hehsa', 'parsepdf.hehsa:parse'),
	(4, 'Transamerica', '', '.pdf', 'transamerica&&retirement account statement', 'transamerica', 'parsepdf.transamerica:parse'),
	(6, 'Fedloan Servicing', 'Student', '.xlsx', 'fedloan servicing', 'fedloan', 'parsexlsx.fedloan:parse'),
	(7, 'Amazon', 'Personal', '.csv', 'amazon&&unspsc code&&asin/isbn', 'amazonper', 'parsecsv.amazonper:parse'),
	(7, 'Amazon', 'Business', '.csv', 'amazon&&account group&&po number', 'amazonbus', 'parsecsv.amazonbus:parse'),
	(4, 'Vanguard', '', '.pdf', 'vanguard.com&&account summary', 'vanguard', 'parsepdf.vanguard:parse');



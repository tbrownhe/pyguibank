--SQLite
CREATE TABLE "Accounts" (
	"AccountID"	INTEGER UNIQUE,
	"NickName"	TEXT UNIQUE,
	"Company"	TEXT,
	"Subtype"	TEXT,
	"Type"	TEXT,
	"AssetType"	TEXT,
	PRIMARY KEY("AccountID" AUTOINCREMENT)
);

CREATE TABLE "AccountNumbers" (
	"AccountNumberID"	INTEGER UNIQUE,
	"AccountID"	INTEGER,
	"AccountNumber"	TEXT UNIQUE,
	PRIMARY KEY("AccountNumberID" AUTOINCREMENT),
	FOREIGN KEY("AccountID") REFERENCES "Accounts"("AccountID")
);

CREATE TABLE "Cards" (
	"CardID"	INTEGER UNIQUE,
	"AccountID"	INTEGER,
	"CardNumber"	TEXT,
	"LastFour"	TEXT UNIQUE,
	PRIMARY KEY("CardID" AUTOINCREMENT),
	FOREIGN KEY("AccountID") REFERENCES "Accounts"("AccountID")
);

CREATE TABLE "StatementTypes" (
	"STID"	INTEGER UNIQUE,
	"Company"	TEXT,
	"Type"	TEXT,
	"Extension"	TEXT,
	"SearchString"	TEXT,
	"Parser"	INTEGER,
	PRIMARY KEY("STID" AUTOINCREMENT)
);

CREATE TABLE "Statements" (
	"StatementID"	INTEGER UNIQUE,
	"STID"	INTEGER,
	"MainAccountID"	INTEGER,
	"StartDate"	TEXT,
	"EndDate"	TEXT,
	"ImportDate"	TEXT,
	"Filename"	TEXT,
	"MD5"	TEXT UNIQUE,
	PRIMARY KEY("StatementID" AUTOINCREMENT),
	FOREIGN KEY("MainAccountID") REFERENCES "Accounts"("AccountID"),
	FOREIGN KEY("STID") REFERENCES "StatementTypes"("STID")
);

CREATE TABLE "Transactions" (
	"TranID"	INTEGER,
	"AccountID"	INTEGER,
	"StatementID"	INTEGER,
	"Date"	TEXT,
	"Amount"	REAL,
	"Balance"	REAL,
	"Description"	TEXT,
	"MD5"	TEXT UNIQUE,
	"Category"	TEXT DEFAULT 'Uncategorized',
	"Verified"	INTEGER DEFAULT 0,
	PRIMARY KEY("TranID" AUTOINCREMENT),
	FOREIGN KEY("AccountID") REFERENCES "Accounts"("AccountID"),
	FOREIGN KEY("StatementID") REFERENCES "Statements"("StatementID")
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
	FOREIGN KEY("CardID") REFERENCES "Cards"("CardID"),
	FOREIGN KEY("StatementID") REFERENCES "Statements"("StatementID")
);

-- Prepopulate StatementTypes with statement recognition values
INSERT INTO "StatementTypes" ("Company", "Type", "Extension", "SearchString", "Parser") 
VALUES 
	('Oregon Community Credit Union', 'Personal Banking', '.pdf', 'oregon community credit union&&member number', 'occubank'),
	('Oregon Community Credit Union', 'Credit Card', '.pdf', 'www.myoccu.org&&card services', 'occucc'),
	('Oregon Community Credit Union', 'Auto Loan', '.csv', '254779', 'occuauto'),
	('Wells Fargo', 'Personal Banking', '.pdf', 'wells fargo everyday checking', 'wfper'),
	('Wells Fargo', 'Personal Banking', '.pdf', 'wells fargo&&way2save&&savings', 'wfper'),
	('Wells Fargo', 'Business Banking', '.pdf', 'wells fargo&&initiate business checking', 'wfbus'),
	('Wells Fargo', 'Business Banking', '.pdf', 'wells fargo&&business market rate savings', 'wfbus'),
	('Wells Fargo', 'Personal Loan', '.pdf', 'wells fargo&&personal loan statement', 'wfploan'),
	('Citibank', 'Credit Card', '.pdf', 'www.citicards.com', 'citi'),
	('US Bank', 'Credit Card', '.pdf', 'u.s. bank&&reivisa.com', 'usbank'),
	('Fidelity', '401k', '.pdf', 'intel 401(k)&&fidelity', 'fidelity401k'),
	('Fidelity', 'HSA', '.pdf', 'fidelity health savings account', 'fidelityhsa'),
	('Health Equity', 'HSA', '.pdf', 'healthequity&&health savings account', 'hehsa'),
	('Transamerica', '401k', '.pdf', 'transamerica&&retirement account statement', 'transamerica'),
	('Fedloan Servicing', 'Student Loan', '.xlsx', 'fedloan servicing', 'fedloan'),
	('Amazon', 'Shopping', '.csv', 'amazon&&unspsc code&&asin/isbn', 'amazonper'),
	('Amazon', 'Business', '.csv', 'amazon&&account group&&po number', 'amazonbus'),
	('Vanguard', '401k', '.pdf', 'vanguard.com&&account summary', 'vanguard');



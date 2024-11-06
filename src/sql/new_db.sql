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
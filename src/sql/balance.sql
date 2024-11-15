--SQLite
SELECT
	Accounts.NickName,
	Transactions.Date,
	Transactions.Balance
FROM Transactions
JOIN Accounts ON Transactions.AccountID = Accounts.AccountID
ORDER BY Transactions.Date ASC, Transactions.TransactionID ASC
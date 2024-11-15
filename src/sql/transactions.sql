--SQLite
SELECT
	Transactions.TransactionID,
	Accounts.NickName,
	AccountTypes.AssetType,
	Transactions.Date,
	Transactions.Amount,
	Transactions.Balance,
	Transactions.Description,
	Transactions.Category
FROM Transactions
JOIN Accounts ON Transactions.AccountID = Accounts.AccountID
JOIN AccountTypes ON Accounts.AccountTypeID = AccountTypes.AccountTypeID
{where}
ORDER BY Transactions.Date ASC, Transactions.TransactionID ASC
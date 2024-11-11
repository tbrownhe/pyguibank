--SQLite
SELECT
	Accounts.NickName,
	Statements.StartDate,
	Statements.EndDate
FROM Statements
JOIN Accounts ON Statements.AccountID = Accounts.AccountID
ORDER BY Accounts.NickName ASC, Statements.StartDate ASC
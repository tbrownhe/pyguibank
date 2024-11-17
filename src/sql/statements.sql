--SQLite
SELECT
	Accounts.AccountName,
	Statements.StartDate,
	Statements.EndDate
FROM Statements
JOIN Accounts ON Statements.AccountID = Accounts.AccountID
{where}
ORDER BY Accounts.AccountName ASC, Statements.StartDate ASC
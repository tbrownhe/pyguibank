SELECT
	b.NickName,
	a.Date,
	a.Balance
FROM (
	SELECT
		TranID,
		AccountID,
		Date,
		Balance
	FROM Transactions
	) as a
	INNER JOIN (
		SELECT
			AccountID,
			NickName
		FROM Accounts
		) as b
		ON a.AccountID = b.AccountID
ORDER BY a.Date ASC, a.TranID ASC
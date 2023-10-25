SELECT
	a.TranID,
	b.NickName,
	b.AssetType,
	a.Date,
	a.Amount,
	a.Balance,
	a.Description,
	a.Category
FROM (
	SELECT
		TranID,
		AccountID,
		Date,
		Amount,
		Balance, 
		Description,
		Category
	FROM Transactions
	) as a
	LEFT JOIN (
		SELECT
			AccountID,
			NickName,
			AssetType
		FROM Accounts
		) as b
		ON a.AccountID = b.AccountID
ORDER BY a.Date ASC, a.TranID ASC
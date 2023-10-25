SELECT
	a.ItemID,
	b.NickName,
	b.AssetType,
	a.Date,
	a.Amount,
	a.Balance,
	a.Description,
	a.Category
FROM (
	SELECT
		ItemID,
		AccountID,
		Date,
		Amount,
		'0' as Balance,
		Description,
		'Shopping' as Category
	FROM Shopping
	WHERE %s
	) as a
	LEFT JOIN (
		SELECT
			AccountID,
			NickName,
			AssetType
		FROM Accounts
		) as b
		ON a.AccountID = b.AccountID
ORDER BY a.Date ASC, a.ItemID ASC
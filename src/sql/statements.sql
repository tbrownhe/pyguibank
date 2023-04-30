SELECT
	b.NickName,
	a.StartDate,
	a.EndDate
FROM (
	SELECT
		MainAccountID,
		StartDate,
		EndDate
	FROM Statements
	) as a
	INNER JOIN (
		SELECT
			AccountID,
			NickName
		FROM Accounts
		) as b
		ON a.MainAccountID = b.AccountID
ORDER BY
	b.NickName ASC,
	a.StartDate ASC
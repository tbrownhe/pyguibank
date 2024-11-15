--SQLite
SELECT
	Shopping.ItemID,
	Accounts.NickName,
	Accounts.AssetType,
	Shopping.Date,
	Shopping.Amount,
	Shopping.Balance,
	Shopping.Description,
	Shopping.Category
FROM Shopping
JOIN Accounts ON Shopping.AccountID = Accounts.AccountID
{where}
ORDER BY Shopping.Date ASC, Shopping.ItemID ASC
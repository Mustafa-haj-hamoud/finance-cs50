from cs50 import SQL

db = SQL("sqlite:///finance.db")

bought = db.execute('SELECT symbol,SUM(amount) AS sum FROM history WHERE user_id = ? AND transaction_type="buy" GROUP BY symbol', 2)
sold = db.execute('SELECT symbol,SUM(amount) AS sum FROM history WHERE user_id = ? AND transaction_type="sell" GROUP BY symbol', 2)
bought_dict = {}
sold_dict = {}

for stock in bought:
    stock_name = stock["symbol"]
    bought_dict[stock_name] = stock["sum"]

for stock in sold:
    stock_name = stock["symbol"]
    sold_dict[stock_name] = stock["sum"]

total = bought_dict
for stock in bought_dict:
    try:
        total[stock] = bought_dict[stock] - sold_dict[stock]
    except KeyError:
        pass
print(bought_dict)
print(sold_dict)
print(total)

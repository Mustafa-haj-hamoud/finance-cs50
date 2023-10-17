import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    bought = db.execute(
        'SELECT symbol,SUM(amount) AS sum FROM history WHERE user_id = ? AND transaction_type="buy" GROUP BY symbol',
        session["user_id"],
    )
    sold = db.execute(
        'SELECT symbol,SUM(amount) AS sum FROM history WHERE user_id = ? AND transaction_type="sell" GROUP BY symbol',
        session["user_id"],
    )
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
    to_remove = []
    for stock in total:
        if total[stock] == 0:
            to_remove.append(stock)

    for stock in to_remove:
        total.pop(stock)

    assets = {}
    for stock in total:
        value = lookup(stock)["price"]
        assets[stock] = value * total[stock]

    remaining_balance = db.execute(
        "SELECT cash FROM users WHERE id = ?", session["user_id"]
    )[0]["cash"]

    return render_template(
        "index.html", total=total, assets=assets, remaining_balance=remaining_balance
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
        # Validate user input
        symbol = request.form.get("symbol")
        try:
            quantity = int(request.form.get("shares"))
        except ValueError:
            return apology("please provide a positive integer for quantity")
        if not symbol:
            return apology("Please provide a stock symbol")
        if not quantity or quantity < 1:
            return apology("please provide a positive integer for quantity")

        # Check if symbol exists
        result = lookup(symbol)
        if not result:
            return apology("Failed to find stock")

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0][
            "cash"
        ]
        price = quantity * result["price"]
        if price > cash:
            return apology("Not enough money in your account")

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db.execute(
            "INSERT INTO history (user_id, symbol, amount, total_price, time_bought, transaction_type)VALUES(?,?,?,?,?,?)",
            session["user_id"],
            symbol,
            quantity,
            price,
            current_time,
            "buy",
        )

        db.execute(
            "UPDATE users SET cash = ? WHERE id=?", cash - price, session["user_id"]
        )

        return redirect("/")


@app.route("/history")
@login_required
def history():
    hist = db.execute(
        "SELECT * FROM history WHERE user_id = ? ORDER BY time_bought DESC",
        session["user_id"],
    )
    return render_template("history.html", hist=hist)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        result = lookup(symbol)
        if result:
            return render_template("quoted.html", symbol=symbol, result=result)
        else:
            return apology("Could not Find symbol")
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").lower()
        if len(username) < 5:
            return apology("Username must be longer than 5 characters")

        password = request.form.get("password")
        if len(password) < 5:
            return apology("Password must be longer than 5 characters")

        confirmation = request.form.get("confirmation")
        if password != confirmation:
            return apology("password and confirmation must match")

        sql_username = db.execute(
            "SELECT username FROM users WHERE username = ?", username
        )
        if sql_username:
            return apology("This username already exists")

        hashed_password = generate_password_hash(password)

        db.execute(
            "INSERT INTO users (username,hash) VALUES(?,?)", username, hashed_password
        )
        login()
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        bought = db.execute(
            'SELECT symbol,SUM(amount) AS sum FROM history WHERE user_id = ? AND transaction_type="buy" GROUP BY symbol',
            session["user_id"],
        )
        sold = db.execute(
            'SELECT symbol,SUM(amount) AS sum FROM history WHERE user_id = ? AND transaction_type="sell" GROUP BY symbol',
            session["user_id"],
        )
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
        to_remove = []
        for stock in total:
            if total[stock] == 0:
                to_remove.append(stock)

        for stock in to_remove:
            total.pop(stock)

        return render_template("sell.html", total=total)

    elif request.method == "POST":
        # Validate user input
        symbol = request.form.get("symbol")
        try:
            quantity = int(request.form.get("shares"))
        except ValueError:
            return apology("please provide a positive integer for quantity")
        if not symbol:
            return apology("Please provide a stock symbol")
        if not quantity or quantity < 1:
            return apology("please provide a positive integer for quantity")

        # Check if symbol exists
        result = lookup(symbol)
        if not result:
            return apology("Failed to find stock")

        # Calculate how many stocks this user has
        bought = db.execute(
            'SELECT symbol,SUM(amount) AS sum FROM history WHERE user_id = ? AND transaction_type="buy" GROUP BY symbol',
            session["user_id"],
        )
        sold = db.execute(
            'SELECT symbol,SUM(amount) AS sum FROM history WHERE user_id = ? AND transaction_type="sell" GROUP BY symbol',
            session["user_id"],
        )
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

        # check if user has enough tokens
        if total[symbol] < quantity:
            return apology("You do not have enough stocks to sell")

        total_price = quantity * result["price"]
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_cash = float(
            db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])[0][
                "cash"
            ]
        )
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?",
            total_price + current_cash,
            session["user_id"],
        )
        db.execute(
            "INSERT INTO history (user_id, symbol, amount, total_price, time_bought, transaction_type)VALUES(?,?,?,?,?,?)",
            session["user_id"],
            symbol,
            quantity,
            total_price,
            current_time,
            "sell",
        )
        return redirect("/")

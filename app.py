import logging
import sqlite3 as sql

from os.path import exists
from time import strftime, time

from flask import Flask, jsonify, request

app = Flask(__name__)
_db = 'stock_exchange.sqlite'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M',
)
logger = logging.getLogger(__name__)

if not exists(_db):
    db = sql.connect(_db)
    c = db.cursor()
    c.execute(
        "create table offers"
        "("
        "epoch real not null constraint offers_pk primary key, "
        "datetime text not null, "
        "operation text not null, "
        "broker text not null, "
        "stock text not null, "
        "value real not null, "
        "shares int not null"
        ")"
    )
    c.execute(
        "create table wallets"
        "("
        "broker text not null, "
        "stock text not null, "
        "shares int, "
        "constraint wallets_pk primary key (broker, stock)"
        ")"
    )
    c.close()
    db.commit()
    db.close()


class Offer:
    __slots__ = [
        "epoch", "datetime", "operation", "broker", "stock", "value", "shares",
        "json"
    ]

    def __init__(
            self,
            operation, broker, stock, value, shares
    ):
        self.epoch = time()
        self.datetime = strftime('%Y/%m/%d %H:%M:%S')
        self.operation = operation.lower()
        self.broker = broker.lower()
        self.stock = stock.upper()
        self.value = value
        self.shares = shares
        self.json = {
            "epoch": self.epoch,
            "datetime": self.datetime,
            "operation": self.operation,
            "broker": self.broker,
            "stock": self.stock,
            "shares": self.shares
        }

    def __str__(self):
        return (
            f"{self.epoch}, '{self.datetime}', "
            f"'{self.operation}', '{self.broker}', "
            f"'{self.stock}', {self.value}, {self.shares}"
        )

    def __repr__(self):
        return self.json


@app.route('/')
@app.errorhandler(404)
def index(e=0):
    return (
               f'<H2>How to:</H2>'
               f'</br>'
               f'<H4>Make a new stock exchange offer:</H4>'
               f'<p>'
               f'{request.host_url}offer/operation;broker;stock;value;shares'
               f'</p>'
               f'operation = buy | sell'
               f'</br>'
               f'broker = your name or something like that'
               f'</br>'
               f'stock = stock id, like "APPL" for Apple'
               f'</br>'
               f'value = value per stock share, '
               f'float value (using dot "." as decimal separator)'
               f'</br>'
               f'shares = number of stock shares, integer value'
               f'</br>'
               f'<H4>Get stock exchange offers\' information:</H4>'
               f'<p>'
               f'{request.host_url}info/[broker|operation|stock]=value'
               f'</p>'
               f'either choose "broker", "operation" or "stock"'
               f'</br>'
           ), 200


@app.route(
    '/offer'
    '/<string:operation>'
    ';<string:broker>'
    ';<string:stock>'
    ';<float:value>'
    ';<int:shares>'
)
def offer(operation=None, broker=None, stock=None, value=None, shares=None):
    if (
        operation is None or
        broker is None or
        stock is None or
        value is None or
        shares is None
    ):
        return index(0)
    new_offer = Offer(operation, broker, stock, value, shares)
    if operation == 'buy':
        insert_into_wallet(new_offer)
    elif operation == 'sell':
        wallet_shares = get_shares_from_wallet(new_offer)
        if wallet_shares is None:
            return f'You do not have any shares from {stock}', 200
        else:
            if wallet_shares < shares:
                return f'You only have {wallet_shares} shares from {stock}', 200
            else:
                return update_wallet(new_offer, wallet_shares)
    else:
        return index(0)


@app.route('/info/<string:column>=<string:term>', methods=['GET'])
def info(column, term):
    return get_data(column, term), 200


def update_offers(obj):
    try:
        db = sql.connect(_db)
        c = db.cursor()
        logging.info(f"inserting into DB: {obj}")
        c.execute(
            f"insert into offers"
            f"("
            f"epoch, datetime, operation, broker, stock, value, shares"
            f") values ("
            f"{obj}"
            f")"
        )
    except Exception as e:
        logging.error(e)
        return f'Error: {e}', 500
    else:
        c.close()
        db.commit()
        db.close()
        logging.info('offers DB updated!')
        return jsonify({"offer inserted": obj.json}), 200


def insert_into_wallet(obj):
    db = sql.connect(_db)
    c = db.cursor()
    logging.info(f"inserting into wallet DB: {obj}")
    try:
        c.execute(
            f"insert into wallets"
            f"("
            f"broker, stock, shares"
            f") values ("
            f"'{obj.broker}', '{obj.stock}', {obj.shares}"
            f")"
        )
    except Exception as e:
        c.execute(
            f"select shares from wallets "
            f"where broker = '{obj.broker}' "
            f"and stock = '{obj.stock}'"
        )
        shares = c.fetchone()[0]
        shares += obj.shares
        c.execute(
            f"replace into wallets"
            f"("
            f"broker, stock, shares"
            f") values ("
            f"'{obj.broker}', '{obj.stock}', {shares}"
            f")"
        )
    else:
        logging.info('wallets DB updated!')
        return "stock shares inserted into wallet", 200
    finally:
        c.close()
        db.commit()
        db.close()


def get_shares_from_wallet(obj):
    db = sql.connect(_db)
    c = db.cursor()
    try:
        c.execute(
            f"select shares from wallets "
            f"where broker = '{obj.broker}' "
            f"and stock = '{obj.stock}'"
        )
        logging.info(f'broker={obj.broker} | stock={obj.stock}')
    except Exception as e:
        logging.error(e)
        return f'Error: {e}', 500
    else:
        logging.info(f'rowcount={c.rowcount}')
        if c.rowcount != -1:
            return None
        else:
            shares = c.fetchone()
            return shares[0]
    finally:
        c.close()
        db.commit()
        db.close()


def update_wallet(obj, wshares):
    db = sql.connect(_db)
    c = db.cursor()
    logging.info(f"updating wallet DB: {obj}")
    try:
        wshares -= obj.shares
        c.execute(
            f"replace into wallets"
            f"("
            f"broker, stock, shares"
            f") values ("
            f"'{obj.broker}', '{obj.stock}', {wshares}"
            f")"
        )
    except Exception as e:
        logging.error(e)
        return f'Error: {e}', 500
    else:
        logging.info('wallets DB updated!')
        return jsonify({"stock shares updated in wallet": obj.json}), 200
    finally:
        c.close()
        db.commit()
        db.close()


def get_data(column, term):
    try:
        db = sql.connect(_db)
        c = db.cursor()
        logging.info(f'column: {column} | term: {term}')
        if column == 'broker':
            c.execute(
                f"select * from offers "
                f"where broker = '{term}'"
            )
        elif column == 'operation':
            c.execute(
                f"select * from offers "
                f"where operation = '{term}'"
            )
        elif column == 'stock':
            c.execute(
                f"select * from offers "
                f"where stock = '{term}'"
            )
        else:
            return index(0)
        output = c.fetchall()
    except Exception as e:
        logging.error(e)
        return f'Error: {e}', 500
    else:
        return jsonify({"output":output})


if __name__ == '__main__':
    app.run()

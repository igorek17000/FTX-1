import time
from turtle import position
import urllib.parse
from typing import Optional, Dict, Any, List

from requests import Request, Session, Response
import hmac
from ciso8601 import parse_datetime
import matplotlib.pyplot as plt
from dateutil import parser
import datetime
from matplotlib import font_manager




class FtxClient:
    _ENDPOINT = 'https://ftx.com/api/'

    def __init__(self, api_key=None, api_secret=None, subaccount_name=None) -> None:
        self._session = Session()
        self._api_key = api_key
        self._api_secret = api_secret
        self._subaccount_name = subaccount_name

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('GET', path, params=params)

    def _post(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('POST', path, json=params)

    def _delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('DELETE', path, json=params)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        request = Request(method, self._ENDPOINT + path, **kwargs)
        self._sign_request(request)
        response = self._session.send(request.prepare())
        return self._process_response(response)

    def _sign_request(self, request: Request) -> None:
        ts = int(time.time() * 1000)
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        signature = hmac.new(self._api_secret.encode(), signature_payload, 'sha256').hexdigest()
        request.headers['FTX-KEY'] = self._api_key
        request.headers['FTX-SIGN'] = signature
        request.headers['FTX-TS'] = str(ts)
        if self._subaccount_name:
            request.headers['FTX-SUBACCOUNT'] = urllib.parse.quote(self._subaccount_name)

    def _process_response(self, response: Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            if not data['success']:
                raise Exception(data['error'])
            return data['result']

    def get_all_futures(self) -> List[dict]:
        return self._get('futures')

    def get_future(self, future_name: str = None) -> dict:
        return self._get(f'futures/{future_name}')

    def get_markets(self) -> List[dict]:
        return self._get('markets')

    def get_market(self, market) -> List[dict]:
        return self._get(f'markets/{market}')

    def get_orderbook(self, market: str, depth: int = None) -> dict:
        return self._get(f'markets/{market}/orderbook', {'depth': depth})

    def get_trades(self, market: str, start_time: float = None, end_time: float = None) -> dict:
        return self._get(f'markets/{market}/trades', {'start_time': start_time, 'end_time': end_time})

    def get_account_info(self) -> dict:
        return self._get(f'account')

    def get_open_orders(self, market: str = None) -> List[dict]:
        return self._get(f'orders', {'market': market})

    def get_order_history(
        self, market: str = None, side: str = None, order_type: str = None,
        start_time: float = None, end_time: float = None
    ) -> List[dict]:
        return self._get(f'orders/history', {
            'market': market,
            'side': side,
            'orderType': order_type,
            'start_time': start_time,
            'end_time': end_time
        })

    def get_conditional_order_history(
        self, market: str = None, side: str = None, type: str = None,
        order_type: str = None, start_time: float = None, end_time: float = None
    ) -> List[dict]:
        return self._get(f'conditional_orders/history', {
            'market': market,
            'side': side,
            'type': type,
            'orderType': order_type,
            'start_time': start_time,
            'end_time': end_time
        })

    def modify_order(
        self, existing_order_id: Optional[str] = None,
        existing_client_order_id: Optional[str] = None, price: Optional[float] = None,
        size: Optional[float] = None, client_order_id: Optional[str] = None,
    ) -> dict:
        assert (existing_order_id is None) ^ (existing_client_order_id is None), \
            'Must supply exactly one ID for the order to modify'
        assert (price is None) or (size is None), 'Must modify price or size of order'
        path = f'orders/{existing_order_id}/modify' if existing_order_id is not None else \
            f'orders/by_client_id/{existing_client_order_id}/modify'
        return self._post(path, {
            **({'size': size} if size is not None else {}),
            **({'price': price} if price is not None else {}),
            ** ({'clientId': client_order_id} if client_order_id is not None else {}),
        })

    def get_conditional_orders(self, market: str = None) -> List[dict]:
        return self._get(f'conditional_orders', {'market': market})

    def place_order(self, market: str, side: str, price: float, size: float, type: str = 'limit',
                    reduce_only: bool = False, ioc: bool = False, post_only: bool = False,
                    client_id: str = None, reject_after_ts: float = None) -> dict:
        return self._post('orders', {
            'market': market,
            'side': side,
            'price': price,
            'size': size,
            'type': type,
            'reduceOnly': reduce_only,
            'ioc': ioc,
            'postOnly': post_only,
            'clientId': client_id,
            'rejectAfterTs': reject_after_ts
        })

    def place_conditional_order(
        self, market: str, side: str, size: float, type: str = 'stop',
        limit_price: float = None, reduce_only: bool = False, cancel: bool = True,
        trigger_price: float = None, trail_value: float = None
    ) -> dict:
        """
        To send a Stop Market order, set type='stop' and supply a trigger_price
        To send a Stop Limit order, also supply a limit_price
        To send a Take Profit Market order, set type='trailing_stop' and supply a trigger_price
        To send a Trailing Stop order, set type='trailing_stop' and supply a trail_value
        """
        assert type in ('stop', 'take_profit', 'trailing_stop')
        assert type not in ('stop', 'take_profit') or trigger_price is not None, \
            'Need trigger prices for stop losses and take profits'
        assert type not in ('trailing_stop',) or (trigger_price is None and trail_value is not None), \
            'Trailing stops need a trail value and cannot take a trigger price'

        return self._post('conditional_orders', {
            'market': market,
            'side': side,
            'triggerPrice': trigger_price,
            'size': size,
            'reduceOnly': reduce_only,
            'type': 'stop',
            'cancelLimitOnTrigger': cancel,
            'orderPrice': limit_price
        })

    def cancel_order(self, order_id: str) -> dict:
        return self._delete(f'orders/{order_id}')

    def cancel_orders(
        self, market_name: str = None,
        conditional_orders: bool = False, limit_orders: bool = False
    ) -> dict:
        return self._delete(f'orders', {
            'market': market_name,
            'conditionalOrdersOnly': conditional_orders,
            'limitOrdersOnly': limit_orders
        })

    def get_fills(self, market: str = None, start_time: float = None,
        end_time: float = None, min_id: int = None, order_id: int = None
    ) -> List[dict]:
        return self._get('fills', {
            'market': market,
            'start_time': start_time,
            'end_time': end_time,
            'minId': min_id,
            'orderId': order_id
        })

    def get_balances(self) -> List[dict]:
        return self._get('wallet/balances')

    def get_total_usd_balance(self) -> int:
        total_usd = 0
        balances = self._get('wallet/balances')
        for balance in balances:
            total_usd += balance['usdValue']
        return total_usd

    def get_all_balances(self) -> List[dict]:
        return self._get('wallet/all_balances')

    def get_total_account_usd_balance(self) -> int:
        total_usd = 0
        all_balances = self._get('wallet/all_balances')
        for wallet in all_balances:
            for balance in all_balances[wallet]:
                total_usd += balance['usdValue']
        return total_usd

    def get_positions(self, show_avg_price: bool = False) -> List[dict]:
        return self._get('positions', {'showAvgPrice': show_avg_price})

    def get_position(self, name: str, show_avg_price: bool = False) -> dict:
        return next(filter(lambda x: x['future'] == name, self.get_positions(show_avg_price)), None)

    def get_all_trades(self, market: str, start_time: float = None, end_time: float = None) -> List:
        ids = set()
        limit = 100
        results = []
        while True:
            response = self._get(f'markets/{market}/trades', {
                'end_time': end_time,
                'start_time': start_time,
            })
            deduped_trades = [r for r in response if r['id'] not in ids]
            results.extend(deduped_trades)
            ids |= {r['id'] for r in deduped_trades}
            print(f'Adding {len(response)} trades with end time {end_time}')
            if len(response) == 0:
                break
            end_time = min(parse_datetime(t['time']) for t in response).timestamp()
            if len(response) < limit:
                break
        return results

    def get_historical_prices(
        self, market: str, resolution: int = 300, start_time: float = None,
        end_time: float = None
    ) -> List[dict]:
        return self._get(f'markets/{market}/candles', {
            'resolution': resolution,
            'start_time': start_time,
            'end_time': end_time
        })

    def get_last_historical_prices(self, market: str, resolution: int = 300) -> List[dict]:
        return self._get(f'markets/{market}/candles/last', {'resolution': resolution})

    def get_borrow_rates(self) -> List[dict]:
        return self._get('spot_margin/borrow_rates')

    def get_borrow_history(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('spot_margin/borrow_history', {'start_time': start_time, 'end_time': end_time})

    def get_lending_history(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('spot_margin/lending_history', {
            'start_time': start_time,
            'end_time': end_time
        })

    def get_expired_futures(self) -> List[dict]:
        return self._get('expired_futures')

    def get_coins(self) -> List[dict]:
        return self._get('wallet/coins')

    def get_future_stats(self, future_name: str) -> dict:
        return self._get(f'futures/{future_name}/stats')

    def get_single_market(self, market: str = None) -> dict:
        return self._get(f'markets/{market}')

    def get_market_info(self, market: str = None) -> dict:
        return self._get('spot_margin/market_info', {'market': market})

    def get_trigger_order_triggers(self, conditional_order_id: str = None) -> List[dict]:
        return self._get(f'conditional_orders/{conditional_order_id}/triggers')

    def get_trigger_order_history(self, market: str = None) -> List[dict]:
        return self._get('conditional_orders/history', {'market': market})

    def get_staking_balances(self) -> List[dict]:
        return self._get('staking/balances')

    def get_stakes(self) -> List[dict]:
        return self._get('staking/stakes')

    def get_staking_rewards(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('staking/staking_rewards', {
            'start_time': start_time,
            'end_time': end_time
        })

    def place_staking_request(self, coin: str = 'SRM', size: float = None) -> dict:
        return self._post('srm_stakes/stakes',)

    def get_funding_rates(self, future: str = None, start_time: float = None, end_time: float = None)-> List[dict]:
        return self._get('funding_rates', {
            'future': future,
            'start_time': start_time,
            'end_time': end_time
        })

    def get_all_funding_rates(self) -> List[dict]:
        return self._get('funding_rates')

    def get_funding_payments(self, start_time: float = None, end_time: float = None, future: str = None) -> List[dict]:
        return self._get('funding_payments', {
            'start_time': start_time,
            'end_time': end_time,
            'future':future
        })

    def create_subaccount(self, nickname: str) -> dict:
        return self._post('subaccounts', {'nickname': nickname})

    def get_subaccount_balances(self, nickname: str) -> List[dict]:
        return self._get(f'subaccounts/{nickname}/balances')

    def get_deposit_address(self, ticker: str) -> dict:
        return self._get(f'wallet/deposit_address/{ticker}')

    def get_deposit_history(self) -> List[dict]:
        return self._get('wallet/deposits')

    def get_withdrawal_fee(self, coin: str, size: int, address: str, method: str = None, tag: str = None) -> Dict:
        return self._get('wallet/withdrawal_fee', {
            'coin': coin,
            'size': size,
            'address': address,
            'method': method,
            'tag': tag
        })

    def get_withdrawals(self, start_time: float = None, end_time: float = None) -> List[dict]:
        return self._get('wallet/withdrawals', {'start_time': start_time, 'end_time': end_time})

    def get_saved_addresses(self, coin: str = None) -> dict:
        return self._get('wallet/saved_addresses', {'coin': coin})

    def submit_fiat_withdrawal(self, coin: str, size: int, saved_address_id: int, code: int = None) -> Dict:
        return self._post('wallet/fiat_withdrawals', {
        'coin': coin,
        'size': size,
        'savedAddressId': saved_address_id,
        'code': code
    })

    def get_latency_stats(self, days: int = 1, subaccount_nickname: str = None) -> Dict:
        return self._get('stats/latency_stats', {'days': days, 'subaccount_nickname': subaccount_nickname})

    def positive_future_dif(self, future: str = None, market: str = None):
        future_bid = float(self.get_future(future)['bid'])
        market_ask = float(self.get_single_market(market)['ask'])

        difference = (future_bid-market_ask)/market_ask*100
        return (difference)


    def negative_future_dif(self, future: str = None, market: str = None):
        future_ask = float(self.get_future(future)['ask'])
        market_bid = float(self.get_single_market(market)['bid'])
        difference = (future_ask-market_bid)/market_bid*100
        return (difference)


    def run_positive (self, coin, tolerance, attempt, wait):
        size = self.coin_min(f'{coin}/USD')
        for _ in range(attempt):
            future = f'{coin}-PERP'
            market = f'{coin}/USD'
            future_bid = float(self.get_future(future)['bid'])
            market_ask = float(self.get_single_market(market)['ask'])
            #sell future
            #buy market
            if self.positive_future_dif(future, market)>tolerance:
                try:
                    self.place_order(f'{coin}-PERP', 'sell', future_bid, size, 'limit',
                            False, False, False, None, None)
                    self.place_order(f'{coin}/USD', 'buy', market_ask, size, 'limit',
                            False, False, False, None, None)   
                    return ('success')
                except Exception as e:
                    return (f'failure: {e}')
            else: 
                print('failure: condition unmet')
                time.sleep(wait)
                continue

    def run_negative (self, coin, tolerance, attempt, wait):
        size = self.coin_min(f'{coin}/USD')
        for _ in range(attempt):
            future = f'{coin}-PERP'
            market = f'{coin}/USD'
            future_ask = float(self.get_future(future)['ask'])
            market_bid = float(self.get_single_market(market)['bid'])
            #buy future
            #sell market
            if self.negative_future_dif(future, market) < tolerance:
                try:
                    self.place_order(f'{coin}-PERP', 'buy', future_ask, size, 'limit',
                            False, False, False, None, None)
                    self.place_order(f'{coin}/USD', 'sell', market_bid, size, 'limit',
                            False, False, False, None, None)   
                    return ('success')
                except Exception as e:
                    return (f'failure: {e}')
            else:
                print('failure: condition unmet')
                time.sleep(wait)
                continue

    def graph_funding_rates(self, future: str="BTC"):
        fontP = font_manager.FontProperties()
        fontP.set_family('SimHei')
        fontP.set_size(14)
        xvalues = []
        yvalues = []
        colors =[]
        tn = int(time.time())
        funding_rates = self.get_funding_rates(f'{future}-PERP', tn-1728000, tn)
        
        for i in funding_rates[::-1]:
            xvalues.append(parser.parse(i["time"]))
            yvalues.append(round(float(i['rate'])*636000,2))
        
        for i in yvalues:
            if i>0:
                colors.append('green')
            elif i==0:
                colors.append('grey')
            else:
                colors.append('red')
        plt.figure(figsize=(15,5))
        plt.scatter(xvalues, yvalues, c=colors)
        plt.grid(axis="y")
        plt.title(f"{future}-PERP Funding Rates (20 Days)",fontproperties=fontP)
        plt.show()

    def fund_overtime(self, coin: str="BTC", days: int=7):
        future = f'{coin}-PERP'
        tn = int(time.time())
        funding_rates = self.get_funding_rates(future, tn-(days*86400), tn)
        total_rate = 0

        for i in funding_rates:
            total_rate+=float(i['rate'])*636000
        
        average_rate = round(total_rate/len(funding_rates),2)
        return (f'Funding Over {days} days: {average_rate}%')

    def coin_min(self, market):
        return (self.get_market(market)['minProvideSize'])

    def graph_payments(self, future):
        
        test_date = datetime.datetime(2020, 5, 17)
        tn = int(time.time())
        xvalues = []
        yvalues = []
        data = self.get_funding_payments(tn-(1728000),tn, f'{future}-PERP')[::-1]
        for j in data:
            j['time'] = parser.parse(j['time'])
            date = j['time']
            if test_date.date() != date.date():
                xvalues.append(date.date())
                test_date = date
        
        for i in xvalues:
            payment = 0
            for j in data:
                if j['time'].date() == i:
                    payment-=j['payment']
            yvalues.append(payment)

        plt.figure(figsize=(15,5))
        plt.grid()
        plt.title(f"{future}-PERP Funding Payments (20 Days)")
        plt.bar(xvalues,yvalues)
        plt.show()




Client = FtxClient('1lzuMlvkbTyhgf0qzqc7c_wGrrJQrPB0TZDt018f','XAGNmVjiM6Zrdcv2FBhZzyUr5JS4HtJBTjw9LVKr', 'AI01')

# print(Client.get_balances())

# while True:
#     print(Client.positive_future_dif("ETH-PERP", "ETH/USD"))
#     print(Client.negative_future_dif("ETH-PERP", "ETH/USD"))

# print(Client.fund_overtime("RUNE-PERP", 10))
# while True:
#     print(Client.run_positive("BTC", 0.001))


# Client.graph_payments('LEO')
# Client.graph_funding_rates('LEO')




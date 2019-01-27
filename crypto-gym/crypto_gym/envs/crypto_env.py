import gym
from gym import error, spaces, utils
from .frame_manager import FrameManager
from math import inf
import numpy as np
import matplotlib.pyplot as plt
from random import randint
from .constants import *
import time


#to start, only EOSUSD, BTCUSD, ETHUSD.
class CryptoEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    """ need: 
            observation_space: Box(100, 49, 5)
            action_space: FUNCTION! Box(3,) with lower bounds -1 and upper bounds 1 U sum(upperAction)<=1
            """

    """ Pull initial state from Postgres and have internally. also pull up orderbook raw for fulfillment.
    """

    def __init__(self):
        size = pair_limit * 4 * 4 + 1
        self.observation_space = spaces.Box(low=-inf, high=inf, shape=(100*size*framerate,))
        """ Observation space format:
        First row: USD_holdings, BTC_holdings, EOS_holdings, ETH_holdings, ... zeros(81) ... , for each pair: Candle ([open, close, high, low, volume])
        for each pair: (3)
            For each orderbook in (p0, p1, p2, p3): (4) 
                row bid_amounts, row bid_counts, row ask_amounts, row ask_counts (4) 
        """

        self.action_space = spaces.Box(low=-1, high=1, shape=(pair_limit,))
        self.frames = FrameManager(framerate=framerate, pair_limit=pair_limit)
        self.pairs = self.frames.get_pairs()
        self.current_frames = self.frames.next_frames(np.pad([starting_usd, 0.15], (0, pair_limit-1), 'constant'))
        self.holdings_history = np.array(self.current_holdings())
        self.portfolio_value_history = [1000]
        self.iter = framerate
        self.round = 1
        self.scales = [0.005, 0.015, 0.15, 1.0]


    def step(self, trades):
        #returns observation_array, reward, if game is over (mostly False), and "info" ({})
        """ To calculate reward:
            -convert all to USD as if filling order book -- should it instead be ticker price??? -- and save as init value
            -buy/sell as if filling raw order book in whatever amounts it says (if buying fill sell book and vice versa)
                    Note: can eventually greatly expand action space by accounting for specific maker/taker orders at specific amounts instead. Massive undertaking.
            -subtract 0.2% (0.002) of any active trade.
            -get next raw order book
            -convert all to USD as if filling order book -- should it instead be ticker price??? -- and save as new value
            -return new-init.
            """
        trades = self.scale_trades_by_currency(trades)
        holdings = self.current_holdings()
        #initial_money = self.portfolio_spot_value([1000, 0.15], self.iter)
        holdings = self.make_trades(holdings, trades)  #self.holdings altered to new holdings
        dummy_holdings_for_reward = self.make_trades([1000, 0.15], trades)
        next = self.frames.get_next_frame(self.iter)
        next.loc[['Candles'], :pair_limit] = holdings
        self.iter += 1
        new_money = self.portfolio_spot_value(dummy_holdings_for_reward, self.iter+10)
        new_money_real = self.portfolio_spot_value(holdings, self.iter+1)

        self.portfolio_value_history.append(new_money_real)

        self.holdings_history = np.vstack([self.holdings_history, holdings])
        self.current_frames.append(next)
        self.current_frames = self.current_frames[1:]
        if self.iter % 500 is 0:
            print(time.ctime() + " " + str(self.iter) + " Current Portfolio Value: ", new_money_real, " Holdings: USD ", holdings[0], " BTC ", holdings[1])  #, " EOS ", holdings[2], " ETH ", holdings[3], ".")
        return np.hstack(np.vstack(np.dstack(self.current_frames))), self.reward(new_money, 1974.25), self.iter >= 6000 or new_money < 500, {}

    def reward(self, value, start):
        return (value-start) * abs(value-start)

    """
            let scales = [0.005, 0.015, 0.15, 1.0];   p0, p1, p2, p3.
            for i in 0..orders.len() {
            let price = orders [i][0];
            if orders[i][2] > 0.0 { //is a bid
                let n = cmp::min((((last-price)/last)*(100.0/scales[level])) as usize, 99) as usize;
                bid_amounts[n] += orders[i][2];
                bid_counts[n] += orders[i][1] as i16;
            } else {
                let n = cmp::min((((price-last)/last)*(100.0/scales[level])) as usize, 99) as usize;
                ask_amounts[n] += orders[i][2];
                ask_counts[n] += orders[i][1] as i16;
            }

        }
    """
    def create_prices_asks(self, level, closing):
        multiplier = (self.scales[level]/100)*closing
        prices = [(n*multiplier) + closing for n in range(100)]
        return prices

    def create_prices_bids(self, level, closing):
        multiplier = (self.scales[level]/100)*closing
        prices = [abs((n*multiplier)-closing) for n in range(100)]
        return prices

    def get_bids_for_level(self, level, pair):
        return self.current_frames[framerate-1].loc[pair+book_parts[0]+book_types[level]]

    def get_asks_for_level(self, level, pair):
        return self.current_frames[framerate-1].loc[pair+book_parts[2]+book_types[level]]

    def trade_from_raw(self, holdings, trades, delta, name, pair):
        order_books = self.frames.get_current_raw_book(self.iter)
        if trades[pair] < 0 and holdings[pair+1] > 0:  # sell crypto side / buy usd side
            bid_index = 0  #delta is amount of crypto to sell in crypto units (e.g. sell 1 bitcoin)
            usd = 0
            book_amounts = order_books.loc[name+raw_parts[0]]
            book_prices = order_books.loc[name+raw_parts[1]]
            while delta > 0:
                d = min(delta, book_amounts[bid_index])
                delta -= d
                usd += d * book_prices[bid_index]
                bid_index += 1
                holdings[pair+1] -= d
                if bid_index == 5000 and delta is not 0:
                    print("Err! Not enough order volume to buy USD for held ", delta, " and pair ", name)
                    break
            holdings[0] += usd * 0.998
        if trades[pair] > 0 and holdings[0] > 0:  # buy crypto side / sell usd side
            ask_index = 0  # delta is amount of USD to sell in USD
            crypto = 0
            book_amounts = order_books.loc[name+raw_parts[2]]      #amounts are in crypto units, e.g. 1 btc
            book_prices = order_books.loc[name+raw_parts[3]]         #prices in USD
            while delta > 0:
                d = min(delta, book_amounts[ask_index]*book_prices[ask_index])
                if d > 0:
                    delta -= d
                    crypto += d / book_prices[ask_index]
                    holdings[0] -= d
                ask_index += 1
                if ask_index == 5000 and delta is not 0:
                    print("Err! Not enough order volume to buy crypto for held ", delta, " and pair ", name)
                    break
            holdings[pair+1] += crypto * 0.998
        return holdings

    #trade off of non-raw books instead of raw books -- both for performance and to avoid Err! Not enough order volume to buy.
    def make_trades(self, holdings, trades):
        for pair in range(len(trades)):
            name = self.frames.get_pairs()[pair+1]
            closing = self.frames.get_price(pair+1, self.iter)
            if trades[pair] < 0 and holdings[pair+1] > 0:  # sell crypto side / buy usd side
                delta = abs(trades[pair] * holdings[pair+1])  #delta is amount of crypto to sell in crypto units (e.g. sell 1 bitcoin)
                usd = delta*closing
                holdings[pair+1] -= delta
                holdings[0] += usd * 0.998
            if trades[pair] > 0 and holdings[0] > 0:  # buy crypto side / sell usd side
                delta = trades[pair] * holdings[0]  # delta is amount of USD to sell in USD
                crypto = delta/closing
                holdings[0] -= delta
                holdings[pair+1] += crypto * 0.998
        return holdings

    def portfolio_spot_value(self, holdings, iter):
        usd = holdings[0]
        for i in range(1, len(holdings)):
            usd += holdings[i] * self.frames.get_price(i, iter)
        return usd

    #no longer used. calculate by ticker price instead.
    def calculate_portfolio_value(self, holdings):
        usd = holdings[0]
        for i in range(1, len(holdings)+1):
            pair = self.pairs[i]
            held, bid_index = holdings[i], 0
            book_amounts = self.order_books.loc[pair+raw_parts[0]]
            book_prices = self.order_books.loc[pair+raw_parts[1]]
            while held > 0:
                delta = min(held, book_amounts[bid_index])
                #[pair-1][0][bid_index])
                held -= delta
                usd += delta * book_prices[bid_index]
                bid_index += 1
                if bid_index == 5000 and held is not 0:
                    print("Err! Not enough order volume to convert to USD for held ", held, " and pair ", pair)
                    break
        return usd

    def current_holdings(self):
        return self.current_frames[framerate-1].loc[['Candles'], :pair_limit].values[0]
        #return self.current_frames[0, 0:4, 0]
        #        return


    def reset(self):
        #return first observation array.
        self.current_frames = self.frames.next_frames(np.pad([starting_usd, 0.15], (0, pair_limit-1), 'constant'))
        #todo init all money as what? USD? currently start with 10K USD and nothing else.
        self.holdings_history = np.array(self.current_holdings())
        self.portfolio_value_history = [1000]
        self.iter = framerate
        self.round += 1
        return np.hstack(np.vstack(self.current_frames))

    def render(self, mode='human', close=False):
        #this is for making visualizations. maybe a plot of profits?
        if self.round % 2 is 0:
            try:
                colors = ["green", "blue", "red", "cyan"]
                fig = plt.figure()
                self.holdings_history[:, 1] = [n*1000 for n in self.holdings_history[:, 1]]
                for i in range(len(self.holdings_history[0])):
                    plt.plot(self.holdings_history[:, i], color=colors[i])  # plot rewards
                plt.plot(self.portfolio_value_history, color="black")
                plt.xlabel('step')
                plt.ylabel('holdings')
                fig.savefig(str(self.round) + "_" + str(self.iter) + "_" + str(randint(0, 100)) + '.png')
            except:
                print("Something went wrong when saving the figure.")

    """ will we need this??? 
    @property
    def action_space(self):
        ...
            #[-0.6800189   1.          0.44649774]

    """

    def scale_trades_by_currency(self, trades):
        buy = 0
        sell = 0
        for x in trades:
            if x > 0:
                buy = buy + x
            else:
                sell = sell - x

        for i in range(0, len(trades)):
            if trades[i] > 0 and buy > 1:
                trades[i] = trades[i]/buy
            elif sell > 1:
                trades[i] = trades[i]/sell

        return trades




"""
        #scale by row
        for row in range(0, len(trades)):
            rowsum = 0
            for col in range(0, 1): #len(trades[row])):
                rowsum += trades[row][col]
            rowsum -= trades[row][row]
            for col in range(0, 1): #len(trades[row])):
                trades[row][col] = trades[row][col]/rowsum

        #scale by column
        for col in range(0, len(trades)):
            colsum = 0
            for row in range(0, 1): #len(trades[row])):
                colsum += trades[row][col]
            colsum -= trades[row][row]
            for col in range(0, 1): #len(trades[row])):
                trades[row][col] = trades[row][col]/colsum
                """



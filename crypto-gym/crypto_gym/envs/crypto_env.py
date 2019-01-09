import gym
from gym import error, spaces, utils
from gym.utils import seeding
from .frame_manager import FrameManager
from math import inf
import numpy as np
import matplotlib.pyplot as plt
from random import randint


#to start, only EOSUSD, BTCUSD, ETHUSD.
class CryptoEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    """ need: 
            observation_space: Box(100, 51, 5)
            action_space: FUNCTION! Box(3,) with lower bounds -1 and upper bounds 1 U sum(upperAction)<=1
            """

    """ Pull initial state from Postgres and have internally. also pull up orderbook raw for fulfillment.
    """

    def __init__(self):
        self.observation_space = spaces.Box(low=-inf, high=inf, shape=(24500,))
        """ Observation space format:
        First row: USD_holdings, BTC_holdings, EOS_holdings, ETH_holdings, ... zeros(81) ... , for each pair: Candle ([open, close, high, low, volume])
        for each pair: (3)
            For each orderbook in (p0, p1, p2, p3): (4) 
                row bid_amounts, row bid_counts, row ask_amounts, row ask_counts (4) 
        """
        self.action_space = spaces.Box(low=-1, high=1, shape=(3,))
        self.frames = FrameManager(framerate=5, pair_limit=3)
        self.current_frames = self.frames.next_frames(np.array([500, 0, 0, 0]))
        self.holdings_history = np.array(self.current_holdings())

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
        self.order_books = self.frames.get_current_raw_book()
        holdings = self.current_holdings()
        #print(holdings)
        initial_money = self.calculate_portfolio_value(holdings)
        holdings = self.make_trades(holdings, trades)  #self.holdings altered to new holdings
        self.order_books = self.frames.get_next_raw_book()
        new_money = self.calculate_portfolio_value(holdings)
        self.current_frames = np.dstack([self.current_frames[:, :, 0:4], self.frames.get_next_frame(holdings)])
        #print(holdings)
        #print(self.current_frames.shape, " dstacked: ", np.dstack(self.current_frames).shape, " vstacked: ", np.vstack(self.current_frames).shape, " hstacked: ", np.hstack(self.current_frames).shape)

        self.holdings_history = np.dstack((self.holdings_history, holdings))

        return np.hstack(np.vstack(self.current_frames)), new_money-initial_money, False, {}

    def make_trades(self, holdings, trades):
        for pair in range(len(trades)):
            if trades[pair] < 0 and holdings[pair+1] > 0:  # sell crypto side / buy usd side
                delta, bid_index = abs(max(-1, trades[pair]) * holdings[pair+1]), 0
                usd = 0
                while delta > 0:
                    d = min(delta, self.order_books[pair][0][bid_index])
                    delta -= d
                    usd += d * self.order_books[pair][1][bid_index]
                    bid_index += 1
                    holdings[pair+1] -= d
                    if bid_index == 5000 and delta > 0:
                        print("Err! Not enough order volume to buy USD")
                        break
                holdings[0] += usd * 0.998
            if trades[pair] > 0 and holdings[0] > 0:  # buy crypto side / sell usd side
                delta, ask_index = min(1, trades[pair]) * holdings[0], 0
                crypto = 0
                while delta > 0:
                    d = min(delta, self.order_books[pair][2][ask_index])
                    delta -= d
                    crypto += d * self.order_books[pair][3][ask_index]
                    ask_index += 1
                    holdings[0] -= d
                    if ask_index == 5000 and delta > 0:
                        print("Err! Not enough order volume to buy crypto")
                        break
                holdings[pair+1] += crypto * 0.998
        return holdings


    def calculate_portfolio_value(self, holdings):
        usd = holdings[0]
        #print(holdings)
        for pair in range(1, len(holdings)):
            held, bid_index = holdings[pair], 0
            while held > 0:
                delta = min(held, self.order_books[pair-1][0][bid_index])
                held -= delta
                usd += delta * self.order_books[pair-1][1][bid_index]
                bid_index += 1
                if bid_index == 5000 and held > 0:
                    print("Err! Not enough order volume to convert to USD for held ", held, " and pair ", pair)
                    break
        return usd

    def current_holdings(self):
        return self.current_frames[0, 0:4, 0]

    def reset(self):
        #return first observation array.
        self.frames = FrameManager(framerate=5, pair_limit=3)
        self.current_frames = self.frames.next_frames(np.array([1000, 0, 0, 0]))
        #todo init all money as what? USD? currently start with 10K USD and nothing else.
        #print(self.current_frames.shape, " dstacked: ", np.dstack(self.current_frames).shape, " vstacked: ", np.vstack(self.current_frames).shape, " hstacked: ", np.hstack(self.current_frames).shape)
        self.holdings_history = np.array(self.current_holdings())
        return np.hstack(np.vstack(self.current_frames))

    def render(self, mode='human', close=False):
        #this is for making visualizations. maybe a plot of profits?
        for i in range(len(self.holdings_history[0])):
            plt.plot(self.holdings_history[:, i])  # plot rewards
        plt.xlabel('step')
        plt.ylabel('holdings')
        plt.savefig(str(randint(0, 100))+'.png')
    """ will we need this??? 
    @property
    def action_space(self):
        ...
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
            if trades[i] > 0:
                trades[i] = trades[i]/buy
            else:
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



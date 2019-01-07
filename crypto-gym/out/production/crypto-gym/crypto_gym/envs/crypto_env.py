import gym
from gym import error, spaces, utils
from gym.utils import seeding
from crypto_gym.envs import FrameManager
from math import inf
import numpy as np

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
        self.observation_space = spaces.Box(low=-inf, high=inf, shape=(100, 49, 5))
        """ Observation space format:
        First row: USD_holdings, BTC_holdings, EOS_holdings, ETH_holdings, ... zeros(81) ... , for each pair: Candle ([open, close, high, low, volume])
        for each pair: (3)
            For each orderbook in (p0, p1, p2, p3): (4) 
                row bid_amounts, row bid_counts, row ask_amounts, row ask_counts (4) 
        """
        self.action_space = spaces.Box(low=-1, high=1, shape=(3,))

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
        self.order_books = self.frames.get_current_raw_book()
        self.holdings = self.current_holdings()
        initial_money = self.calculate_portfolio_value(self.holdings[0], self.holdings[1:])
        self.make_trades(self.holdings, trades) #self.holdings altered to new holdings
        self.order_books = self.frames.get_next_raw_book()
        new_money = self.calculate_portfolio_value(self.holdings[0], self.holdings[1:])
        self.current_frames = np.insert(self.current_frames, 0, self.frames.get_next_frame(self.holdings))[0:4]
        return self.current_frames, new_money-initial_money, False, {}

    def make_trades(self, holdings, trades):
        for pair in 0..trades.length:
            if trades[pair] < 0: #sell crypto side / buy usd side
                delta, bid_index = abs(trades[pair] * holdings[pair+1]), 0
                usd = 0
                while delta > 0 :
                    d = min(delta, self.order_books[pair][0][bid_index])
                    delta -= d
                    usd += d * self.order_books[pair][1][bid_index]
                    bid_index += 1
                    if bid_index == 5000 and delta > 0:
                        print("Err! Not enough order volume to buy USD")
                        break
                holdings[0] += usd * 0.998
                holdings[pair+1] -= delta
            if trades[pair] > 0: # buy crypto side / sell usd side
                delta, ask_index = trades[pair] * holdings[0], 0
                crypto = 0
                while delta > 0:
                    d = min(delta, self.order_books[pair][2][ask_index])
                    delta -= d
                    crypto += d * self.order_books[pair][3][ask_index]
                    ask_index += 1
                    if ask_index == 5000 and delta > 0:
                        print("Err! Not enough order volume to buy crypto")
                        break
                    holdings[pair+1] += crypto * 0.998
                    holdings[0] -= delta


    def calculate_portfolio_value(self, USD, holdings):
        usd = USD
        for pair in 0..holdings.length:
            held, bid_index = holdings[pair], 0
            while held > 0 :
                delta = min(held, self.order_books[pair][0][bid_index])
                held -= delta
                usd += delta * self.order_books[pair][1][bid_index]
                bid_index += 1
                if bid_index == 5000 and held > 0:
                    print("Err! Not enough order volume to convert to USD")
                    break
        return usd

    def current_holdings(self):
        return self.current_frames[0][0][0:4]


    def reset(self):
        #return first observation array.
        self.frames = FrameManager(framerate=5, pair_limit=3)
        self.current_frames = self.frames.next_frames(np.array([10000, 0, 0, 0]))
        #todo init all money as what? USD? currently start with 10K USD and nothing else.
        return self.current_frames

    def render(self, mode='human', close=False):
        #this is for making visualizations. maybe a plot of profits?
        ...

    """ will we need this??? 
    @property
    def action_space(self):
        ...
    """
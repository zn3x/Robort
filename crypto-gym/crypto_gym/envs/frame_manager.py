from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import numpy as np
from .constants import *
import pandas as pd

class FrameManager:
    class __FrameManager:

        def __init__(self, framerate, pair_limit):
            self.framerate = framerate
            self.pair_limit = pair_limit
            Base = automap_base()
            engine = create_engine("postgres://postgres:Gr0mpie3@localhost")
            # reflect the tables
            Base.prepare(engine, reflect=True)
            # mapped classes are now created with names by default
            # matching that of the table name.
            self.Raw_Books = Base.classes.order_book_raw
            self.Books = [Base.classes.order_book_p0, Base.classes.order_book_p1, Base.classes.order_book_p2, Base.classes.order_book_p3]
            self.Candles = Base.classes.candles
            self.Snaps = Base.classes.snaps
            self.session = Session(engine)
            self.nframes = 9750
            self.book_parts = ["_bid_amounts_", "_bid_counts_", "_ask_amounts_", "_ask_counts_"]
            self.raw_parts = ["_bid_amounts", "_bid_prices", "_ask_amounts", "_ask_prices"]
            self.book_types = ['p0', 'p1', 'p2', 'p3']
            self.pairs = {}

            for pair in self.session.query(Base.classes.pairs):
                self.pairs[pair.id] = pair.name.strip()

            self.framelength = self.pair_limit * len(self.Books) * 4 + 1
            self.frames = {}

            self.load_all_frames()
            # collection-based relationships are by default named
            # "<classname>_collection"
            #print (session.order_book_p3_collection)

        def load_all_frames(self):
            begin, end = '2018-09-10', '2018-09-25'  #self.get_time(self.frame)
            self.prices = {}
            for i in range(self.nframes):
                self.frames[i] = self.build_frame()
                self.prices[i] = {}

            candles = self.session.query(self.Candles).filter(self.Candles.timestamp > '2018-09-10', self.Candles.timestamp < '2018-09-25', self.Candles.pair <= self.pair_limit).order_by(self.Candles.timestamp.desc())
            indices = {}

            for i in range(self.nframes):
                indices[i] = self.pair_limit+1
            for candle in candles:
                index = indices[candle.snap_id]
                self.frames[candle.snap_id].loc[['Candles'], index:index+4] = [candle.open, candle.close, candle.high, candle.low, candle.volume]
                indices[candle.snap_id] += 5
                if candle.pair not in self.prices[candle.snap_id]:
                    self.prices[candle.snap_id][candle.pair] = candle.close

            index = 0
            for books in self.Books:
                for book in self.session.query(books).filter(books.timestamp > begin, books.timestamp <= end, books.pair <= self.pair_limit):
                    self.frames[book.snap_id].loc[[self.pairs[book.pair]+self.book_parts[0]+self.book_types[index]], :] = np.pad(book.bid_amounts, (0, 100-len(book.bid_amounts)), 'constant')
                    self.frames[book.snap_id].loc[[self.pairs[book.pair]+self.book_parts[1]+self.book_types[index]], :] = np.pad(book.bid_counts, (0, 100-len(book.bid_counts)), 'constant')
                    self.frames[book.snap_id].loc[[self.pairs[book.pair]+self.book_parts[2]+self.book_types[index]], :] = np.pad(book.ask_amounts, (0, 100-len(book.ask_amounts)), 'constant')
                    self.frames[book.snap_id].loc[[self.pairs[book.pair]+self.book_parts[3]+self.book_types[index]], :] = np.pad(book.ask_counts, (0, 100-len(book.ask_counts)), 'constant')
                index += 1

        def build_frame(self):
            frames = [[self.pairs[pair]+self.book_parts[0], self.pairs[pair]+self.book_parts[1], self.pairs[pair]+self.book_parts[2], self.pairs[pair]+self.book_parts[3]] for pair in range(1, self.pair_limit+1)]
            frames = np.array([[[pair+booktype for pair in pairbook] for booktype in self.book_types] for pairbook in frames])
            frames = np.insert(frames, 0, "Candles")
            frames.reshape(self.framelength,)
            frame = np.zeros([self.framelength, 100])
            frame = pd.DataFrame(frame, index=frames, columns=range(100))

            return frame

        def get_next_frame(self, frame):
            #get next frame from postgres.
            return self.frames[frame]

        def next_frames(self, holdings):
            #get next framerate num frames and return array.
            frames = []
            frame = self.get_next_frame(0)
            frame.loc[['Candles'], :self.pair_limit] = holdings
            frames.append(frame)
            for _ in range(1, self.framerate):
                nextt = self.get_next_frame(_)
                nextt.loc[['Candles'], :self.pair_limit] = holdings
                frames.append(nextt)
            return frames

        def load_raw_books(self):
            self.raw_books = {}
            begin, end = '2018-09-10', '2018-09-25'  #self.get_time(self.frame)

            frames = np.array([[self.pairs[pair]+self.raw_parts[0], self.pairs[pair]+self.raw_parts[1], self.pairs[pair]+self.raw_parts[2], self.pairs[pair]+self.raw_parts[3]] for pair in range(1, self.pair_limit+1)]).reshape(12,)

            for i in range(self.nframes):
                self.raw_books[i] = pd.DataFrame(np.zeros([4*self.pair_limit, 5000]), index=frames, columns=range(5000))

            for book in self.session.query(self.Raw_Books).filter(self.Raw_Books.timestamp >= begin, self.Raw_Books.timestamp <= end, self.Raw_Books.pair <= self.pair_limit).order_by(self.Raw_Books.pair):
                self.raw_books[book.snap_id].loc[self.pairs[book.pair]+self.raw_parts[0], :] = np.pad(book.bid_amounts, (0, 5000-len(book.bid_amounts)), 'constant')
                self.raw_books[book.snap_id].loc[self.pairs[book.pair]+self.raw_parts[1], :] = np.pad(book.bid_prices, (0, 5000-len(book.bid_prices)), 'constant')
                self.raw_books[book.snap_id].loc[self.pairs[book.pair]+self.raw_parts[2], :] = np.pad(book.ask_amounts, (0, 5000-len(book.ask_amounts)), 'constant')
                self.raw_books[book.snap_id].loc[self.pairs[book.pair]+self.raw_parts[3], :] = np.pad(book.ask_prices, (0, 5000-len(book.ask_prices)), 'constant')


        def get_book(self, frameno):
            begin, end = '2018-09-10', '2018-09-25'  #self.get_time(self.frame)

            frames = np.array([[self.pairs[pair]+self.raw_parts[0], self.pairs[pair]+self.raw_parts[1], self.pairs[pair]+self.raw_parts[2], self.pairs[pair]+self.raw_parts[3]] for pair in range(1, self.pair_limit+1)]).reshape(self.pair_limit*4,)
            frame = pd.DataFrame(np.zeros([4*self.pair_limit, 5000]), index=frames, columns=range(5000))

            for book in self.session.query(self.Raw_Books).filter(self.Raw_Books.snap_id == frameno, self.Raw_Books.timestamp >= begin, self.Raw_Books.timestamp <= end, self.Raw_Books.pair <= self.pair_limit).order_by(self.Raw_Books.pair):
                frame.loc[self.pairs[book.pair]+self.raw_parts[0], :] = np.pad(book.bid_amounts, (0, 5000-len(book.bid_amounts)), 'constant')
                frame.loc[self.pairs[book.pair]+self.raw_parts[1], :] = np.pad(book.bid_prices, (0, 5000-len(book.bid_prices)), 'constant')
                frame.loc[self.pairs[book.pair]+self.raw_parts[2], :] = np.pad(book.ask_amounts, (0, 5000-len(book.ask_amounts)), 'constant')
                frame.loc[self.pairs[book.pair]+self.raw_parts[3], :] = np.pad(book.ask_prices, (0, 5000-len(book.ask_prices)), 'constant')
            return frame

        def get_current_raw_book(self, frame):
            """ return current raw books as an array of pair_limit x 4 x 5000 """
            return self.get_book(frame) #self.raw_books[self.frame]

        def get_pairs(self):
            return self.pairs

        def get_time(self, frame):
            snap = self.session.query(self.Snaps).filter(self.Snaps.snap_id == frame, self.Snaps.time_begin > '2018-09-10', self.Snaps.time_end < '2018-09-25').first()
            return snap.time_begin, snap.time_end

        def get_price(self, pair, frame):
            try:
                return self.prices[frame+1][pair]
            except:
                print("Err! No price available for frame "+str(frame+1)+" and pair "+str(pair))
                return 0

    instance = None
    def __init__(self, framerate, pair_limit):
        if not FrameManager.instance:
            FrameManager.instance = FrameManager.__FrameManager(framerate, pair_limit)

    def __getattr__(self, name):
        return getattr(self.instance, name)
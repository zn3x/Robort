from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import numpy as np
import pandas as pd

class FrameManager():

    def __init__(self, framerate, pair_limit):
        self.frame = 25
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

        self.pairs = {}

        for pair in self.session.query(Base.classes.pairs):
            self.pairs[pair.id] = pair.name.strip()
            print(pair.id, pair.name)

        self.framelength = self.pair_limit * len(self.Books) * 4 + 1
        print("rows per frame: ", self.framelength)
        self.get_current_raw_book()
        self.get_next_raw_book()
        # collection-based relationships are by default named
        # "<classname>_collection"
        #print (session.order_book_p3_collection)

    def get_next_frame(self, holdings):
        #get next frame from postgres.
        frames = np.array([[self.pairs[pair]+"_bid_amounts_", self.pairs[pair]+"_bid_counts_", self.pairs[pair]+"_ask_amounts_", self.pairs[pair]+"_ask_counts_"] for pair in range(1, self.pair_limit+1)]*len(self.Books))
        frames = np.insert(frames, 0, "Candles")
        frames.reshape(self.framelength,)
        frame = np.zeros([self.framelength, 100])
        frame = pd.DataFrame(frame, index=frames)
        frame[:self.pair_limit+1][0] = holdings
        frame
        snap = self.session.query(self.Snaps).filter(self.Snaps.snap_id==self.frame).order_by(self.Snaps.time_begin.desc()).first()
        begin, end = snap.time_begin, snap.time_end
        candles = self.session.query(self.Candles).filter(self.Candles.timestamp > begin, self.Candles.timestamp <= end).order_by(self.Candles.pair)
        index = self.pair_limit+1
        for candle in candles:
            #print(candle.pair)
            if candle.pair <= self.pair_limit:
                frame[index:index+5][0] = [candle.open, candle.close, candle.high, candle.low, candle.volume]
                index += 5
        for books in self.Books:
            for book in self.session.query(books).filter(books.timestamp > begin, books.timestamp <= end).order_by(books.pair):
                if book.pair <= self.pair_limit:
                    #print(frame.shape)
                    #print(np.pad(book.ask_amounts, (0, 100-len(book.ask_amounts)), 'constant').shape)
                    try:
                        frame = np.vstack([frame, np.pad(book.bid_amounts, (0, 100-len(book.bid_amounts)), 'constant'),
                                       np.pad(book.bid_counts, (0, 100-len(book.bid_counts)), 'constant'),
                                       np.pad(book.ask_amounts, (0, 100-len(book.ask_amounts)), 'constant'),
                                       np.pad(book.ask_counts, (0, 100-len(book.ask_counts)), 'constant')])
                    except:
                        self.frame += 1
                        return self.get_next_frame(holdings)
        if self.frame%200 == 0:
            print("next frame: ", frame.shape, begin, self.frame)
        self.frame += 1
        frame
        if frame.shape != (49, 100):
            return self.get_next_frame(holdings)
        else:
            return frame

    def next_frames(self, holdings):
        #get next framerate num frames and return array.
        frames = self.get_next_frame(holdings)
        for _ in range(1, self.framerate):
            frames = np.dstack([frames, self.get_next_frame(holdings)])
        #print(frames.shape)
        return frames

    def get_current_raw_book(self):
        """ return current raw books as an array of pair_limit x 4 x 5000 """

        snap = self.session.query(self.Snaps).filter(self.Snaps.snap_id==self.frame).order_by(self.Snaps.time_begin.desc()).first()
        begin, end = snap.time_begin, snap.time_end
        first = True
        frame = np.array([])
        third = False
        taken = []
        for book in self.session.query(self.Raw_Books).filter(self.Raw_Books.timestamp >= begin, self.Raw_Books.timestamp <= end).order_by(self.Raw_Books.pair):
            if book.pair <= self.pair_limit and book.pair not in taken:
                taken.append(book.pair)
                abook = np.vstack([np.pad(book.bid_amounts, (0, 5000-len(book.bid_amounts)), 'constant'),
                                   np.pad(book.bid_prices, (0, 5000-len(book.bid_prices)), 'constant'),
                                   np.pad(book.ask_amounts, (0, 5000-len(book.ask_amounts)), 'constant'),
                                   np.pad(book.ask_prices, (0, 5000-len(book.ask_prices)), 'constant')])
                if(first):
                    frame = abook
                elif(third):
                    frame = np.vstack([frame, [abook]])
                else:
                    frame = np.array([frame, abook])
                    third = True
                first = False
        #print(frame.shape)
        if frame.shape != (3, 4, 5000):
            self.frame += 1
            return self.get_next_raw_book()
        else:
            return frame


    def get_next_raw_book(self):
        """ return current raw books as an array of pair_limit x 4 x 5000 """
        snap = self.session.query(self.Snaps).filter(self.Snaps.snap_id==self.frame+1).order_by(self.Snaps.time_begin.desc()).first()
        begin, end = snap.time_begin, snap.time_end
        first = True
        frame = np.array([])
        third = False
        taken = []
        for book in self.session.query(self.Raw_Books).filter(self.Raw_Books.timestamp >= begin, self.Raw_Books.timestamp <= end).order_by(self.Raw_Books.pair):
            if book.pair <= self.pair_limit and book.pair not in taken:
                taken.append(book.pair)
                abook = np.vstack([np.pad(book.bid_amounts, (0, 5000-len(book.bid_amounts)), 'constant'),
                                   np.pad(book.bid_prices, (0, 5000-len(book.bid_prices)), 'constant'),
                                   np.pad(book.ask_amounts, (0, 5000-len(book.ask_amounts)), 'constant'),
                                   np.pad(book.ask_prices, (0, 5000-len(book.ask_prices)), 'constant')])
                if(first):
                    frame = abook
                elif(third):
                    frame = np.vstack([frame, [abook]])
                else:
                    frame = np.array([frame, abook])
                    third = True
                first = False
        #print(frame.shape)
        if frame.shape != (3, 4, 5000):
            self.frame += 1
            return self.get_next_raw_book()
        else:
            return frame

f = FrameManager(5, 3)
f.get_next_frame(np.array([500, 0, 0, 0]))



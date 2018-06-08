extern crate bitfinex;
extern crate postgres;
extern crate postgres_array;
extern crate reqwest;
extern crate chrono;
#[macro_use]
extern crate serde_derive;
extern crate serde_json;

use postgres::{Connection, TlsMode};
use std::sync::{Arc, Mutex};
use bitfinex::{ errors::*, events::*, websockets::* };
use bitfinex::{ pairs::*};//, precision::*}; //currency::*
use std::{thread, cmp};
use std::io::Read;
use chrono::prelude::*;
use serde_json::{Value, Error};

struct Ticker {connection: Connection, snap: Arc<Mutex<i32>>, seq: Arc<Mutex<i16>>}
struct Trades {connection: Connection, snap: Arc<Mutex<i32>>}
struct Candles {connection: Connection, snap: Arc<Mutex<i32>>, seq: Arc<Mutex<i16>>, last: bool, now: i64}

impl EventHandler for Ticker {
    fn on_data_event(&mut self, event:DataEvent) {
        if let DataEvent::TickerTradingEvent(channel, tick) = event {
            let mut snaplock = self.snap.lock().unwrap();
            let mut seqlock = self.seq.lock().unwrap();
            *seqlock += 1;
            let (snap, seq) = (*snaplock, *seqlock);
            drop(snaplock);
            drop(seqlock);
            self.connection.execute("INSERT INTO ticker \
                (snap_id, exchange, pair, timestamp, sequence, \
                 bid, bid_size, ask, ask_size, daily_change, \
                 daily_change_perc, last_price, volume, high, low) VALUES \
                 ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)",
                 &[&snap, &(1 as i16), &(1 as i16), &Utc::now(), &&seq,
                 &tick.bid, &tick.bid_size, &tick.ask, &tick.ask_size, &tick.daily_change,
                 &tick.daily_change_perc, &tick.last_price, &tick.volume, &tick.high, &tick.low]).unwrap();
        }
    }
}


impl EventHandler for Trades {
    fn on_data_event(&mut self, event:DataEvent) {
        if let DataEvent::TradesTradingUpdateEvent(channel, unk, trade) = event {
            if unk != "te" {
                let is_sell: bool = trade.amount < 0.0;
                self.connection.execute("INSERT INTO trades \
                (snap_id, exchange, pair, timestamp, trade_id, \
                 amount, price, is_sell) VALUES \
                 ($1, $2, $3, $4, $5, $6, $7, $8)",
                 &[&*self.snap.lock().unwrap(), &(1 as i16), &(1 as i16), &get_utc_from_ms(trade.mts), &(trade.id as i32),
                &trade.amount, &trade.price, &is_sell]).unwrap();
            }
        }
    }
}

pub fn get_unix_timestamp_ms() -> i64 {
    let now = Utc::now();
    let seconds: i64 = now.timestamp();
    let nanoseconds: i64 = now.nanosecond() as i64;
    (seconds * 1000) + (nanoseconds / 1000 / 1000)
}

pub fn get_utc_from_ms(timestamp: i64) -> chrono::DateTime<Utc> {
    let seconds = timestamp / 1000;
    let nanoseconds = ((timestamp%1000) * 1000000) as u32;
    chrono::DateTime::<Utc>::from_utc(NaiveDateTime::from_timestamp(seconds, nanoseconds), Utc)
}

pub fn get_utc_from_s(timestamp: i64) -> chrono::DateTime<Utc> {
    chrono::DateTime::<Utc>::from_utc(NaiveDateTime::from_timestamp(timestamp, 0), Utc)
}

impl EventHandler for Candles {
    fn on_data_event(&mut self, event:DataEvent) {
        if let DataEvent::CandlesUpdateEvent(channel, candle) = event {
            if self.last { //handle old values
                if candle.timestamp == self.now { //this is finalized new information; let's go!
                    println!("{}", Utc::now());

                    //increment the snap id and reset the seq to zero
                    let mut snaplock = self.snap.lock().unwrap();
                    let mut seqlock = self.seq.lock().unwrap();
                    *snaplock += 1;
                    *seqlock = 0;
                    let (snap, seq) = (*snaplock, *seqlock);
                    drop(snaplock);
                    drop(seqlock);
                    //And make all order books take a snapshot
                    let mut kids = vec![];

                    for i in 0..4 {
                        kids.push(thread::spawn(move|| {
                            get_P_book(candle.close, candle.timestamp+60000, snap-1, i);
                        }));
                    }
                    // Make rawbooks make a query
                    kids.push(thread::spawn(move|| {
                        get_raw_book(snap-1);
                    }));
                    //Insert into candles table
                    self.connection.execute("INSERT INTO candles \
                (snap_id, exchange, pair, timestamp, \
                 open, close, high, low, volume) VALUES \
                 ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                 &[&snap, &(1 as i16), &(1 as i16), &get_utc_from_ms(candle.timestamp),
                  &candle.open, &candle.close, &candle.high, &candle.low, &candle.volume]).unwrap();
                    //Insert into snaps table
                    self.connection.execute("INSERT INTO snaps \
                (snap_id, time_begin, time_end) VALUES ($1, $2, $3)",
                   &[&(snap-1), &get_utc_from_ms(candle.timestamp), &get_utc_from_ms(candle.timestamp+60000)]).unwrap();
                    for kid in kids {
                        let _ = kid.join();
                    }
                    println!("{}", Utc::now());

                }
                self.last = false;
            } else {
                self.last = true;
                self.now = candle.timestamp;
            }
        }
    }
}

fn get_P_book(last: f64, time: i64, snap_id: i32, level: usize) -> Result<()> {
    let mut res = reqwest::get(&format!("{}{}{}", "https://api.bitfinex.com/v2/book/tBTCUSD/P", level, "?len=100"))?;
    let mut body = String::new();


    res.read_to_string(&mut body)?;
    let scales = [0.005, 0.015, 0.15, 1.0];

    let mut bid_amounts :Vec<f64> = vec![0.0; 100]; //quantity of coin
    let mut bid_counts :Vec<i16> = vec![0; 100];  //number of bids
    let mut ask_amounts:Vec<f64> = vec![0.0; 100]; //quantity of coin
    let mut ask_counts :Vec<i16> = vec![0; 100];  //number of asks
    let b = format!("{}{}{}", "{", body, "}");
    let orders :Vec<Vec<f64>> = serde_json::from_str(&body)?;
    //let asks = Vec::split_off(bids, 100);
    for i in 0..100 {
        let price = orders[i][0];
        let n = cmp::min((((last-price)/last)*(100.0/scales[level])) as usize, 99) as usize;
        bid_amounts[n] += orders[i][2];
        bid_counts[n] += orders[i][1] as i16;
    }
    for i in 100..200 {
        let price = orders[i][0];
        let n = cmp::min((((price-last)/last)*(100.0/scales[level])) as usize, 99) as usize;
        ask_amounts[n] += orders[i][2];
        ask_counts[n] += orders[i][1] as i16;
    }
    let mut sql = " ";
    let conn = get_postgres();
    conn.execute(&format!("{}{}{}", "INSERT INTO order_book_p", level, " (snap_id, exchange, pair, timestamp, last_price,\
     bid_amounts, bid_counts, ask_amounts, ask_counts) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)"),
                       &[&snap_id, &(1 as i16), &(1 as i16), &get_utc_from_ms(time), &last,
                           &bid_amounts, &bid_counts, &ask_amounts, &ask_counts]).unwrap();

    Ok(())
}

#[derive(Serialize, Deserialize)]
struct order {
    price: String,
    amount: String,
    timestamp: String
}

#[derive(Serialize, Deserialize)]
struct Book {
    bids: Vec<order>,
    asks: Vec<order>
}

fn get_raw_book(snap_id: i32) -> Result<()> {

    let mut res = reqwest::get("https://api.bitfinex.com/v1/book/btcusd?limit_asks=5000&limit_bids=5000&group=0")?;
    let mut body = String::new();
    res.read_to_string(&mut body)?;

    let mut bid_amounts:Vec<f64> = vec![0.0; 5000]; //quantity of coin
    let mut bid_prices:Vec<f64> = vec![0.0; 5000];  //price of bids
    let mut ask_amounts :Vec<f64> = vec![0.0; 5000]; //quantity of coin
    let mut ask_prices:Vec<f64> = vec![0.0; 5000];  //price of asks

    let book :Book  = serde_json::from_str(&body)?;
    let time = &book.bids[0].timestamp;

    for n in 0..5000 {
        bid_amounts[n] = book.bids[n].amount.parse::<f64>().unwrap();
        bid_prices[n] = book.bids[n].price.parse::<f64>().unwrap();
        ask_amounts[n] = book.asks[n].amount.parse::<f64>().unwrap();
        ask_prices[n] = book.asks[n].price.parse::<f64>().unwrap();
    }

    let conn = get_postgres();
    conn.execute("INSERT INTO order_book_raw (snap_id, exchange, pair, timestamp, \
     bid_amounts, bid_prices, ask_amounts, ask_prices) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                 &[&snap_id, &(1 as i16), &(1 as i16), &get_utc_from_s(time.parse::<f64>().unwrap() as i64),
                     &bid_amounts, &bid_prices, &ask_amounts, &ask_prices]).unwrap();
    Ok(())
}

/*fn make_order_insert() -> String {

}*/

fn get_postgres() -> Connection {
    Connection::connect("postgres://postgres:S0up3rd7kE50062%24XXXxXx@localhost:5432", TlsMode::None).unwrap()
}

fn main() {
    let mut kids = vec![];

    let snap:Arc<Mutex<i32>> = Arc::new(Mutex::new(0));
    let seq: Arc<Mutex<i16>> = Arc::new(Mutex::new(0));

    let snap_ticker = Arc::clone(&snap);
    let seq_ticker = Arc::clone(&seq);
    kids.push(thread::spawn(move|| {
        let mut socket: WebSockets = WebSockets::new();
        socket.add_event_handler(Ticker {connection: get_postgres(), snap: snap_ticker, seq: seq_ticker});
        socket.connect().unwrap();
        // Ticker
        socket.subscribe_ticker(BTCUSD, EventType::Trading);
        socket.event_loop().unwrap();
    }));
    let snap_trades = Arc::clone(&snap);
    kids.push(thread::spawn(move|| {
        let mut socket: WebSockets = WebSockets::new();
        socket.add_event_handler(Trades {connection: get_postgres(), snap: snap_trades});
        socket.connect().unwrap();
        // Trades
        socket.subscribe_trades(BTCUSD, EventType::Trading);
        socket.event_loop().unwrap();
    }));

    let snap_candles = Arc::clone(&snap);
    let seq_candles = Arc::clone(&seq);
    //let book_candles = Arc::clone(&book);
    kids.push(thread::spawn(move|| {
        let mut socket: WebSockets = WebSockets::new();
        socket.add_event_handler(Candles {connection: get_postgres(), snap: snap_candles, seq: seq_candles, last: true, now: 0});
        socket.connect().unwrap();
        // Candles
        socket.subscribe_candles(BTCUSD, "1m");
        socket.event_loop().unwrap();
    }));

    for kid in kids {
        let _ = kid.join();
    }

}
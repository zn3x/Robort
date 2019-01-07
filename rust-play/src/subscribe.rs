

use postgres::{Connection, TlsMode};
use std::sync::{Arc, Mutex};
use std::io;
use bitfinex::{ events::*, websockets::* , errors::*};
use std::{thread, cmp};
use std::thread::{spawn, sleep};
use std::io::Read;
use chrono::{DateTime, NaiveDateTime, Utc};
use reqwest::get;
use serde_json::{from_str};
use r2d2::{Pool, PooledConnection};
use r2d2_postgres::PostgresConnectionManager;
use std::time::{Duration};
extern crate rand;
use self::rand as r;

#[derive(Clone)]
pub struct Pair {
    pub uid: i16,
    pub name: String
}

struct Ticker {postgres: Pool<PostgresConnectionManager>, snap: Arc<Mutex<i32>>, seq: Arc<Mutex<i16>>, pair: i16, exchange: i16}
struct Trades {postgres: Pool<PostgresConnectionManager>, pair: i16, exchange: i16}
struct Candles {postgres: Pool<PostgresConnectionManager>, snap: Arc<Mutex<i32>>, seq: Arc<Mutex<i16>>, beat: Arc<Mutex<Heartbeat>>, exchange: i16, pair: Pair}

impl EventHandler for Ticker {
    fn on_data_event(&mut self, event:DataEvent) {
        if let DataEvent::TickerTradingEvent(_channel, tick) = event {
            let mut snaplock = self.snap.lock().unwrap();
            let mut seqlock = self.seq.lock().unwrap();
            *seqlock += 1;
            let (snap, seq) = (*snaplock, *seqlock);
            drop(snaplock);
            drop(seqlock);
            let result = match get_conn(&self.postgres, 1) {
                Ok(conn) => {
                    conn.execute("INSERT INTO ticker \
                (snap_id, exchange, pair, timestamp, sequence, \
                 bid, bid_size, ask, ask_size, daily_change, \
                 daily_change_perc, last_price, volume, high, low) VALUES \
                 ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)",
                                 &[&snap, &self.exchange, &self.pair, &Utc::now(), &&seq,
                                     &tick.bid, &tick.bid_size, &tick.ask, &tick.ask_size, &tick.daily_change,
                                     &tick.daily_change_perc, &tick.last_price, &tick.volume, &tick.high, &tick.low]).unwrap();
                },
                Err(err) => return
            };

        }
    }
}

fn get_conn(pg:&Pool<PostgresConnectionManager>, t:i16) ->  Result<PooledConnection<PostgresConnectionManager>> {
    match pg.get() {
        Ok(connection) => {
            Ok(connection)
        },
        Err(err) => {
            if(t>5) {
                return  Err(Error::with_chain(err, "Maximum connection attempts exceeded."));
            }
            println!("{}", "Connection failed, retry... ");
            get_conn(pg, t+1)
        }
    }
}


impl EventHandler for Trades {
    fn on_data_event(&mut self, event:DataEvent) {
        if let DataEvent::TradesTradingUpdateEvent(_channel, unk, trade) = event {
            if unk != "te" {
                let is_sell: bool = trade.amount < 0.0;
                self.postgres.get().unwrap().execute("INSERT INTO trades \
                (snap_id, exchange, pair, timestamp, trade_id, \
                 amount, price, is_sell, inserted) VALUES \
                 ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                 &[&(1 as i32), &self.exchange, &self.pair, &get_utc_from_ms(trade.mts), &(trade.id as i32),
                &trade.amount, &trade.price, &is_sell, &Utc::now()]).unwrap();
            }
        }
    }
}

pub fn get_utc_from_ms(timestamp: i64) -> DateTime<Utc> {
    let seconds = timestamp / 1000;
    let nanoseconds = ((timestamp%1000) * 1000000) as u32;
    DateTime::<Utc>::from_utc(NaiveDateTime::from_timestamp(seconds, nanoseconds), Utc)
}

pub fn get_utc_from_s(timestamp: i64) -> DateTime<Utc> {
    DateTime::<Utc>::from_utc(NaiveDateTime::from_timestamp(timestamp, 0), Utc)
}

impl EventHandler for Candles {
    fn on_data_event(&mut self, event:DataEvent) {
        if let DataEvent::CandlesUpdateEvent(_channel, candle) = event {
            let mut beatlock = self.beat.lock().unwrap();
                let (now, last) = ((*beatlock).now, (*beatlock).last);
                (*beatlock).now = candle.timestamp;
                if candle.timestamp == now && candle.timestamp != last { //this is finalized new information; let's go!
                    (*beatlock).last = candle.timestamp;
                    drop(beatlock);
                    //increment the snap id and reset the seq to zero
                    let mut snaplock = self.snap.lock().unwrap();
                    let mut seqlock = self.seq.lock().unwrap();
                    *snaplock += 1;
                    *seqlock = 0;
                    let snap = *snaplock;
                    drop(snaplock);
                    drop(seqlock);
                    //And make all order books take a snapshot
                    let mut kids = vec![];

                    if self.pair.uid < 9 {
                        for i in 0..4 {
                            let p = self.pair.name.to_string();
                            let u = self.pair.uid;
                            let c = self.postgres.get().unwrap();
                            kids.push(thread::spawn(move || {
                                get_p_book(candle.close,snap - 1,
                                           i, p, u, c);
                            }));
                        }
                    }
                    // Make rawbooks make a query
                    let i = self.pair.name.to_string();
                    let j = self.pair.uid;
                    let c = self.postgres.get().unwrap();
                    kids.push(thread::spawn(move|| {

                        get_raw_book(snap-1, i, j, c).unwrap();
                    }));
                    //Insert into candles table
                    let conn = self.postgres.get().unwrap();
                    conn.execute("INSERT INTO candles \
                (snap_id, exchange, pair, timestamp, \
                 open, close, high, low, volume, inserted) VALUES \
                 ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
                 &[&snap, &self.exchange, &self.pair.uid, &get_utc_from_ms(candle.timestamp),
                  &candle.open, &candle.close, &candle.high, &candle.low, &candle.volume, &Utc::now()]).unwrap();
                    //Insert into snaps table
                    if self.pair.uid == 1 {
                        conn.execute("INSERT INTO snaps \
                (snap_id, time_begin, time_end, inserted) VALUES ($1, $2, $3, $4)",
                                     &[&(snap - 1), &get_utc_from_ms(candle.timestamp), &get_utc_from_ms(candle.timestamp + 60000), &Utc::now()]).unwrap();
                    }
                        for kid in kids {
                        let _ = kid.join();
                    }
                    //println!("{}", Utc::now());
                } else {
                    drop(beatlock);
                }
        }
    }


}


    pub fn get_p_book(last: f64, snap_id: i32, level: usize, pair: String, uid: i16, conn: PooledConnection<PostgresConnectionManager>)
        -> Result<u64> {
        let mut res = get(&format!("{}{}{}{}{}", "https://api.bitfinex.com/v2/book/t", pair, "/P", level, "?len=100"))?;
        let mut body = String::new();


        res.read_to_string(&mut body)?;
        let scales = [0.005, 0.015, 0.15, 1.0];

        let mut bid_amounts :Vec<f64> = vec![0.0; 100]; //quantity of coin
        let mut bid_counts :Vec<i16> = vec![0; 100];  //number of bids
        let mut ask_amounts:Vec<f64> = vec![0.0; 100]; //quantity of coin
        let mut ask_counts :Vec<i16> = vec![0; 100];  //number of asks
        let orders :Vec<Vec<f64>> = from_str(&body)?;

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

        conn.execute(&format!("{}{}{}", "INSERT INTO order_book_p", level, " (snap_id, exchange, pair, timestamp, last_price,\
     bid_amounts, bid_counts, ask_amounts, ask_counts) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)"),
                     &[&snap_id, &(1 as i16), &uid, &Utc::now(), &last,
                         &bid_amounts, &bid_counts, &ask_amounts, &ask_counts]);
        Ok(2)


    }

    fn get_raw_book(snap_id: i32, pair: String, u: i16, conn: PooledConnection<PostgresConnectionManager>) -> Result<()> {

        let mut res = get(&format!("{}{}{}", "https://api.bitfinex.com/v1/book/", pair, "?limit_asks=5000&limit_bids=5000&group=0"))?;
        let mut body = String::new();
        res.read_to_string(&mut body)?;

        let mut bid_amounts:Vec<f64> = vec![0.0; 5000]; //quantity of coin
        let mut bid_prices:Vec<f64> = vec![0.0; 5000];  //price of bids
        let mut ask_amounts :Vec<f64> = vec![0.0; 5000]; //quantity of coin
        let mut ask_prices:Vec<f64> = vec![0.0; 5000];  //price of asks

        let book :Book  = from_str(&body)?;
        let time = &book.bids[0].timestamp;

        let (bids, asks) = (book.bids.len(), book.asks.len());
        println!("{} bids {}, asks {}, {}", pair, bids, asks, Utc::now());
        for n in 0..bids {
            bid_amounts[n] = match book.bids[n].amount.parse::<f64>() {
                Ok(val) => val,
                Err(val) => 0.0
            };
            bid_prices[n] = match book.bids[n].price.parse::<f64>() {
                Ok(val) => val,
                Err(val) => 0.0
            };
        }
        for n in 0..asks {
            ask_amounts[n] = match book.asks[n].amount.parse::<f64>() {
                Ok(val) => val,
                Err(va) => 0.0
            };
            ask_prices[n] = match book.asks[n].price.parse::<f64>(){
                Ok(val) => val,
                Err(va) => 0.0
            };
        }

        conn.execute("INSERT INTO order_book_raw (snap_id, exchange, pair, timestamp, \
     bid_amounts, bid_prices, ask_amounts, ask_prices, inserted) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                     &[&snap_id, &(1 as i16), &u, &get_utc_from_s(time.parse::<f64>().unwrap() as i64),
                         &bid_amounts, &bid_prices, &ask_amounts, &ask_prices, &Utc::now()]).unwrap();
        Ok(())
    }




#[derive(Serialize, Deserialize)]
struct Order {
    price: String,
    amount: String,
    timestamp: String
}

#[derive(Serialize, Deserialize)]
struct Book {
    bids: Vec<Order>,
    asks: Vec<Order>
}



/*fn make_order_insert() -> String {

}*/

pub fn get_postgres() -> Connection {
    Connection::connect("postgres://postgres:Gr0mpie3@35.199.7.86:5432", TlsMode::None).unwrap()
}

struct Heartbeat {
    last: i64,
    now: i64
}



pub fn start(exchange: i16, name: String, uid: i16, postgres: Pool<PostgresConnectionManager>) {
    let mut kids = vec![];

    let pair: Pair = Pair { uid, name };

    let snap:Arc<Mutex<i32>> = Arc::new(Mutex::new(0));
    let seq: Arc<Mutex<i16>> = Arc::new(Mutex::new(0));
    let beat: Arc<Mutex<Heartbeat>> = Arc::new(Mutex::new(Heartbeat {last: 0, now:0}));

    let snap_ticker = Arc::clone(&snap);
    let seq_ticker = Arc::clone(&seq);
    let pair_ticker = pair.clone();
    let postgres_ticker = postgres.clone();
    kids.push(thread::spawn(move|| {
        loop {
            let mut pair_tick = pair_ticker.clone();
            let mut socket: WebSockets = WebSockets::new();
            socket.add_event_handler(Ticker {postgres: postgres_ticker.clone(), snap: Arc::clone(&snap_ticker), seq: Arc::clone(&seq_ticker), pair: pair_tick.uid, exchange});
            socket.connect().unwrap();
            // Ticker
            socket.subscribe_ticker(pair_tick.name, EventType::Trading);
            match socket.event_loop() {
                Ok(any) => {
                    println!("{:?} : {:?}", "Ticker websocket success exit, retrying...", any);
                    sleep(Duration::from_millis(65000));
                    continue
                },
                Err(any) => {
                    println!("{:?} : {:?}", "Ticker websocket failure exit, retrying...", any);
                    sleep(Duration::from_millis(65000));
                    continue
                }
            }
        }
    }));

    let pair_trades = pair.clone();
    let postgres_trades = postgres.clone();
    kids.push(thread::spawn(move|| {
        loop {
            let mut pair_trades = pair_trades.clone();
            let mut socket: WebSockets = WebSockets::new();
        socket.add_event_handler(Trades {postgres: postgres_trades.clone(), pair: pair_trades.uid, exchange});
            socket.connect().unwrap();  //TODO cannot unwrap here without error handling, idiot!!!
            // Trades
            socket.subscribe_trades(pair_trades.name, EventType::Trading);
            match socket.event_loop() {
                Ok(any) => {
                    println!("{:?} : {:?}", "Trades websocket success exit, retrying...", any);
                    sleep(Duration::from_millis(65000));
                    continue
                },
                Err(any) => {
                    println!("{:?} : {:?}", "Trades websocket failure exit, retrying...", any);
                    sleep(Duration::from_millis(65000));
                    continue
                }
            }
        }
    }));

    let snap_candles = Arc::clone(&snap);
    let seq_candles = Arc::clone(&seq);
    let beat_candles = Arc::clone(&beat);

    let postgres_candles = postgres.clone();
    kids.push(thread::spawn(move|| {
        loop {
            let pair_candles = pair.clone();
            let mut socket: WebSockets = WebSockets::new();
            socket.add_event_handler(Candles {postgres: postgres_candles.clone(), snap: Arc::clone(&snap_candles), seq: Arc::clone(&seq_candles), beat: Arc::clone(&beat_candles), pair: pair_candles.clone(), exchange});
            socket.connect().unwrap();
            // Candles
            socket.subscribe_candles(pair_candles.name, "1m".to_string());
            match socket.event_loop() {
            Ok(any) => {
            println!("{:?} : {:?}", "Candles websocket success exit, retrying...", any);
                sleep(Duration::from_millis(65000));
                continue
            },
            Err(any) => {
            println!("{:?} : {:?}", "Candles websocket failure exit, retrying...", any);
                sleep(Duration::from_millis(65000));
                continue
            }
        }
    }}));

    for kid in kids {
        let _ = kid.join();
    }

}
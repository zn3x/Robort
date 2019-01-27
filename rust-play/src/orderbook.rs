extern crate bitfinex;

//use orderbook::bitfinex::{ events::* };
//use std::time::{SystemTime};
//use std::collections::HashMap;

pub enum level {
    P0,
    P1,
    P2,
    P3
}

pub struct order_bucket {
    pub count: i32,
    pub amount: f64
}

pub struct order {
    pub bid_or_ask: bool,
    pub amount: f64,
    pub count: i32,
}

pub struct OrderBook {
    symbol: &'static str,
    level: level,
    //time: SystemTime,
    last_tick: f64,
   // bids: [order_bucket;100],
   // asks: [order_bucket;100],
    //orders: HashMap<f64, f64>,
    //scale: f64
    //hashmap of price to amount and count

}

impl OrderBook {
    fn store_raw() {

    }

    fn store_tensors() {

    }

    /*fn from_snapshot(data: DataEvent::BookTradingSnapshotEvent) {

    }*/

    pub fn new( ) -> OrderBook {
        let scales = [0.005, 0.015, 0.15, 1.0];
        OrderBook {symbol: "BTCUSD", level: level::P3, last_tick: 0.0}
    }
}

//bucket = ((last-val)/last)*100
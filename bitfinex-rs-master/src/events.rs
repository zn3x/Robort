use ticker::*;
use candles::Candle;
use trades::{TradingPair as TradesTradingPair, FundingCurrency as TradesFundingCurrency};
use book::{TradingPair as BookTradingPair, FundingCurrency as BookFundingCurrency};
//use rawbook::{TradingPair as RawBookTradingPair, FundingCurrency as RawBookFundingCurrency};

#[derive(Debug, Deserialize)]
#[serde(untagged)]
#[serde(rename_all = "camelCase")]
pub enum NotificationEvent {
    Info { event: String, version: u16, platform: Platform },

    #[serde(rename_all = "camelCase")]
    TradingSubsbribed { event: String, channel: String, chan_id: u16, symbol: String, pair: String },

    #[serde(rename_all = "camelCase")]
    FundingSubsbribed { event: String, channel: String, chan_id: u16, symbol: String, currency: String },

    #[serde(rename_all = "camelCase")]
    CandlesSubsbribed { event: String, channel: String, chan_id: u16, key: String },
}

#[derive(Debug, Deserialize)]
#[serde(untagged)]
pub enum DataEvent {
    TickerTradingEvent (i32, TradingPair),
    TickerFundingEvent (i32, FundingCurrency),
    TradesTradingSnapshotEvent (i32, Vec<TradesTradingPair>),
    TradesTradingUpdateEvent (i32, String, TradesTradingPair),
    TradesFundingSnapshotEvent (i32, Vec<TradesFundingCurrency>),
    TradesFundingUpdateEvent (i32, String, TradesFundingCurrency),
    BookTradingSnapshotEvent (i32, Vec<BookTradingPair>),
    BookTradingUpdateEvent (i32, BookTradingPair),
    BookFundingSnapshotEvent (i32, Vec<BookFundingCurrency>),
    BookFundingUpdateEvent (i32, BookFundingCurrency),
    /*RawBookTradingSnapshotEvent (i32, Vec<RawBookTradingPair>),
    RawBookTradingUpdateEvent (i32, RawBookTradingPair),
    RawBookFundingSnapshotEvent (i32, Vec<RawBookFundingCurrency>),
    RawBookFundingUpdateEvent (i32, RawBookFundingCurrency),*/
    CandlesSnapshotEvent (i32, Vec<Candle>),
    CandlesUpdateEvent (i32, Candle),
    HeartbeatEvent (i32, String)
}

#[derive(Debug, Deserialize)]
pub struct Platform {
    pub status: u16,
}


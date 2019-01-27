use client::*;
use errors::*;
use serde_json::from_str;

#[derive(Serialize, Deserialize, Debug)]
pub struct TradingPair {
    pub order_id: i64,
    pub price: f64,
    pub amount: f64,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct FundingCurrency {
    pub offer_id: i64,
    pub period: f64,
    pub rate: f64,
    pub amount: f64,
}

#[derive(Clone)]
pub struct RawBook {
    client: Client,
}

impl RawBook {
    pub fn new() -> Self {
        RawBook { client: Client::new(None, None) }
    }

    pub fn funding_currency<S>(&self, symbol: S, precision: S) -> Result<(Vec<FundingCurrency>)>
        where S: Into<String>
    {
        let endpoint: String = format!("book/f{}/{}", symbol.into(), precision.into());
        let data = self.client.get(endpoint, String::new())?;

        let rawbook: Vec<FundingCurrency> = from_str(data.as_str())?;

        Ok(rawbook)
    }

    pub fn trading_pair<S>(&self, symbol: S, precision: S) -> Result<(Vec<TradingPair>)>
        where S: Into<String>
    {
        let endpoint: String = format!("book/t{}/{}", symbol.into(), precision.into());
        let data = self.client.get(endpoint, String::new())?;

        let rawbook: Vec<TradingPair> = from_str(data.as_str())?;

        Ok(rawbook)
    }
}
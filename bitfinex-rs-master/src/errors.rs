use std;
use reqwest;
use url;
use serde_json;
use tungstenite;
use postgres;
use r2d2;

error_chain! {
    types {
        Error, ErrorKind, ResultExt, Result;
    }

    errors {         
        Internal(t: String) {
            description("invalid toolchain name")
            display("invalid toolchain name: '{}'", t)
        }
    }

    foreign_links {
        ReqError(reqwest::Error);
        IoError(std::io::Error);
        ParseFloatError(std::num::ParseFloatError);
        UrlParserError(url::ParseError);
        Json(serde_json::Error);
        Tungstenite(tungstenite::Error);
        TimestampError(std::time::SystemTimeError);
        DBError(postgres::Error);
        PoolError(r2d2::Error);
    }

}
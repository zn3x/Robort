extern crate bitfinex;
extern crate postgres;
extern crate postgres_array;
extern crate reqwest;
extern crate chrono;
#[macro_use]
extern crate serde_derive;
extern crate serde_json;
extern crate r2d2;
extern crate r2d2_postgres;

use std::thread::{spawn, sleep};
use std::time::{Duration};
use r2d2_postgres::{TlsMode, PostgresConnectionManager};

mod subscribe;

fn main() {
    let mut kids = vec![];
    let manager = PostgresConnectionManager::new("postgres://postgres:Gr0mpie3@35.199.7.86:5432", TlsMode::None).unwrap();
    let pool = r2d2::Pool::builder().max_size(25).build(manager).unwrap();
    let conn = subscribe::get_postgres();
    let mut count = 0;
    for row in &conn.query("SELECT * from pairs", &[]).unwrap() {

        let mut name : String   = row.get(1);
        name = name.trim().to_string();
        let uid : i16 = row.get(0);
        println!("'{}'", name);
        let pool = pool.clone();
        kids.push(spawn(move|| {
            subscribe::start(1, name, uid, pool);
        }));
        //sleep(Duration::from_millis(2000));
        count += 1;
        if count == 20 {
            break;
        }
    }

    for kid in kids {
        let _ = kid.join();
    }
}
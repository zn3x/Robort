// Rust 1.19, Hyper 0.11, tokio-core 0.1, futures 0.1

extern crate futures;
extern crate hyper;
extern crate tokio_core;

use futures::{Future};
use hyper::{Client, Uri};
use tokio_core::reactor::Core;

fn main() {
    // Core is the Tokio event loop used for making a non-blocking request
    let mut core = Core::new().unwrap();

    let client = Client::new(&core.handle());

    let url : Uri = "http://httpbin.org/response-headers?foo=bar".parse().unwrap();
    assert_eq!(url.query(), Some("foo=bar"));

    let request = client.get(url)
        .map(|res| {
            assert_eq!(res.status(), hyper::Ok);
        });

    // request is a Future, futures are lazy, so must explicitly run
    core.run(request).unwrap();
}
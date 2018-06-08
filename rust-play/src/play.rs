extern crate csv;
extern crate reqwest;
extern crate tempdir;

use std::io::copy;
use std::fs::File;
use std::fs;
use tempdir::TempDir;
use csv::Reader;
use std::error::Error;
use std::process;

fn run() -> Result<(), Box<Error>> {
    // create a temp dir with prefix "example"
    let tmp_dir = TempDir::new("example")?;
    // make HTTP request for remote content
    let target = "https://raw.githubusercontent.com/BurntSushi/rust-csv/master/examples/data/uspop.csv";
    let mut response = reqwest::get(target)?;

    let mut dest = {
        // extract target filename from URL
        let fname = response
            .url()
            .path_segments()
            .and_then(|segments| segments.last())
            .and_then(|name| if name.is_empty() { None } else { Some(name) })
            .unwrap_or("tmp.bin");

        println!("file to download: '{}'", fname);
        let fname = tmp_dir.path().join(fname);
        println!("will be located under: '{:?}'", fname);
        // create file with given name inside the temp dir
        File::create(fname)?
    };
    // data is copied into the target file
    copy(&mut response, &mut dest)?;

    for entry in fs::read_dir(tmp_dir.path())? {
        let dir = entry?;
        let mut _file = File::open(dir.path())?;
        let mut reader = Reader::from_reader(_file);
        for result in reader.records() {
            let record = result?;
            println!("{:?}", record);
        }
    }

    // tmp_dir is implicitly removed
    Ok(())
}
fn main() -> Result<(), Box<Error>> {
    println!("Gimme that sweet sweet comma separation");
    if let Err(err) = run() {
        println!("error: {}", err);
        process::exit(-1);
    }
    let mut _f = File::open("./target/debug/example.csv")?;
    let mut reader = Reader::from_reader(_f);
    for result in reader.records() {
        let record = result?;
        println!("{:?}", record);
    }
    Ok(())
}

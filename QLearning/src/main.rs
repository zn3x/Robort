/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

extern crate rand;
extern crate rurel;

use std::collections::HashMap;

use rurel::mdp::{State, Agent};
use rurel::AgentTrainer;
use rurel::strategy::learn::QLearning;
use rurel::strategy::explore::RandomExploration;
use rurel::strategy::terminate::FixedIterations;
#[derive(PartialEq, Eq, Hash, Clone, Copy)]
struct Point {
    x: i32,
    y: i32
}
#[derive(PartialEq, Eq, Hash, Clone)]
struct MyState {
    //TODO define state. Includes:
    //Last X candles (make this settable)
    //Last Y orderbooks (also settable)
    //Last Z tickers (also settable)
    //For several coins at once
    //Price of each coin
    x: i32,
    y: i32,
    p: Point,
    maxx: i32,
    maxy: i32,
}

#[derive(PartialEq, Eq, Hash, Clone)]
enum MyAction {
    Move { dx: i32, dy: i32 },
}

impl State for MyState {
    type A = MyAction;
    fn reward(&self) -> f64 {
        //TODO impl reward for trading
        //.2% penalty for each action; gains only rewarded when realized -- assume market taking,
        //i.e., eat into order book until buy/sell is filled.
        //Assume buys/sells executed in the same book or the next tick's book???
        let (tx, ty) = (10, 10);
        let d = (((tx - self.x).pow(2) + (ty - self.y).pow(2)) as f64).sqrt() - 10.0;
        -d
    }
    fn actions(&self) -> Vec<MyAction> {
        vec![MyAction::Move { dx: -1, dy: 0 },
             MyAction::Move { dx: 1, dy: 0 },
             MyAction::Move { dx: 0, dy: -1 },
             MyAction::Move { dx: 0, dy: 1 }]
    }
}

struct MyAgent {
    state: MyState,
}

impl Agent<MyState> for MyAgent {
    fn current_state(&self) -> &MyState {
        &self.state
    }
    fn take_action(&mut self, action: &MyAction) -> () {
        match action {
            &MyAction::Move { dx, dy } => {
                self.state = MyState {
                    x: (((self.state.x + dx) % self.state.maxx) + self.state.maxx) %
                        self.state.maxx,
                    y: (((self.state.y + dy) % self.state.maxy) + self.state.maxy) %
                        self.state.maxy,
                    ..self.state.clone()
                };
            }
        }
    }
}

fn main() {
    let initial_state = MyState {
        x: 0,
        y: 0,
        p: Point {x: 0, y: 0},
        maxx: 21,
        maxy: 21,
    };
    let mut trainer = AgentTrainer::new();
    let mut agent = MyAgent { state: initial_state.clone() };
    trainer.train(&mut agent,
                  &QLearning::new(0.2, 0.01, 2.),
                  &mut FixedIterations::new(100000),
                  &RandomExploration::new());
    for i in 0..21 {
        for j in 0..21 {
            let entry: &HashMap<MyAction, f64> = trainer.expected_values(&MyState {
                x: i,
                y: j,
                ..initial_state
            })
                .unwrap();
            let val: f64 = *entry.values().next().unwrap();
            print!("{:.3}\t", val);
        }
        println!();
    }
}

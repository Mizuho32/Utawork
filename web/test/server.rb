#!/usr/bin/env ruby

require_relative '../ruby/main'

loop do
  App.run!(
    {list: Pathname(__dir__) / "data/list.yaml"},
    public_folder: (Pathname(__dir__) / "../public"),
    views:         (Pathname(__dir__) / "../views"),
    server: 'thin',
    sockets: [],
    port: 8001,
    bind: "0.0.0.0")
  break if not App.restart
end

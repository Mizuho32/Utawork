require 'optparse'


option = {}

parser = OptionParser.new
parser.on('-l list.yaml', "--list", "List of youtube videos") {|v| option[:list] = v }
parser.on('-d', "--debug", "Debug mode") { option[:debug] = true }
parser.on('-s google sheet id and gid', "--sheet-link", "id and gid of Google sheet for commenting") {|v| option[:sheet_link] = v }
parser.on('--lc list.yaml', "--list-with-comments", "List with video comments") {|v| option[:list_with_comments] = v }

# For sinatra help
if not ARGV.map{|el| el =~ /h(elp)?/}.any? then
  begin
    parser.parse!(ARGV)
  rescue StandardError
    STDERR.puts parser
    exit 1
  end
else
  puts parser.help
end

require_relative 'ruby/utils'
require_relative 'ruby/main'

Utils.init()


App.run!(
  option,
  public_folder: (Pathname(__dir__) / "public"),
  views:         (Pathname(__dir__) / "views"),
  server: 'thin',
  sockets: [],
  port: 8000,
  bind: "0.0.0.0",
)

puts "End"

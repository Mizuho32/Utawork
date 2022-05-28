require 'open-uri'

#require 'sinatra/reloader' if development?
require 'oga'
require 'sinatra'
require 'sinatra-websocket'


# https://qiita.com/TeQuiLayy/items/a74f928426dcb013e1cd
def google(word)
  #user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.81 Safari/537.36"
  user_agent = "(｀・ω・´)" # not to load images(?)

  search_url = "https://www.google.co.jp/search?hl=jp&gl=JP&"
  query = URI.encode_www_form(q: word)
  search_url += query

  charset = nil

  html = URI.open(search_url, 'User-Agent' => user_agent) { |f|
      charset = f.charset
      f.read
  }

  parsed = Oga.parse_html(
    html.encode("UTF-16BE", "UTF-8", :invalid => :replace, :undef => :replace, :replace => '?')
        .encode("UTF-8"))
  return parsed.xpath("//div[@id='main']").first.to_xml

end

set :public_folder, __dir__
set :server, 'thin'
set :sockets, []
set :port, 8000
set :bind, "0.0.0.0"

get '/' do
  is_mobile = params.key?("mobile")
  erb :index, locals: {
    :css =>  is_mobile ? "mobile.css" : "style.css",
    is_mobile: is_mobile,
    search: erb(:search),
    table: erb(:table, locals: {is_mobile: is_mobile})
  }
end

get '/websocket' do
  if request.websocket?
    request.websocket do |ws|

      ws.onopen do
        #settings.sockets << ws
      end

      ws.onmessage do |msg|
        puts "search: #{msg}"
			  sleep 1
        #html = Oga.parse_html(File.read("test.html").encode("UTF-16BE", "UTF-8", :invalid => :replace, :undef => :replace, :replace => '?').encode("UTF-8"))
        #main = html.xpath("//div[@id='rcnt']").first

        #ws.send(main.to_xml)
        ws.send(google(msg))
      rescue StandardError => ex
        puts ex.message, ex.backtrace.join("\n")
        #settings.sockets.each do |s|
        #  s.send(msg)
        #end
      end

      ws.onclose do
        #settings.sockets.delete(ws)
      end

    end
  end
end

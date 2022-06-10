require 'open-uri'
require 'json'

#require 'sinatra/reloader' if development?
require 'oga'
require 'sinatra'
require 'sinatra-websocket'

require_relative 'utils'

class App < Sinatra::Base

  class << self
    attr_reader :option
    def run!(opt, **kw)
      @option = opt
      puts @option[:list]
      super(**kw)
    end
  end

  get '/' do
    is_mobile = params.key?("mobile")
    video_id, segments = Utils.load_segments(params["video_id"].to_s)

    locals = {
      :css =>  is_mobile ? "mobile.css" : "style.css",
      is_mobile: is_mobile, raw_times: segments, video_id: video_id
    }

    erb :index, locals: {
      **locals,
      search: erb(:search, locals: locals),
      table: erb(:table, locals: locals)
    }
  end

  post "/segments" do
   request.body.rewind  # 既に読まれているときのため
   data = JSON.parse request.body.read
   puts data

   if data["segments"].empty? then
     status 501
     "Empty timestamp"
   else
     Utils.save_segments(data["video_id"], data["segments"])
     status 201
     "OK"
   end
  rescue StandardError => ex
    status 500
    "#{ex.message}\n#{Utils.remove_bundler(ex).join("\n")}"
  end

  get '/websocket' do
    if request.websocket?
      request.websocket { |ws|

        ws.onopen do
          #settings.sockets << ws
        end

        ws.onmessage do |msg|
          query = JSON.parse(msg)

          if query.key? "search" then
            word = query["search"].to_s
            if App.option[:debug] then
              puts "search: #{word}"
              #sleep 1
              html = Oga.parse_html(File.read("public/test2.html").encode("UTF-16BE", "UTF-8", :invalid => :replace, :undef => :replace, :replace => '?').encode("UTF-8"))
              main = html.xpath("//div[@id='main']").first

              ws.send(main.to_xml)
            else
              ws.send(Utils.google(word))
            end
          elsif query.key? "tags" then
            begin
              tags = JSON.parse(query["tags"])
              vid = query["video_id"]
              puts("tags: #{tags}, id:#{vid}")
              Utils.save_tags(vid, tags)

              ws.send(tags.size.to_s);
            rescue StandardError => ex
              puts ex.message, Utils.remove_bundler(ex).join("\n")
              ws.send(ex.message);
            end
          end
        rescue StandardError => ex
          puts ex.message, Utils.remove_bundler(ex).join("\n")
          #settings.sockets.each do |s|
          #  s.send(msg)
          #end
        end

        ws.onclose do
          #settings.sockets.delete(ws)
        end

      }
    end
  end

end

require 'open-uri'
require 'json'

#require 'sinatra/reloader' if development?
require 'oga'
require 'sinatra'
require 'sinatra-websocket'

require_relative 'ruby/utils'

Utils.init()

set :public_folder, (Pathname(__dir__) / "public")
set :server, 'thin'
set :sockets, []
set :port, 8000
set :bind, "0.0.0.0"

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

get '/websocket' do
  if request.websocket?
    request.websocket do |ws|

      ws.onopen do
        #settings.sockets << ws
      end

      ws.onmessage do |msg|
        query = JSON.parse(msg)

        if query.key? "search" then
          word = query["search"].to_s
          if ARGV.first&.include? "d" then
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
            puts ex.message, ex.backtrace.select{|line| not line.include?("bundle")}.join("\n")
            ws.send(ex.message);
          end
        end
      rescue StandardError => ex
        puts ex.message, ex.backtrace.select{|line| not line.include?("bundle")}.join("\n")
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

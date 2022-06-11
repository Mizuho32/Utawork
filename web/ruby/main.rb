require 'open-uri'
require 'json'
require 'date'

#require 'sinatra/reloader' if development?
require 'oga'
require 'sinatra'
require 'sinatra-websocket'
require 'sinatra/reloader'

require_relative 'utils'

class App < Sinatra::Base

  configure :development do
    Utils::DATA_DIR = Pathname("test") / Utils::DATA_DIR
    register Sinatra::Reloader

    get '/restart' do
      App.restart = true
      App.quit!
    end
  end

  class << self
    attr_reader :option, :list, :args
    attr_accessor :restart
    def run!(opt, **args)
      @option = opt
      @args   = args
      @list   = Utils.load_list(@option[:list])
      #pp @list
      @restart = false
      super(**args)
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

  get '/locked' do
    App.list.values.select{|item| item[:lock]}.map{|item| Utils.decode_videoinfo(item)}.to_json
  end

  get '/video2process' do
    yet_processed = App.list.values.select{|item|
      not item[:has_segments] and not item[:lock]
    }.first&.dup || {}
    id = yet_processed[:video_id]&.to_sym
    #pp App.list.values

    if id then
      if params.key?("lock") then
        App.list[id][:lock] = DateTime.now
        Utils.save_list(App.option[:list], App.list)
      end

      return Utils.decode_videoinfo(yet_processed).to_json
    else
      return "{}"
    end
  rescue StandardError => ex
    status 500
    msg = "#{ex.message}\n#{Utils.remove_bundler(ex).join("\n")}"
    puts msg
    {error: msg}.to_json
  end

  post "/segments" do
   request.body.rewind  # 既に読まれているときのため
   data = JSON.parse request.body.read
   id = data["video_id"].to_sym
   puts data

   App.list[id][:lock] = false if App.list[id][:lock]

   txt =
   if data["segments"].empty? then
     status 501
     "Empty timestamp"
   else
     Utils.save_segments(data["video_id"], data["segments"])
     App.list[id][:has_segments] = true
     status 201
     "OK"
   end

   Utils.save_list(App.option[:list], App.list)

   txt
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

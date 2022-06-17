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
    if not Utils::DATA_DIR.each_filename.map{|f| f == "test"}.any? then
      Utils::DATA_DIR = Pathname("test") / Utils::DATA_DIR
    end
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

    video_info = App.list[video_id.to_sym]
    if video_info then
      tagging_lock = video_info[:tagging_lock]
      unlock = (not params["lock"].nil? and params["lock"] == tagging_lock)
      #p params["lock"], tagging_lock
      return erb(:now_tagging, locals: video_info) if tagging_lock.is_a?(String) and not unlock # locked
    end

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

  get '/tagging' do
    Utils.renew_list(App.list) # FIXME: should not access disk
    erb :manual_list, locals: {list: App.list.values
      .select{|item| item[:has_segments] and not item[:segments_is_empty] }
      .sort{|l, r|
        l = l[:has_tags] ? 1 : 0
        r = r[:has_tags] ? 1 : 0
        l <=> r
      }
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

   App.list[id] = {video_id: id} if not App.list[id]
   App.list[id][:lock] = false if App.list[id][:lock]

   txt =
   if data["segments"].empty? then
     App.list[id][:segments_is_empty] = true
     status 501
     "Empty timestamp"
   else
     App.list[id].delete(:segments_is_empty) if App.list[id].has_key?(:segments_is_empty)
     status 201
     "OK"
   end
   Utils.save_segments(data["video_id"], data["segments"])
   App.list[id][:has_segments] = true

   Utils.save_list(App.option[:list], App.list)

   txt
  rescue StandardError => ex
    status 500
    err = "#{ex.message}\n#{Utils.remove_bundler(ex).join("\n")}"
    puts err
    err
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
          elsif query.key? "lock" then
            id = query["video_id"].to_sym
            if info = App.list[id] then
              info[:tagging_lock] = query["lock"]
              Utils.save_list(App.option[:list], App.list)
              ws.send(query["lock"]);
            end
          elsif query.key? "unlock" then
            id = query["video_id"].to_sym
            if info = App.list[id] and info[:tagging_lock]==query["unlock"] then
              info.delete(:tagging_lock)
              Utils.save_list(App.option[:list], App.list)
              ws.send(query["unlock"]);
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
